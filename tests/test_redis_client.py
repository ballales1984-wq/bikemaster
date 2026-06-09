"""Tests for redis_client module."""
import pytest
import json

from bike_analyzer.backend.redis_client import (
    cache_key, cached, cache_set, cache_delete,
    rate_limit_key, check_rate_limit
)


class TestCacheKey:
    def test_simple_args(self):
        key = cache_key("test", 123, "abc")
        assert key.startswith("bikemaster:cache:")

    def test_with_kwargs(self):
        key = cache_key("ride", id=1, athlete=2)
        assert key.startswith("bikemaster:cache:")

    def test_deterministic(self):
        key1 = cache_key("test", 1, 2)
        key2 = cache_key("test", 1, 2)
        assert key1 == key2

    def test_unique_inputs(self):
        key1 = cache_key("test", 1)
        key2 = cache_key("test", 2)
        assert key1 != key2


class TestCacheGetSet:
    @pytest.mark.asyncio
    async def test_cached_without_redis_returns_none(self):
        result = await cached("nonexistent:key", ttl=60)
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_set_without_redis_returns_false(self):
        result = await cache_set("test:key", {"data": 123})
        assert result is False

    @pytest.mark.asyncio
    async def test_cache_delete_without_redis_returns_false(self):
        result = await cache_delete("test:key")
        assert result is False


class TestRateLimitKey:
    def test_user_rate_limit_key(self):
        key = rate_limit_key(123, "rides")
        assert key == "bikemaster:ratelimit:123:rides"

    def test_anonymous_rate_limit_key(self):
        key = rate_limit_key(None, "import")
        assert key == "bikemaster:ratelimit:anon:import"


class TestCheckRateLimit:
    @pytest.mark.asyncio
    async def test_check_without_redis_allows(self):
        result = await check_rate_limit(1, "rides", limit=100, window=60)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_anonymous(self):
        result = await check_rate_limit(None, "api")
        assert result is True