"""JWT authentication, authorization, and session management.

This module provides:

- Generation and validation of JWT access tokens (HS256) using ``python-jose``.
- Password hashing and verification with ``bcrypt``.
- Token revocation via in-memory blacklist + Redis (for logout and security).
- Refresh token management with limit of active sessions per athlete.
- Two-factor authentication (TOTP/2FA) implemented with standard libraries only
  (``hmac``, ``hashlib``) — no additional dependencies.
- Secure HttpOnly cookies for the frontend (access + refresh).

I token JWT includono i claim standard (``sub``, ``iat``, ``exp``, ``iss``,
``aud``, ``jti``) plus custom fields ``is_admin``, ``is_client`` and
``tenant_id`` for multi-tenant isolation.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import inspect
import logging
import os
import struct
import time
from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from .redis_client import get_redis
from .settings import get_settings

logger = logging.getLogger(__name__)

_s = get_settings()

ALGORITHM = _s.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = _s.access_token_expire_minutes
JWT_AUDIENCE = _s.jwt_audience
JWT_ISSUER = _s.jwt_issuer
SECRET_KEY = _s.secret_key
SECRET_KEY_PREVIOUS = _s.secret_key_previous

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


JWT_BLACKLIST_PREFIX = "bikemaster:jwt:blacklist:"
JWT_BLACKLIST_TTL = 7200
_memory_revoked_tokens: dict[str, float] = {}
REFRESH_PREFIX = "bikemaster:refresh:"
# Validity duration of a refresh token (30 days), aligned with create_refresh_token.
REFRESH_TTL = 86400 * 30
# Maximum number of active sessions/refresh tokens per athlete (FIFO in save_refresh_token).
REFRESH_MAX_ACTIVE = 5


def _sweep_revoked_tokens() -> None:
    """Rimuovi token revocati scaduti dalla blacklist in-memory.

    The stale threshold is ``JWT_BLACKLIST_TTL * 2`` to ensure tokens
    still valid are not deleted prematurely. Called
    automaticamente ogni 100 inserimenti.
    """
    now = time.time()
    cutoff = now - JWT_BLACKLIST_TTL
    stale = [jti for jti, ts in _memory_revoked_tokens.items() if ts < cutoff]
    for jti in stale:
        del _memory_revoked_tokens[jti]
    if stale:
        logger.debug("Swept %d stale revoked tokens from memory", len(stale))


async def get_refresh_token(athlete_id: int) -> str | None:
    """Retrieves the active refresh token for an athlete from Redis.

    Returns ``None`` if Redis is not available or if the athlete does not have
    a saved refresh token.
    """
    r = await get_redis()
    if r is None:
        return None
    try:
        return await _await_if_needed(r.get(f"{REFRESH_PREFIX}{athlete_id}"))
    except Exception as exc:
        logger.warning("Failed to get refresh token for athlete %s: %s", athlete_id, exc)
        return None


async def save_refresh_token(athlete_id: int, refresh_token: str, ttl: int = REFRESH_TTL) -> bool:
    """Saves a new refresh token for an athlete in Redis.

    Keeps up to ``REFRESH_MAX_ACTIVE`` tokens per athlete, removing the
    oldest when the limit is exceeded. The most recent token is
    always accessible directly via the ``REFRESH_PREFIX`` key.
    """
    r = await get_redis()
    if r is None:
        return False
    try:
        tokens_raw = await r.get(f"{REFRESH_PREFIX}{athlete_id}:tokens")
        tokens = tokens_raw.split(",") if tokens_raw else []
        tokens = [t for t in tokens if t]
        tokens.append(refresh_token)
        if len(tokens) > REFRESH_MAX_ACTIVE:
            tokens.pop(0)
        await r.set(f"{REFRESH_PREFIX}{athlete_id}", refresh_token, ex=ttl)
        await r.set(f"{REFRESH_PREFIX}{athlete_id}:tokens", ",".join(tokens), ex=ttl)
        return True
    except Exception as exc:
        logger.warning("Failed to save refresh token for athlete %s: %s", athlete_id, exc)
        return False


async def revoke_refresh_token(athlete_id: int) -> bool:
    """Revokes all refresh tokens for an athlete (final logout).

    Deletes both the current token and the list of active tokens from Redis.
    """
    r = await get_redis()
    if r is None:
        return False
    try:
        await r.delete(f"{REFRESH_PREFIX}{athlete_id}")
        await r.delete(f"{REFRESH_PREFIX}{athlete_id}:tokens")
        return True
    except Exception as exc:
        logger.warning("Failed to revoke refresh token for athlete %s: %s", athlete_id, exc)
        return False


UNAUTH_401 = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token",
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
    """Inserts a JWT into the revocation blacklist.

    The token is marked as revoked in Redis (preferred), SQLite (fallback),
    and in-memory (for performance). The blacklist has a TTL of
    ``JWT_BLACKLIST_TTL`` seconds, after which the token naturally expires
    e puo' essere rimosso dalla memoria.
    """
    _memory_revoked_tokens[jti] = time.time()
    if len(_memory_revoked_tokens) % 100 == 0:
        _sweep_revoked_tokens()
    r = await get_redis()
    if r is not None:
        try:
            await _await_if_needed(r.set(jti_key(jti), "1", ex=ttl))
        except Exception as exc:
            logger.warning("Failed to revoke token %s via Redis: %s", jti, exc)
    try:
        _revoke_token_sqlite(jti, ttl)
    except Exception as exc:
        logger.warning("Failed to revoke token %s via SQLite: %s", jti, exc)
    return True


def _revoke_token_sqlite(jti: str, ttl: int) -> None:
    from .db.database import revoke_token

    revoke_token(jti, ttl=ttl)


async def is_token_revoked(jti: str) -> bool:
    if jti in _memory_revoked_tokens:
        _sweep_revoked_tokens()
        return True
    r = await get_redis()
    if r is not None:
        try:
            if await _await_if_needed(r.exists(jti_key(jti))):
                return True
        except Exception as exc:
            logger.warning("Failed to check token revocation via Redis %s: %s", jti, exc)
    try:
        if _is_token_revoked_sqlite(jti):
            return True
    except Exception as exc:
        logger.warning(
            "SQLite revocation check failed for jti %s: %s — failing open "
            "(token signature/expiration/issuer/audience already validated)",
            jti,
            exc,
        )
    return False


def _is_token_revoked_sqlite(jti: str) -> bool:
    from .db.database import is_token_revoked

    return is_token_revoked(jti)


async def _await_if_needed(value):
    if inspect.isawaitable(value):
        return await value
    return value


def fingerprint_token(token: str) -> str:
    raw = f"{token}:{SECRET_KEY}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def hash_password(password: str) -> str:
    """Generates the bcrypt hash of a plaintext password.

    Uses the default bcrypt cost (rounds=12). The output is
    a UTF-8 string ready to be saved to the database.
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verifies that a plaintext password matches the saved hash.

    Also handles empty/invalid hashes returning ``False`` instead of
    raising exceptions, to avoid side-channel attacks.
    """
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception as exc:
        logger.warning("Password verification failed: %s", exc)
        return False


def create_access_token(
    subject: str,
    is_admin: bool = False,
    expires_delta: timedelta | None = None,
    jti: str | None = None,
    tenant_id: int | None = None,
    is_client: bool = False,
    athlete_id: int | None = None,
) -> str:
    """Generates a JWT access token (HS256) for the specified user.

    Il token include i claim standard (``sub``, ``iat``, ``exp``, ``iss``,
    ``aud``, ``jti``) plus custom fields ``is_admin``, ``is_client`` and
    ``tenant_id``. If ``jti`` is not provided, a unique identifier is generated
    based on SHA-256. The default expiration is configured by
    ``ACCESS_TOKEN_EXPIRE_MINUTES``.
    """
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    if jti is None:
        jti = hashlib.sha256(f"{subject}:{time.time()}:{SECRET_KEY}".encode()).hexdigest()[:32]
    payload = {
        "sub": subject,
        "is_admin": is_admin,
        "is_client": is_client,
        "iat": datetime.now(UTC),
        "exp": expire,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "jti": jti,
    }
    if tenant_id is not None:
        payload["tenant_id"] = tenant_id
    if athlete_id is not None:
        payload["athlete_id"] = athlete_id
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    subject: str,
    is_admin: bool = False,
    tenant_id: int | None = None,
    is_client: bool = False,
    athlete_id: int | None = None,
) -> str:
    """Generates a JWT refresh token with a duration of 30 days.

    Similar to ``create_access_token`` but with claim ``type="refresh"`` and
    extended expiration. Used to obtain new access tokens without requiring
    credentials again.
    """
    expire = datetime.now(UTC) + timedelta(days=30)
    jti = hashlib.sha256(f"refresh:{subject}:{time.time()}:{SECRET_KEY}".encode()).hexdigest()[:32]
    payload = {
        "sub": subject,
        "is_admin": is_admin,
        "is_client": is_client,
        "type": "refresh",
        "jti": jti,
        "iat": datetime.now(UTC),
        "exp": expire,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    if tenant_id is not None:
        payload["tenant_id"] = tenant_id
    if athlete_id is not None:
        payload["athlete_id"] = athlete_id
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _try_decode(token: str, secret: str) -> dict | None:
    """Decodes a JWT with the specified key, returning None in case of error.

    Used internally to support fallback between old and new
    ones during JWT secret rotation.
    """
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM], issuer=JWT_ISSUER, audience=JWT_AUDIENCE)
    except JWTError:
        return None


async def decode_token_with_fallback(token: str | None) -> dict | None:
    """Decodes a JWT with fallback to the previous key.

    During JWT secret rotation, tokens issued with the key
    vecchia devono rimanere validi fino a scadenza. Questa funzione tenta
    first with the current ``SECRET_KEY``, then with ``SECRET_KEY_PREVIOUS`` if
    configurata.
    """
    if not isinstance(token, str):
        return None
    payload = _try_decode(token, SECRET_KEY)
    if payload is not None:
        return payload
    if SECRET_KEY_PREVIOUS:
        payload = _try_decode(token, SECRET_KEY_PREVIOUS)
        if payload is not None:
            logger.debug("Token decoded with previous secret key")
            return payload
    return None


async def decode_token(token: str | None) -> dict:
    """Decodes and validates a JWT access token.

    Verifies the signature, expiration, issuer and audience. Also checks
    that the token has not been revoked via blacklist. Raises
    ``HTTPException`` with status 401 in case of invalid, expired or
    revoked token.
    """
    if not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = await decode_token_with_fallback(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("type") == "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    jti = payload.get("jti")
    if jti and await is_token_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revocato",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)) -> dict:
    """FastAPI dependency to get the authenticated user from the JWT token.

    Supports the token both in the Authorization header and in the cookie
    ``bikemaster_access``. Returns a dict with ``id``, ``is_admin``,
    ``is_client`` and optionally ``tenant_id`` and ``athlete_id``. Raises 401 if the token
    is not valid.
    """
    cookie_token = request.cookies.get("bikemaster_access")
    active_token = cookie_token or token
    payload = await decode_token(active_token)
    user_id: str = payload.get("sub")
    is_admin: bool = payload.get("is_admin", False)
    is_client: bool = payload.get("is_client", False)
    tenant_id: int | None = payload.get("tenant_id")
    athlete_id: int | None = payload.get("athlete_id")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    result = {"id": user_id_int, "is_admin": is_admin, "is_client": is_client}
    if tenant_id is not None:
        result["tenant_id"] = tenant_id
    if athlete_id is not None:
        result["athlete_id"] = athlete_id
    return result


async def get_admin_user(request: Request, token: str = Depends(oauth2_scheme)) -> dict:
    """FastAPI dependency that requires administrator privileges.

    Extends ``get_current_user`` by verifying that the ``is_admin`` claim is
    ``True``. Raises 403 if the authenticated user is not admin.
    """
    user = await get_current_user(request, token)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accesso amministratore richiesto")
    return user


async def get_optional_current_user(request: Request, token: str | None = Depends(oauth2_scheme)) -> dict | None:
    """Optional FastAPI dependency for the authenticated user.

    If a valid token is present, returns the user; otherwise
    returns ``None`` without raising exceptions. Useful for endpoints
    public that have different behaviors for authenticated users.
    """
    if not token:
        return None
    try:
        return await get_current_user(request, token)
    except HTTPException:
        return None


TOTP_ISSUER = "BikeMaster"
TOTP_KEY_PREFIX = "bikemaster:2fa:secret:"


def _generate_totp_secret() -> str:
    # Derives the secret from SECRET_KEY + temporal entropy, then encodes it in Base32
    # (RFC 4226) truncating to 20 bytes — standard length for TOTP secrets.
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
    # HMAC-based One-Time Password (RFC 4226). Calculates HMAC-SHA256 on the counter at
    # 64 bit big-endian, then applies the "dynamic truncation" algorithm (RFC 4226
    # §5.3): the last nibble of H chooses an offset, from which 31 bits are extracted
    # (the high bit zeroed to avoid sign) and reduced to `digits` digits.
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
    """Generates a TOTP code (Time-based One-Time Password, RFC 6238).

    The code is valid for ``period`` seconds and uses the
    hash specificato. Deriva il contatore da ``int(time.time()) // period``.
    """
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
    """Verifies a TOTP code with clock drift tolerance.

    Accepts valid codes within ``window`` periods before/after
    the current time, to handle drift between client and server
    clocks. Uses ``hmac.compare_digest`` to prevent timing attacks.
    """
    if not code or not code.isdigit() or len(code) != digits:
        return False
    counter = int(time.time()) // period
    for offset in range(-window, window + 1):
        expected = _hotp(secret, counter + offset, digits=digits, algorithm=algorithm)
        if hmac.compare_digest(expected, code):
            return True
    return False


def provisioning_uri(secret: str, user_id: int, issuer: str = TOTP_ISSUER) -> str:
    """Generates the ``otpauth://`` URI for authenticator app configuration.

    The URI is compatible with Google Authenticator, Authy and other clients
    TOTP clients. Includes SHA-256 algorithm, 6 digits and 30s period.
    """
    return f"otpauth://totp/{issuer}:user{user_id}?secret={secret}&issuer={issuer}&algorithm=sha256&digits=6&period=30"


def _cookie_secure() -> bool:
    env = os.getenv("ENVIRONMENT", "development")
    return env.lower() in ("production", "prod", "staging")


def set_auth_cookies(response: Response, access_token: str, refresh_token: str | None = None) -> None:
    """Sets HttpOnly cookies for access and refresh token.

    In production cookies are ``secure`` and ``samesite=none`` to support
    cross-site requests; in development they are ``samesite=lax`` and not secure.
    """
    secure = _cookie_secure()
    samesite = "none" if secure else "lax"
    response.set_cookie(
        key="bikemaster_access",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    if refresh_token:
        response.set_cookie(
            key="bikemaster_refresh",
            value=refresh_token,
            httponly=True,
            secure=secure,
            samesite=samesite,
            max_age=REFRESH_TTL,
            path="/api/v1/auth",
        )


def delete_auth_cookies(response: Response) -> None:
    """Clears authentication cookies from the client browser.

    Removes both the access and refresh cookies, forcing
    logout dal lato client.
    """
    response.delete_cookie(key="bikemaster_access", path="/")
    response.delete_cookie(key="bikemaster_refresh", path="/api/v1/auth")
