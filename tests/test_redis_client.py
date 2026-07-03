"""Tests for redis_client module."""

import hashlib
import json
from unittest.mock import AsyncMock, patch

import pytest

from bike_analyzer.backend.redis_client import (
    cache,
    cache_key,
    check_rate_limit,
    rate_limit_key,
)


class TestCacheKey:
    def test_basic(self):
        k = cache_key("arg1", "arg2", key="value")
        assert k.startswith("bikemaster:cache:")

    def test_deterministic(self):
        k1 = cache_key("test", 123)
        k2 = cache_key("test", 123)
        assert k1 == k2

    def test_different_args_different_keys(self):
        k1 = cache_key("a")
        k2 = cache_key("b")
        assert k1 != k2

    def test_empty_args(self):
        k = cache_key()
        assert k.startswith("bikemaster:cache:")

    def test_consistent_hash(self):
        raw = json.dumps({"args": ("test",), "kwargs": {}}, sort_keys=True, default=str)
        expected = "bikemaster:cache:" + hashlib.sha256(raw.encode()).hexdigest()
        assert cache_key("test") == expected


class TestRateLimitKey:
    def test_with_user_id(self):
        k = rate_limit_key(42, "/api/test")
        assert k == "bikemaster:ratelimit:42:/api/test"

    def test_without_user_id(self):
        k = rate_limit_key(None, "/api/test")
        assert k == "bikemaster:ratelimit:anon:/api/test"

    def test_empty_endpoint(self):
        k = rate_limit_key(1, "")
        assert k == "bikemaster:ratelimit:1:"


class TestCacheDecorator:
    @pytest.mark.asyncio
    async def test_cache_hit(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps("cached_value"))

        with patch("bike_analyzer.backend.redis_client.get_redis", return_value=mock_redis):
            @cache(ttl=60)
            async def expensive_func(x):
                return x * 2

            result = await expensive_func(5)
            assert result == "cached_value"

    @pytest.mark.asyncio
    async def test_cache_miss_then_set(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)

        with patch("bike_analyzer.backend.redis_client.get_redis", return_value=mock_redis):
            @cache(ttl=60)
            async def compute(x):
                return x * 2

            result = await compute(5)
            assert result == 10
            mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_redis_returns_none(self):
        with patch("bike_analyzer.backend.redis_client.get_redis", return_value=None):
            @cache(ttl=60)
            async def compute(x):
                return x * 2

            result = await compute(5)
            assert result == 10


class TestCheckRateLimit:
    @pytest.mark.asyncio
    async def test_allowed(self):
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()

        with patch("bike_analyzer.backend.redis_client.get_redis", return_value=mock_redis):
            result = await check_rate_limit(1, "/api/test", limit=60)
            assert result is True

    @pytest.mark.asyncio
    async def test_over_limit(self):
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=61)
        mock_redis.expire = AsyncMock()

        with patch("bike_analyzer.backend.redis_client.get_redis", return_value=mock_redis):
            result = await check_rate_limit(1, "/api/test", limit=60)
            assert result is False

    @pytest.mark.asyncio
    async def test_no_redis_allows(self):
        with patch("bike_analyzer.backend.redis_client.get_redis", return_value=None):
            result = await check_rate_limit(1, "/api/test")
            assert result is True

    @pytest.mark.asyncio
    async def test_redis_exception_allows(self):
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=Exception("Redis error"))

        with patch("bike_analyzer.backend.redis_client.get_redis", return_value=mock_redis):
            result = await check_rate_limit(1, "/api/test")
            assert result is True
