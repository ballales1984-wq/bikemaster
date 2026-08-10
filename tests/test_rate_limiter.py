"""Tests for rate limiter module."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from bike_analyzer.backend.rate_limiter import (
    RateLimitConfig,
    check_user_rate_limit,
    get_limiter_key,
    rate_limit_dependency,
)
from bike_analyzer.backend.trusted_proxies import _is_trusted_proxy


def test_is_trusted_proxy_private():
    assert _is_trusted_proxy("10.0.0.1") is True
    assert _is_trusted_proxy("172.16.0.5") is True
    assert _is_trusted_proxy("192.168.1.1") is True
    assert _is_trusted_proxy("127.0.0.1") is True
    assert _is_trusted_proxy("::1") is True


def test_is_trusted_proxy_public():
    assert _is_trusted_proxy("8.8.8.8") is False
    assert _is_trusted_proxy("1.1.1.1") is False


def test_is_trusted_proxy_invalid():
    assert _is_trusted_proxy("not-an-ip") is False
    assert _is_trusted_proxy("") is False


def test_get_limiter_key_trusted_proxy():
    request = MagicMock()
    request.headers.get.return_value = "203.0.113.1, 198.51.100.1"
    request.client.host = "10.0.0.1"
    key = get_limiter_key(request)
    assert key == "203.0.113.1"


def test_get_limiter_key_untrusted_proxy():
    request = MagicMock()
    request.headers.get.return_value = "203.0.113.1"
    request.client.host = "8.8.8.8"
    key = get_limiter_key(request)
    assert key == "8.8.8.8"


def test_get_limiter_key_no_forwarded():
    request = MagicMock()
    request.headers.get.return_value = ""
    request.client.host = "8.8.8.8"
    key = get_limiter_key(request)
    assert key == "8.8.8.8"


def test_check_user_rate_limit_within_limit():
    from bike_analyzer.backend.rate_limiter import _USER_RATE_LIMITS

    _USER_RATE_LIMITS.clear()
    cfg = RateLimitConfig(max_requests=3, window_seconds=60)
    check_user_rate_limit(1, "/test", cfg)
    check_user_rate_limit(1, "/test", cfg)
    check_user_rate_limit(1, "/test", cfg)


def test_check_user_rate_limit_blocks():
    from bike_analyzer.backend.rate_limiter import _USER_RATE_LIMITS

    _USER_RATE_LIMITS.clear()
    cfg = RateLimitConfig(max_requests=2, window_seconds=60)
    check_user_rate_limit(1, "/test", cfg)
    check_user_rate_limit(1, "/test", cfg)
    with pytest.raises(HTTPException) as exc_info:
        check_user_rate_limit(1, "/test", cfg)
    assert exc_info.value.status_code == 429


def test_rate_limit_dependency_allows():
    dep = rate_limit_dependency(max_requests=5, window_seconds=60)
    user = {"id": "1"}
    result = dep(user)
    assert result == user


def test_rate_limit_dependency_ignores_anon():
    dep = rate_limit_dependency(max_requests=1, window_seconds=60)
    user = {"id": 0}
    result = dep(user)
    assert result == user
