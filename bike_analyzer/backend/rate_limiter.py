"""Shared rate limiter for slowapi."""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from ipaddress import AddressValueError, ip_address, ip_network

from fastapi import HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

_TRUSTED_PROXIES: tuple[str, ...] = (
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.1",
    "::1",
)


def _is_trusted_proxy(ip_str: str) -> bool:
    try:
        addr = ip_address(ip_str)
        for prefix in _TRUSTED_PROXIES:
            try:
                if addr in ip_network(prefix):
                    return True
            except (AddressValueError, ValueError):
                if addr == ip_address(prefix):
                    return True
    except (AddressValueError, ValueError):
        pass
    return False


def get_limiter_key(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        first_hop = forwarded.split(",")[0].strip()
        client_host = request.client.host if request.client else "unknown"
        if _is_trusted_proxy(client_host):
            return first_hop
        logger.debug("X-Forwarded-For from untrusted source %s, using direct IP", client_host)
    return get_remote_address(request)


limiter = Limiter(key_func=get_limiter_key)


@dataclass
class RateLimitConfig:
    max_requests: int = 100
    window_seconds: int = 60


_USER_RATE_LIMITS: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))


def check_user_rate_limit(user_id: int, endpoint: str, config: RateLimitConfig | None = None) -> None:
    cfg = config or RateLimitConfig()
    key = f"user:{user_id}:{endpoint}"
    now = time.time()
    window_start = now - cfg.window_seconds
    requests = _USER_RATE_LIMITS[key]
    requests[:] = [t for t in requests if t > window_start]
    if len(requests) >= cfg.max_requests:
        logger.warning("Rate limit exceeded for user %s on %s (%d/%d in %ds)",
                       user_id, endpoint, len(requests), cfg.max_requests, cfg.window_seconds)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {cfg.max_requests} requests per {cfg.window_seconds}s",
        )
    requests.append(now)


def rate_limit_dependency(max_requests: int = 100, window_seconds: int = 60):
    config = RateLimitConfig(max_requests=max_requests, window_seconds=window_seconds)

    def _check(current_user: dict) -> dict:
        user_id = int(current_user.get("id", 0))
        if user_id > 0:
            check_user_rate_limit(user_id, "global", config)
        return current_user

    return _check

