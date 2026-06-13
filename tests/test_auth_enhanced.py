"""Enhanced auth tests: JWT blacklist and TOTP/2FA (stdlib only)."""

from __future__ import annotations

import asyncio
import time

import pytest


def test_totp_generate_and_verify():
    import os
    from bike_analyzer.backend.security import generate_totp, verify_totp

    os.environ.setdefault("SECRET_KEY", "test-secret-totp")
    secret = "JBSWY3DPEHPK3PXP"
    code = generate_totp(secret)
    assert isinstance(code, str)
    assert len(code) == 6
    assert code.isdigit()
    assert verify_totp(secret, code) is True
    assert verify_totp(secret, "000000") is False
    assert verify_totp(secret, "") is False
    assert verify_totp(secret, "abc123") is False
    assert verify_totp(secret, "12345") is False


def test_totp_window_skew():
    from bike_analyzer.backend.security import _hotp, generate_totp

    secret = "JBSWY3DPEHPK3PXP"
    now = int(time.time())
    counter = now // 30
    past = _hotp(secret, counter - 1)
    current = _hotp(secret, counter)
    future = _hotp(secret, counter + 1)

    assert verify_totp(secret, past, window=1) is True
    assert verify_totp(secret, current, window=1) is True
    assert verify_totp(secret, future, window=1) is True
    assert verify_totp(secret, _hotp(secret, counter - 2), window=1) is False


def test_totp_provisioning_uri():
    from bike_analyzer.backend.security import provisioning_uri

    secret = "JBSWY3DPEHPK3PXP"
    uri = provisioning_uri(secret, 1)
    assert uri.startswith("otpauth://totp/")
    assert "user1" in uri
    assert "BikeMaster" in uri
    assert "sha256" in uri
    assert "digits=6" in uri
    assert "period=30" in uri


@pytest.mark.asyncio
async def test_blacklist_round_trip():
    import os

    os.environ["ENVIRONMENT"] = "test"
    from unittest.mock import MagicMock, patch

    fake_redis = MagicMock()
    fake_redis.set = MagicMock(return_value=True)
    fake_redis.exists = MagicMock(return_value=1)
    fake_redis.close = MagicMock()

    with patch("bike_analyzer.backend.security.get_redis", return_value=fake_redis):
        from bike_analyzer.backend.security import is_token_revoked, revoke_token

        ok = await revoke_token("ut-jti-1", ttl=60)
        assert ok is True
        assert await is_token_revoked("ut-jti-1") is True
