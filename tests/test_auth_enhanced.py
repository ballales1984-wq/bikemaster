"""Enhanced auth tests: JWT blacklist and TOTP/2FA (stdlib only)."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest


def _make_fake_redis():
    fake = MagicMock()
    fake.set = MagicMock(return_value=True)
    fake.exists = MagicMock(return_value=1)
    fake.get = MagicMock(return_value=None)
    fake.delete = MagicMock(return_value=1)
    fake.close = MagicMock()
    return fake


@pytest.mark.asyncio
async def test_blacklist_round_trip():
    import os

    os.environ["ENVIRONMENT"] = "test"
    fake = _make_fake_redis()
    fake.exists = MagicMock(return_value=1)

    with patch("bike_analyzer.backend.security.get_redis", return_value=fake):
        from bike_analyzer.backend.security import is_token_revoked, revoke_token

        ok = await revoke_token("ut-jti-1", ttl=60)
        assert ok is True
        assert await is_token_revoked("ut-jti-1") is True


@pytest.mark.asyncio
async def test_blacklist_token_not_revoked():
    fake = _make_fake_redis()
    fake.exists = MagicMock(return_value=0)

    with patch("bike_analyzer.backend.security.get_redis", return_value=fake):
        from bike_analyzer.backend.security import is_token_revoked

        assert await is_token_revoked("missing-jti") is False


@pytest.mark.asyncio
async def test_revoke_succeeds_in_memory_when_redis_down():
    # Per commit ce2dccb la revoca in-memory di fallback è considerata un successo:
    # revoke_token ritorna True anche se Redis non è disponibile.
    with patch("bike_analyzer.backend.security.get_redis", return_value=None):
        from bike_analyzer.backend.security import is_token_revoked, revoke_token

        assert await revoke_token("any-jti") is True
        # La revoca è effettiva almeno nel processo corrente (in-memory).
        assert await is_token_revoked("any-jti") is True


def test_totp_generate_and_verify():
    import os

    os.environ.setdefault("SECRET_KEY", "test-secret-totp")
    from bike_analyzer.backend.security import generate_totp, verify_totp

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
    from bike_analyzer.backend.security import _hotp, verify_totp

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


def test_jwt_revoke_with_jti_in_payload():
    import os

    os.environ["ENVIRONMENT"] = "test"
    fake = _make_fake_redis()
    fake.exists = MagicMock(return_value=1)

    with patch("bike_analyzer.backend.security.get_redis", return_value=fake):
        from bike_analyzer.backend.security import create_access_token, decode_token

        token = create_access_token("777", is_admin=False)
        assert token is not None
        try:
            asyncio.run(decode_token(token))
            assert False, "Expected HTTPException 401"
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 401


def test_logout_endpoint_exists(client):
    resp = client.post(
        "/api/v1/auth/logout",
        headers=client.headers,
    )
    assert resp.status_code in (200, 401)
