"""JWT authentication, authorization, and session management.

Questo modulo fornisce:

- Generazione e validazione di access token JWT (HS256) con ``python-jose``.
- Hashing e verifica password con ``bcrypt``.
- Revoca token tramite blacklist in-memory + Redis (per logout e sicurezza).
- Gestione refresh token con limite di sessioni attive per atleta.
- Autenticazione a due fattori (TOTP/2FA) implementata con solo librerie
  standard (``hmac``, ``hashlib``) — nessuna dipendenza aggiuntiva.
- Cookie HttpOnly sicuri per il frontend (access + refresh).

I token JWT includono i claim standard (``sub``, ``iat``, ``exp``, ``iss``,
``aud``, ``jti``) piu' i campi custom ``is_admin``, ``is_client`` e
``tenant_id`` per l'isolamento multi-tenant.
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
# Durata di validità di un refresh token (30 giorni), allineata a create_refresh_token.
REFRESH_TTL = 86400 * 30
# Numero massimo di sessioni/refresh token attivi per atleta (FIFO in save_refresh_token).
REFRESH_MAX_ACTIVE = 5


def _sweep_revoked_tokens() -> None:
    """Rimuovi token revocati scaduti dalla blacklist in-memory.

    La soglia di stale e' ``JWT_BLACKLIST_TTL * 2`` per garantire che i token
    ancora validi non vengano eliminati prematuramente. Viene chiamata
    automaticamente ogni 100 inserimenti.
    """
    now = time.time()
    cutoff = now - (JWT_BLACKLIST_TTL * 2)
    stale = [jti for jti, ts in _memory_revoked_tokens.items() if ts < cutoff]
    for jti in stale:
        del _memory_revoked_tokens[jti]
    if stale:
        logger.debug("Swept %d stale revoked tokens from memory", len(stale))


async def get_refresh_token(athlete_id: int) -> str | None:
    """Recupera il refresh token attivo per un atleta da Redis.

    Restituisce ``None`` se Redis non e' disponibile o se l'atleta non ha
    un refresh token salvato.
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
    """Salva un nuovo refresh token per un atleta in Redis.

    Mantiene fino a ``REFRESH_MAX_ACTIVE`` token per atleta, rimuovendo il
    piu' vecchio quando il limite viene superato. Il token piu' recente e'
    sempre accessibile direttamente tramite la chiave ``REFRESH_PREFIX``.
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
    """Revoca tutti i refresh token di un atleta (logout definitivo).

    Elimina sia il token corrente che la lista dei token attivi da Redis.
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
    """Inserisce un JWT nella blacklist di revoca.

    Il token viene marcato come revocato sia in-memory (per performance)
    che su Redis (per istanze multiple). La blacklist ha un TTL di
    ``JWT_BLACKLIST_TTL`` secondi, dopodiche' il token scade naturalmente
    e puo' essere rimosso dalla memoria.
    """
    _memory_revoked_tokens[jti] = time.time()
    if len(_memory_revoked_tokens) % 100 == 0:
        _sweep_revoked_tokens()
    r = await get_redis()
    if r is None:
        logger.warning("Redis unavailable: token revocation is in-memory only for jti=%s", jti)
        return True
    try:
        await _await_if_needed(r.set(jti_key(jti), "1", ex=ttl))
        return True
    except Exception as exc:
        logger.warning("Failed to revoke token %s: %s", jti, exc)
        return False


async def is_token_revoked(jti: str) -> bool:
    if jti in _memory_revoked_tokens:
        _sweep_revoked_tokens()
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
    """Genera l'hash bcrypt di una password in chiaro.

    Utilizza il costo di default di bcrypt (rounds=12). L'output e' una
    stringa UTF-8 pronta per essere salvata nel database.
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica che una password in chiaro corrisponda all'hash salvato.

    Gestisce anche hash vuoti/non validi restituendo ``False`` invece di
    sollevare eccezioni, per evitare side-channel attacks.
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
) -> str:
    """Genera un access token JWT (HS256) per l'utente specificato.

    Il token include i claim standard (``sub``, ``iat``, ``exp``, ``iss``,
    ``aud``, ``jti``) piu' i campi custom ``is_admin``, ``is_client`` e
    ``tenant_id``. Se ``jti`` non e' fornito viene generato un identificativo
    univoco basato su SHA-256. La scadenza predefinita e' configurata da
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
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    subject: str, is_admin: bool = False, tenant_id: int | None = None, is_client: bool = False
) -> str:
    """Genera un refresh token JWT con durata di 30 giorni.

    Simile a ``create_access_token`` ma con claim ``type="refresh"`` e
    scadenza estesa. Usato per ottenere nuovi access token senza richiedere
    nuovamente le credenziali.
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
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _try_decode(token: str, secret: str) -> dict | None:
    """Decodifica un JWT con la chiave specificata, restituendo None in caso di errore.

    Utilizzato internamente per supportare il fallback tra chiavi vecchie e
    nuove durante la rotazione dei segreti JWT.
    """
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM], issuer=JWT_ISSUER, audience=JWT_AUDIENCE)
    except JWTError:
        return None


async def decode_token_with_fallback(token: str | None) -> dict | None:
    """Decodifica un JWT con fallback sulla chiave precedente.

    Durante la rotazione dei segreti JWT, i token emessi con la chiave
    vecchia devono rimanere validi fino a scadenza. Questa funzione tenta
    prima con ``SECRET_KEY`` corrente, poi con ``SECRET_KEY_PREVIOUS`` se
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
    """Decodifica e valida un access token JWT.

    Verifica la firma, la scadenza, l'issuer e l'audience. Inoltre controlla
    che il token non sia stato revocato tramite blacklist. Solleva
    ``HTTPException`` con status 401 in caso di token non valido, scaduto o
    revocato.
    """
    if not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token non valido o scaduto",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = await decode_token_with_fallback(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token non valido o scaduto",
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
    """Dependency FastAPI per ottenere l'utente autenticato dal token JWT.

    Supporta il token sia nell'header Authorization che nel cookie
    ``bikemaster_access``. Restituisce un dict con ``id``, ``is_admin``,
    ``is_client`` e opzionalmente ``tenant_id``. Solleva 401 se il token
    non e' valido.
    """
    cookie_token = request.cookies.get("bikemaster_access")
    active_token = cookie_token or token
    payload = await decode_token(active_token)
    user_id: str = payload.get("sub")
    is_admin: bool = payload.get("is_admin", False)
    is_client: bool = payload.get("is_client", False)
    tenant_id: int | None = payload.get("tenant_id")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token non valido")
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token non valido") from exc
    result = {"id": user_id_int, "is_admin": is_admin, "is_client": is_client}
    if tenant_id is not None:
        result["tenant_id"] = tenant_id
    return result


async def get_admin_user(request: Request, token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency FastAPI che richiede privilegi di amministratore.

    Estende ``get_current_user`` verificando che il claim ``is_admin`` sia
    ``True``. Solleva 403 se l'utente autenticato non e' admin.
    """
    user = await get_current_user(request, token)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accesso amministratore richiesto")
    return user


async def get_optional_current_user(request: Request, token: str | None = Depends(oauth2_scheme)) -> dict | None:
    """Dependency FastAPI opzionale per l'utente autenticato.

    Se un token valido e' presente, restituisce l'utente; altrimenti
    restituisce ``None`` senza sollevare eccezioni. Utile per endpoint
    pubblici che hanno comportamenti diversi per utenti autenticati.
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
    # Deriva il segreto da SECRET_KEY + entropia temporale, poi lo codifica in Base32
    # (RFC 4226) troncando a 20 byte — lunghezza standard per i segreti TOTP.
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
    # HMAC-based One-Time Password (RFC 4226). Calcola HMAC-SHA256 sul counter a
    # 64 bit big-endian, poi applica l'algoritmo di "dynamic truncation" (RFC 4226
    # §5.3): l'ultimo nibble di H sceglie un offset, da cui si estraggono 31 bit
    # (il bit alto azzerato per evitare il segno) e si riducono a `digits` cifre.
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
    """Genera un codice TOTP (Time-based One-Time Password, RFC 6238).

    Il codice e' valido per ``period`` secondi e utilizza l'algoritmo di
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
    """Verifica un codice TOTP con tolleranza di clock drift.

    Accetta codici validi nell'intorno di ``window`` periodi prima/dopo
    il tempo corrente, per gestire lo drift tra i clock del client e del
    server. Usa ``hmac.compare_digest`` per prevenire timing attacks.
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
    """Genera l'URI ``otpauth://`` per la configurazione dell'app authenticator.

    L'URI e' compatibile con Google Authenticator, Authy e altri client
    TOTP standard. Include algoritmo SHA-256, 6 cifre e periodo di 30s.
    """
    return f"otpauth://totp/{issuer}:user{user_id}?secret={secret}&issuer={issuer}&algorithm=sha256&digits=6&period=30"


def _cookie_secure() -> bool:
    env = os.getenv("ENVIRONMENT", "development")
    return env.lower() in ("production", "prod", "staging")


def set_auth_cookies(response: Response, access_token: str, refresh_token: str | None = None) -> None:
    """Imposta i cookie HttpOnly per l'accesso e il refresh token.

    In produzione i cookie sono ``secure`` e ``samesite=none`` per supportare
    i cross-site requests; in sviluppo sono ``samesite=lax`` e non secure.
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
    """Cancella i cookie di autenticazione dal browser del client.

    Rimuove sia il cookie di accesso che quello di refresh, forzando il
    logout dal lato client.
    """
    response.delete_cookie(key="bikemaster_access", path="/")
    response.delete_cookie(key="bikemaster_refresh", path="/api/v1/auth")
