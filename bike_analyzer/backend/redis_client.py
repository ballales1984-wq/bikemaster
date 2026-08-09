"""Async Redis client with optional fallback.

Provides:
- Singleton Redis connection pool
- Cache decorator for expensive computations
- User-based rate limiting keys
- Graceful degradation when Redis is unavailable
"""

from __future__ import annotations

import asyncio
import contextlib
import functools
import hashlib
import json
import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

_redis = None
_REDIS_CONNECT_TIMEOUT = 3
# After a failed connection, suppress reconnection attempts (and log spam)
# for this long before retrying, so a downed Redis doesn't hammer every request.
_REDIS_RETRY_COOLDOWN = 30.0
_redis_unavailable_at = 0.0
_redis_lock = asyncio.Lock()


async def get_redis():
    """Get or create Redis connection pool.

    On failure the error is cached and reconnection is suppressed for
    ``_REDIS_RETRY_COOLDOWN`` seconds, so a temporarily unavailable Redis
    does not produce a warning (and a blocking connect attempt) on every call.
    """
    global _redis, _redis_unavailable_at
    if _redis is not None:
        return _redis
    if _redis_unavailable_at > 0 and (time.monotonic() - _redis_unavailable_at) < _REDIS_RETRY_COOLDOWN:
        return None
    async with _redis_lock:
        if _redis is not None:
            return _redis
        if _redis_unavailable_at > 0 and (time.monotonic() - _redis_unavailable_at) < _REDIS_RETRY_COOLDOWN:
            return None
        from bike_analyzer.backend.settings import get_settings

        s = get_settings()
        if not s.redis_url:
            return None
        try:
            import redis.asyncio as aioredis

            url = s.redis_url
            _redis = aioredis.from_url(
                url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=_REDIS_CONNECT_TIMEOUT,
                socket_timeout=_REDIS_CONNECT_TIMEOUT,
                retry_on_timeout=False,
            )
            await asyncio.wait_for(_redis.ping(), timeout=_REDIS_CONNECT_TIMEOUT)
            logger.info("Redis connected: %s", url)
            _redis_unavailable_at = 0.0
        except Exception as exc:
            _redis_unavailable_at = time.monotonic()
            logger.warning("Redis unavailable: %s — cache disabled", exc)
            _redis = None
        return _redis


async def close_redis():
    global _redis, _redis_unavailable_at
    if _redis is not None:
        with contextlib.suppress(Exception):
            await _redis.close()
        _redis = None
    _redis_unavailable_at = 0.0


_MEMORY_CACHE: dict[str, tuple[Any, float]] = {}
_MEMORY_RATELIMIT: dict[str, tuple[int, float]] = {}
_MEMORY_CACHE_MAX = 1000
_MEMORY_RATELIMIT_MAX = 1000
_memory_cache_lock = asyncio.Lock()
_memory_ratelimit_lock = asyncio.Lock()


def _cleanup_memory_cache():
    now = time.monotonic()
    expired = [k for k, (v, exp) in _MEMORY_CACHE.items() if now > exp]
    for k in expired:
        _MEMORY_CACHE.pop(k, None)
    if len(_MEMORY_CACHE) > _MEMORY_CACHE_MAX:
        oldest = sorted(_MEMORY_CACHE.items(), key=lambda kv: kv[1][1])[:len(_MEMORY_CACHE) - _MEMORY_CACHE_MAX]
        for k, _ in oldest:
            _MEMORY_CACHE.pop(k, None)

def cache_key(*args: Any, **kwargs: Any) -> str:
    raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return "bikemaster:cache:" + hashlib.sha256(raw.encode()).hexdigest()


async def cached(key: str, ttl: int = 300) -> Any | None:
    r = await get_redis()
    if r is None:
        async with _memory_cache_lock:
            _cleanup_memory_cache()
            if key in _MEMORY_CACHE:
                val, exp = _MEMORY_CACHE[key]
                if time.monotonic() <= exp:
                    return val
                else:
                    _MEMORY_CACHE.pop(key, None)
            return None
    try:
        val = await r.get(key)
        if val is not None:
            return json.loads(val)
    except Exception as exc:
        logger.debug("cache get error: %s", exc)
    return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    r = await get_redis()
    if r is None:
        async with _memory_cache_lock:
            _cleanup_memory_cache()
            _MEMORY_CACHE[key] = (value, time.monotonic() + ttl)
        return True
    try:
        await r.set(key, json.dumps(value, default=str), ex=ttl)
        return True
    except Exception as exc:
        logger.debug("cache set error: %s", exc)
        return False


async def cache_delete(key: str) -> bool:
    r = await get_redis()
    if r is None:
        async with _memory_cache_lock:
            _MEMORY_CACHE.pop(key, None)
        return True
    try:
        await r.delete(key)
        return True
    except Exception:
        return False


def rate_limit_key(user_id: int | None, endpoint: str) -> str:
    uid = user_id or "anon"
    return f"bikemaster:ratelimit:{uid}:{endpoint}"


async def check_rate_limit(user_id: int | None, endpoint: str, limit: int = 60, window: int = 60) -> bool:
    """Per-user rate limit using sliding window."""
    r = await get_redis()
    if r is None:
        now = time.monotonic()
        key = rate_limit_key(user_id, endpoint)
        async with _memory_ratelimit_lock:
            count, exp = _MEMORY_RATELIMIT.get(key, (0, 0))
            if now > exp:
                count = 0
                exp = now + window
            count += 1
            _MEMORY_RATELIMIT[key] = (count, exp)

            if len(_MEMORY_RATELIMIT) > _MEMORY_RATELIMIT_MAX:
                expired = [k for k, (c, e) in _MEMORY_RATELIMIT.items() if now > e]
                for k in expired:
                    _MEMORY_RATELIMIT.pop(k, None)
                if len(_MEMORY_RATELIMIT) > _MEMORY_RATELIMIT_MAX:
                    oldest = sorted(_MEMORY_RATELIMIT.items(), key=lambda kv: kv[1][1])[:len(_MEMORY_RATELIMIT) - _MEMORY_RATELIMIT_MAX]
                    for k, _ in oldest:
                        _MEMORY_RATELIMIT.pop(k, None)

            return count <= limit
    key = rate_limit_key(user_id, endpoint)
    try:
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, window)
        return count <= limit
    except Exception:
        return True


def cache(ttl: int = 300, key_prefix: str = ""):
    """Decorator to cache async function results in Redis."""

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any):
            k = cache_key(key_prefix or func.__name__, *args, **kwargs)
            cached_val = await cached(k, ttl)
            if cached_val is not None:
                return cached_val
            result = await func(*args, **kwargs)
            await cache_set(k, result, ttl)
            return result

        return wrapper

    return decorator


__all__ = [
    "get_redis",
    "close_redis",
    "cached",
    "cache_set",
    "cache_delete",
    "cache_key",
    "rate_limit_key",
    "check_rate_limit",
    "cache",
]
