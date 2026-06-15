"""JWT authentication helpers.

Lightweight implementation using python-jose with HS256.
Password hashing uses bcrypt directly for maximum compatibility.
Includes token blacklist support for logout revocation via Redis.
TOTP/2FA is implemented with stdlib only (hmac/hashlib) — no third-party deps.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import inspect
import logging
import struct
import time
from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from .config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    SECRET_KEY,
    SECRET_KEY_PREVIOUS,
)
from .redis_client import get_redis

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


JWT_BLACKLIST_PREFIX = "bikemaster:jwt:blacklist:"
JWT_BLACKLIST_TTL = 7200
_memory_revoked_tokens: set[str] = set()
REFRESH_PREFIX = "bikemaster:refresh:"
REFRESH_TTL = 86400 * 30
REFRESH_MAX_ACTIVE = 5


async def get_refresh_token(athlete_id: int) -> str | None:
    r = await get_redis()
    if r is None:
        return None
    try:
        return await _await_if_needed(r.get(f"{REFRESH_PREFIX}{athlete_id}"))
    except Exception:
        return None


async def save_refresh_token(athlete_id: int, refresh_token: str, ttl: int = REFRESH_TTL) -> bool:
    r = await get_redis()
    if r is None:
        return False
    try:
        tokens_raw = await r.get(f"{REFRESH_PREFIX}{athlete_id}:tokens")
        tokens = set(tokens_raw.split(",")) if tokens_raw else set()
        tokens.add(refresh_token)
        if len(tokens) > REFRESH_MAX_ACTIVE:
            oldest = tokens.pop()
        await r.set(f"{REFRESH_PREFIX}{athlete_id}", refresh_token, ex=ttl)
        await r.set(f"{REFRESH_PREFIX}{athlete_id}:tokens", ",".join(tokens), ex=ttl)
        return True
    except Exception:
        return False


async def revoke_refresh_token(athlete_id: int) -> bool:
    r = await get_redis()
    if r is None:
        return False
    try:
        await r.delete(f"{REFRESH_PREFIX}{athlete_id}")
        await r.delete(f"{REFRESH_PREFIX}{athlete_id}:tokens")
        return True
    except Exception:
        return False

UNAUTH_401 = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token non valido o scaduto",
    headers={"WWW-Authenticate": "Bearer"},
)
UNAUTH_401_REVOKED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token revocato",
    headers={"WWW-Authenticate": "Bearer"},
)


def jti_key(jti: str) -> str:
    return f"{JWT_BLACKLIST_PREFIX}{jti}"


async def revoke_token(jti: str, ttl: int = JWT_BLACKLIST_TTL) -> bool:
    _memory_revoked_tokens.add(jti)
    r = await get_redis()
    if r is None:
        return True
    try:
        await _await_if_needed(r.set(jti_key(jti), "1", ex=ttl))
        return True
    except Exception as exc:
        logger.warning("Failed to revoke token %s: %s", jti, exc)
        return True


async def is_token_revoked(jti: str) -> bool:
    if jti in _memory_revoked_tokens:
        return True
    r = await get_redis()
    if r is None:
        return False
    try:
        return bool(await _await_if_needed(r.exists(jti_key(jti))))
    except Exception as exc:
        logger.warning("Failed to check token revocation %s: %s", jti, exc)
        return False


async def _await_if_needed(value):
    if inspect.isawaitable(value):
        return await value
    return value


def fingerprint_token(token: str) -> str:
    raw = f"{token}:{SECRET_KEY}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(
    subject: str,
    is_admin: bool = False,
    expires_delta: timedelta | None = None,
    jti: str | None = None,
) -> str:
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": subject,
        "is_admin": is_admin,
        "iat": datetime.now(UTC),
        "exp": expire,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    if jti is not None:
        payload["jti"] = jti
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=30)
    payload = {
        "sub": subject,
        "is_admin": False,
        "type": "refresh",
        "iat": datetime.now(UTC),
        "exp": expire,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _try_decode(token: str, secret: str) -> dict | None:
    try:
        return jwt.decode(
            token, secret, algorithms=[ALGORITHM], issuer=JWT_ISSUER, audience=JWT_AUDIENCE
        )
    except JWTError:
        return None


async def decode_token(token: str | None) -> dict:
    if not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token non valido o scaduto",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _try_decode(token, SECRET_KEY)
    if payload is not None:
        jti = payload.get("jti")
        if jti and await is_token_revoked(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token revocato",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    if SECRET_KEY_PREVIOUS:
        payload = _try_decode(token, SECRET_KEY_PREVIOUS)
        if payload is not None:
            jti = payload.get("jti")
            if jti and await is_token_revoked(jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token revocato",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return payload
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token non valido o scaduto",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = await decode_token(token)
    user_id: str = payload.get("sub")
    is_admin: bool = payload.get("is_admin", False)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token non valido")
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token non valido"
        ) from exc
    return {"id": user_id_int, "is_admin": is_admin}


async def get_admin_user(token: str = Depends(oauth2_scheme)) -> dict:
    user = await get_current_user(token)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accesso amministratore richiesto")
    return user


async def get_optional_current_user(token: str | None = Depends(oauth2_scheme)) -> dict | None:
    if not token:
        return None
    try:
        return await get_current_user(token)
    except HTTPException:
        return None


TOTP_ISSUER = "BikeMaster"
TOTP_KEY_PREFIX = "bikemaster:2fa:secret:"


def _generate_totp_secret() -> str:
    raw = hashlib.sha256(SECRET_KEY.encode()).digest() + hashlib.sha256(str(time.time()).encode()).digest()
    return base64.b32encode(raw[:20]).decode("utf-8").rstrip("=")


def get_totp_secret_key(user_id: int) -> str:
    return f"{TOTP_KEY_PREFIX}{user_id}"


async def get_totp_secret(user_id: int) -> str | None:
    r = await get_redis()
    if r is None:
        return None
    try:
        val = await r.get(get_totp_secret_key(user_id))
        return val
    except Exception as exc:
        logger.warning("TOTP secret fetch failed: %s", exc)
        return None


async def save_totp_secret(user_id: int, secret: str) -> bool:
    r = await get_redis()
    if r is None:
        return False
    try:
        await r.set(get_totp_secret_key(user_id), secret)
        return True
    except Exception as exc:
        logger.warning("TOTP secret save failed: %s", exc)
        return False


async def delete_totp_secret(user_id: int) -> bool:
    r = await get_redis()
    if r is None:
        return False
    try:
        await r.delete(get_totp_secret_key(user_id))
        return True
    except Exception as exc:
        logger.warning("TOTP secret delete failed: %s", exc)
        return False


def _hotp(secret: str, counter: int, digits: int = 6, algorithm: str = "sha256") -> str:
    key = base64.b32decode(secret.upper().replace(" ", ""))
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, getattr(hashlib, algorithm)).digest()
    offset = h[-1] & 0xF
    code = (
        ((h[offset] & 0x7F) << 24)
        | ((h[offset + 1] & 0xFF) << 16)
        | ((h[offset + 2] & 0xFF) << 8)
        | (h[offset + 3] & 0xFF)
    )
    return str(code % 10**digits).zfill(digits)


def generate_totp(secret: str, period: int = 30, digits: int = 6, algorithm: str = "sha256") -> str:
    counter = int(time.time()) // period
    return _hotp(secret, counter, digits=digits, algorithm=algorithm)


def verify_totp(
    secret: str,
    code: str,
    period: int = 30,
    digits: int = 6,
    algorithm: str = "sha256",
    window: int = 1,
) -> bool:
    if not code or not code.isdigit() or len(code) != digits:
        return False
    counter = int(time.time()) // period
    for offset in range(-window, window + 1):
        expected = _hotp(secret, counter + offset, digits=digits, algorithm=algorithm)
        if hmac.compare_digest(expected, code):
            return True
    return False


def provisioning_uri(secret: str, user_id: int, issuer: str = TOTP_ISSUER) -> str:
    return f"otpauth://totp/{issuer}:user{user_id}?secret={secret}&issuer={issuer}&algorithm=sha256&digits=6&period=30"
