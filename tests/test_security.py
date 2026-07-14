"""Tests for security module."""

import time
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from jose import jwt

from bike_analyzer.backend.security import (
    ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    SECRET_KEY,
    _generate_totp_secret,
    _hotp,
    create_access_token,
    create_refresh_token,
    decode_token,
    delete_totp_secret,
    fingerprint_token,
    generate_totp,
    get_refresh_token,
    get_totp_secret,
    get_totp_secret_key,
    hash_password,
    is_token_revoked,
    provisioning_uri,
    revoke_refresh_token,
    revoke_token,
    save_refresh_token,
    save_totp_secret,
    verify_password,
    verify_totp,
)


def _make_redis_mock(get_return=None, set_return=True, delete_return=True, exists_return=0):
    r = AsyncMock()
    r.get = AsyncMock(return_value=get_return)
    r.set = AsyncMock(return_value=set_return)
    r.delete = AsyncMock(return_value=delete_return)
    r.exists = AsyncMock(return_value=exists_return)
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock(return_value=True)
    r.ping = AsyncMock(return_value=True)
    r.return_value = r  # so that awaiting get_redis() returns this mock
    return r


def _patch_get_redis(redis_mock):
    return patch("bike_analyzer.backend.security.get_redis", redis_mock)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


class TestHashPassword:
    def test_hash_returns_string(self):
        h = hash_password("mypassword")
        assert isinstance(h, str)
        assert len(h) > 20

    def test_hash_different_each_time(self):
        h1 = hash_password("password123")
        h2 = hash_password("password123")
        assert h1 != h2

    def test_verify_correct(self):
        h = hash_password("correct_password")
        assert verify_password("correct_password", h) is True

    def test_verify_wrong(self):
        h = hash_password("correct_password")
        assert verify_password("wrong_password", h) is False

    def test_verify_empty_hashed(self):
        assert verify_password("password", "") is False

    def test_verify_none_hashed(self):
        assert verify_password("password", None) is False


# ---------------------------------------------------------------------------
# JWT token creation/decoding
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    def test_basic(self):
        token = create_access_token(subject="1")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decoded_payload(self):
        token = create_access_token(subject="42", is_admin=True)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience=JWT_AUDIENCE, issuer=JWT_ISSUER)
        assert payload["sub"] == "42"
        assert payload["is_admin"] is True
        assert "jti" in payload
        assert "exp" in payload

    def test_with_tenant_id(self):
        token = create_access_token(subject="1", tenant_id=5)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience=JWT_AUDIENCE, issuer=JWT_ISSUER)
        assert payload.get("tenant_id") == 5

    def test_without_tenant_id(self):
        token = create_access_token(subject="1")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience=JWT_AUDIENCE, issuer=JWT_ISSUER)
        assert "tenant_id" not in payload

    def test_custom_expiry(self):
        token = create_access_token(subject="1", expires_delta=timedelta(hours=1))
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience=JWT_AUDIENCE, issuer=JWT_ISSUER)
        assert "exp" in payload


class TestCreateRefreshToken:
    def test_basic(self):
        token = create_refresh_token(subject="1")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_has_type_refresh(self):
        token = create_refresh_token(subject="1")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience=JWT_AUDIENCE, issuer=JWT_ISSUER)
        assert payload.get("type") == "refresh"

    def test_preserves_is_admin_and_tenant(self):
        token = create_refresh_token(subject="7", is_admin=True, tenant_id=7)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience=JWT_AUDIENCE, issuer=JWT_ISSUER)
        assert payload.get("is_admin") is True
        assert payload.get("tenant_id") == 7

    def test_default_is_admin_false(self):
        token = create_refresh_token(subject="1")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience=JWT_AUDIENCE, issuer=JWT_ISSUER)
        assert payload.get("is_admin") is False
        assert "tenant_id" not in payload


# ---------------------------------------------------------------------------
# Token fingerprint
# ---------------------------------------------------------------------------


class TestFingerprintToken:
    def test_returns_string(self):
        fp = fingerprint_token("some_token")
        assert isinstance(fp, str)
        assert len(fp) == 16

    def test_deterministic(self):
        fp1 = fingerprint_token("token123")
        fp2 = fingerprint_token("token123")
        assert fp1 == fp2

    def test_different_tokens_different_fp(self):
        fp1 = fingerprint_token("token1")
        fp2 = fingerprint_token("token2")
        assert fp1 != fp2


# ---------------------------------------------------------------------------
# decode_token
# ---------------------------------------------------------------------------


class TestDecodeToken:
    def test_valid_token(self):
        r = _make_redis_mock(exists_return=0)
        with _patch_get_redis(r):
            token = create_access_token(subject="42", is_admin=False)
            import asyncio

            payload = asyncio.run(decode_token(token))
            assert payload["sub"] == "42"

    def test_invalid_token(self):
        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(decode_token("not.a.valid.token"))
        assert exc_info.value.status_code == 401

    def test_none_token(self):
        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(decode_token(None))
        assert exc_info.value.status_code == 401

    def test_non_string_token(self):
        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(decode_token(123))
        assert exc_info.value.status_code == 401

    def test_revoked_token(self):
        r = _make_redis_mock(exists_return=1)
        with _patch_get_redis(r):
            token = create_access_token(subject="1")
            with pytest.raises(HTTPException) as exc_info:
                import asyncio

                asyncio.run(decode_token(token))
            assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# refresh token storage
# ---------------------------------------------------------------------------


class TestRefreshTokenStorage:
    def test_get_refresh_token(self):
        r = _make_redis_mock(get_return="token123")
        with _patch_get_redis(r):
            import asyncio

            result = asyncio.run(get_refresh_token(1))
            assert result == "token123"

    def test_get_refresh_token_none(self):
        r = _make_redis_mock(get_return=None)
        with _patch_get_redis(r):
            import asyncio

            result = asyncio.run(get_refresh_token(1))
            assert result is None

    def test_save_refresh_token(self):
        r = _make_redis_mock()
        with _patch_get_redis(r):
            import asyncio

            result = asyncio.run(save_refresh_token(1, "token123"))
            assert result is True

    def test_no_redis_returns_none(self):
        r = AsyncMock()
        r.return_value = None
        with _patch_get_redis(r):
            import asyncio

            result = asyncio.run(get_refresh_token(1))
            assert result is None

    def test_no_redis_save_returns_false(self):
        r = AsyncMock(return_value=None)
        with _patch_get_redis(r):
            import asyncio

            result = asyncio.run(save_refresh_token(1, "token123"))
            assert result is False

    def test_revoke_refresh_token(self):
        r = _make_redis_mock()
        with _patch_get_redis(r):
            import asyncio

            result = asyncio.run(revoke_refresh_token(1))
            assert result is True


# ---------------------------------------------------------------------------
# JWT blacklist
# ---------------------------------------------------------------------------


class TestJwtBlacklist:
    def test_revoke_token(self):
        from bike_analyzer.backend.security import _memory_revoked_tokens

        _memory_revoked_tokens.clear()
        r = _make_redis_mock()
        with _patch_get_redis(r):
            import asyncio

            result = asyncio.run(revoke_token("jti-123"))
            assert result is True
            assert "jti-123" in _memory_revoked_tokens
        _memory_revoked_tokens.clear()

    def test_revoke_token_no_redis(self):
        from bike_analyzer.backend.security import _memory_revoked_tokens

        _memory_revoked_tokens.clear()
        r = AsyncMock(return_value=None)
        with _patch_get_redis(r):
            import asyncio

            result = asyncio.run(revoke_token("jti-123"))
            # La revoca in-memory di fallback è considerata un successo (ce2dccb):
            # ritorna True anche senza Redis, e il jti resta tracciato in-memory.
            assert result is True
            assert "jti-123" in _memory_revoked_tokens
        _memory_revoked_tokens.clear()

    def test_is_token_revoked_in_memory(self):
        from bike_analyzer.backend.security import _memory_revoked_tokens

        _memory_revoked_tokens.clear()
        _memory_revoked_tokens["revoked-jti"] = time.time()
        r = _make_redis_mock(exists_return=0)
        with _patch_get_redis(r):
            import asyncio

            result = asyncio.run(is_token_revoked("revoked-jti"))
            assert result is True
        _memory_revoked_tokens.clear()

    def test_is_token_not_revoked(self):
        from bike_analyzer.backend.security import _memory_revoked_tokens

        _memory_revoked_tokens.clear()
        r = _make_redis_mock(exists_return=0)
        with _patch_get_redis(r):
            import asyncio

            result = asyncio.run(is_token_revoked("fresh-jti"))
            assert result is False
        _memory_revoked_tokens.clear()


# ---------------------------------------------------------------------------
# TOTP
# ---------------------------------------------------------------------------


class TestTotp:
    def test_generate_secret(self):
        secret = _generate_totp_secret()
        assert isinstance(secret, str)
        assert len(secret) > 10

    def test_generate_totp(self):
        secret = _generate_totp_secret()
        code = generate_totp(secret)
        assert isinstance(code, str)
        assert len(code) == 6
        assert code.isdigit()

    def test_verify_totp_correct(self):
        secret = _generate_totp_secret()
        code = generate_totp(secret)
        assert verify_totp(secret, code) is True

    def test_verify_totp_wrong(self):
        secret = _generate_totp_secret()
        assert verify_totp(secret, "000000") is False

    def test_verify_totp_invalid_format(self):
        secret = _generate_totp_secret()
        assert verify_totp(secret, "abc") is False
        assert verify_totp(secret, "") is False
        assert verify_totp(secret, "12345") is False

    def test_verify_totp_window(self):
        secret = _generate_totp_secret()
        code = generate_totp(secret)
        assert verify_totp(secret, code, window=1) is True

    def test_hotp_counter(self):
        secret = _generate_totp_secret()
        c1 = _hotp(secret, 1000)
        c2 = _hotp(secret, 1001)
        assert isinstance(c1, str)
        assert len(c1) == 6
        assert c1 != c2

    def test_get_totp_secret_key(self):
        key = get_totp_secret_key(42)
        assert key == "bikemaster:2fa:secret:42"

    def test_provisioning_uri(self):
        secret = _generate_totp_secret()
        uri = provisioning_uri(secret, 42)
        assert uri.startswith("otpauth://totp/")
        assert "secret=" in uri
        assert "BikeMaster" in uri


class TestTotpRedis:
    def test_save_and_get_totp_secret(self):
        r = _make_redis_mock(set_return=True, get_return="secret123")
        # Override get to return different values for set vs get calls
        r.get = AsyncMock(side_effect=["secret123", None])
        r.set = AsyncMock(return_value=True)
        with _patch_get_redis(r):
            import asyncio

            result = asyncio.run(save_totp_secret(42, "secret123"))
            assert result is True

    def test_get_totp_secret(self):
        r = _make_redis_mock(get_return="stored_secret")
        with _patch_get_redis(r):
            import asyncio

            result = asyncio.run(get_totp_secret(42))
            assert result == "stored_secret"

    def test_delete_totp_secret(self):
        r = _make_redis_mock()
        with _patch_get_redis(r):
            import asyncio

            result = asyncio.run(delete_totp_secret(42))
            assert result is True

    def test_no_redis_totp_returns_none(self):
        r = AsyncMock(return_value=None)
        r.return_value = None
        with _patch_get_redis(r):
            import asyncio

            result = asyncio.run(get_totp_secret(42))
            assert result is None
