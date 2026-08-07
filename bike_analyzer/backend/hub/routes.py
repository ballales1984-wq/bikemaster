"""Router principale del backend Hub (cloud, multi-tenant, PostgreSQL).

Espone l'API centrale consumata dal frontend deployato su Vercel:
  - /auth/*       Autenticazione centralizzata (login, register, refresh,
                  logout, profilo, Google OAuth)
  - /admin/*      Operazioni amministrative (atleti, statistiche, backup,
                  analytics CEO)
  - /knowledge/*  Knowledge base condivisa (ricerca vettoriale/BM25,
                  statistiche, reload, embeddings)

Tutti gli endpoint in questo modulo si aspettano che il Hub sia avviato
con ``DATABASE_URL`` configurato (PostgreSQL). SQLite NON e' usato qui.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import UTC, datetime, timedelta
from ipaddress import AddressValueError, ip_address, ip_network
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy import select

from bike_analyzer.backend.analytics.knowledge_base import (
    format_context_for_llm,
    get_kb_stats,
    init_chroma_db,
    init_kb_embeddings,
    reload_kb,
    search_knowledge_base,
)
from bike_analyzer.backend.audit_log import log_action, read_audit_logs
from bike_analyzer.backend.db.async_db import get_session_factory
from bike_analyzer.backend.db.models import (
    AthleteModel,
    ChatHistoryModel,
    RideModel,
    UserModel,
)
from bike_analyzer.backend.rate_limiter import limiter
from bike_analyzer.backend.redis_client import (
    cache_set as _cache_set,
)
from bike_analyzer.backend.redis_client import (
    cached as _cached,
)
from bike_analyzer.backend.redis_client import (
    check_rate_limit,
)
from bike_analyzer.backend.security import (
    ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    create_access_token,
    create_refresh_token,
    decode_token_with_fallback,
    get_admin_user,
    get_current_user,
    hash_password,
    is_token_revoked,
    revoke_refresh_token,
    revoke_token,
    save_refresh_token,
    verify_password,
)
from bike_analyzer.backend.settings import get_settings

_s = get_settings()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers (mirrored from api/routes.py to avoid cross-module coupling)
# ---------------------------------------------------------------------------

_TRUSTED_PROXIES: tuple[str, ...] = (
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.1",
    "::1",
)


def _is_trusted_proxy(ip_str: str) -> bool:
    if ip_str == "testclient":
        return True
    try:
        addr = ip_address(ip_str)
    except (AddressValueError, ValueError):
        return False
    for prefix in _TRUSTED_PROXIES:
        try:
            if addr in ip_network(prefix):
                return True
        except (AddressValueError, ValueError):
            if addr == ip_address(prefix):
                return True
    return False


def _trusted_forwarded_value(request: Request, header: str) -> str | None:
    client_host = request.client.host if request.client else ""
    if not _is_trusted_proxy(client_host):
        return None
    value = request.headers.get(header)
    if not value:
        return None
    return value.split(",", 1)[0].strip()


def _build_redirect_uri(request: Request, path: str) -> str:
    """Costruisce l'URI di redirect completo usando proto e host inoltrati."""
    proto = _trusted_forwarded_value(request, "x-forwarded-proto") or request.url.scheme
    host = _trusted_forwarded_value(request, "x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}{path}"


def _build_oauth_error_url(request: Request, redirect_uri: str, error: str) -> RedirectResponse:
    """Redirect back to the SPA with an ``oauth_error`` query param."""
    parsed = urlparse(redirect_uri)
    if parsed.scheme and parsed.scheme not in ("http", "https"):
        if not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid redirect_uri")
        target = f"{parsed.scheme}://{parsed.netloc}"
        return RedirectResponse(url=f"{target}?{urlencode({'oauth_error': error})}")
    origin = f"{parsed.scheme}://{parsed.netloc or parsed.path.lstrip('/')}/" if parsed.scheme else "/"
    return RedirectResponse(url=f"{origin}?{urlencode({'oauth_error': error})}")


def _build_oauth_success_url(redirect_uri: str, jwt_token: str, email: str, user_id: int) -> str:
    """Build the post-login redirect URL that hands the JWT to the SPA.

    - Mobile / custom app schemes: deliver the token as a query string on the deep-link target.
    - Web SPA: redirect to the SPA origin root with the token in the URL fragment.
    """
    parsed = urlparse(redirect_uri)
    if parsed.scheme and parsed.scheme not in ("http", "https"):
        target = f"{parsed.scheme}://{parsed.netloc or parsed.path.lstrip('/')}"
        return f"{target}?{urlencode({'token': jwt_token, 'email': email or '', 'user_id': str(user_id)})}"

    origin = f"{parsed.scheme}://{parsed.netloc}/" if parsed.scheme else "/"
    return f"{origin}#{urlencode({'token': jwt_token, 'email': email or '', 'user_id': str(user_id)})}"


def _issue_oauth_state(redirect_uri: str, **extra) -> str:
    """Emette un token di stato OAuth firmato con redirect e metadati aggiuntivi."""
    payload = {
        "redirect_uri": redirect_uri,
        "exp": datetime.now(UTC) + timedelta(minutes=10),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "type": "oauth_state",
        **extra,
    }
    return jwt.encode(payload, _s.secret_key, algorithm=ALGORITHM)


def _verify_oauth_state(state: str) -> dict | None:
    """Verifica e decodifica un token di stato OAuth firmato, oppure None se non valido."""
    if not state or "." not in state:
        return None
    try:
        payload = jwt.decode(
            state,
            _s.secret_key,
            algorithms=[ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
        )
        if payload.get("type") != "oauth_state":
            return None
        if "redirect_uri" not in payload:
            return None
        return payload
    except JWTError:
        return None


def _validate_redirect_uri(redirect_uri: str, request: Request) -> None:
    """Valida scheme e host dell'URI di redirect secondo la whitelist configurata."""
    if not redirect_uri:
        raise HTTPException(status_code=400, detail="redirect_uri obbligatoria")
    allowed_schemes = {"http", "https", *set(_s.oauth_redirect_schemes_list)}
    parsed = urlparse(redirect_uri)
    if parsed.scheme not in allowed_schemes:
        raise HTTPException(status_code=400, detail="Scheme non permesso")
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")
    host_lower = parsed.hostname.lower()
    cors_hosts = set()
    try:
        for origin in getattr(_s, "cors_origins_list", []):
            with contextlib.suppress(ValueError):
                cors_hosts.add(urlparse(origin).hostname.lower())
    except Exception:
        logger.debug("Failed to parse CORS origins", exc_info=True)
    configured_hosts = set(getattr(_s, "oauth_allowed_hosts_list", []))
    localhost_ports = {"localhost", "127.0.0.1", "0.0.0.0"}
    if host_lower in localhost_ports:
        return
    allowed_hosts = (
        {
            "bikemaster.onrender.com",
            "bikemaster-api.onrender.com",
            "bikemaster-xi.vercel.app",
            "testserver",
        }
        | cors_hosts
        | configured_hosts
    )
    if host_lower in allowed_hosts:
        return
    if host_lower.endswith(".vercel.app"):
        return
    if host_lower.endswith(".onrender.com"):
        return
    raise HTTPException(status_code=400, detail="Host non autorizzato")


def _validate_frontend_origin(frontend_origin: str | None, request: Request) -> None:
    """Validate that frontend_origin is allowed and matches the current request origin."""
    if not frontend_origin:
        return
    parsed = urlparse(frontend_origin)
    if not parsed.scheme or parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid frontend_origin scheme")
    origin_host = f"{parsed.scheme}://{parsed.netloc}"
    allowed = False
    try:
        cors_list = getattr(_s, "cors_origins_list", [])
        for origin in cors_list:
            if origin.rstrip("/") == origin_host.rstrip("/"):
                allowed = True
                break
    except Exception:
        logger.debug("Failed to parse CORS origins for frontend_origin validation", exc_info=True)
    if not allowed and not parsed.netloc.endswith(".vercel.app"):
        raise HTTPException(status_code=400, detail="Invalid frontend_origin")
    request_origin = request.headers.get("origin") or ""
    if request_origin:
        request_origin = request_origin.rstrip("/")
        if request_origin != origin_host.rstrip("/") and not request_origin.endswith(".vercel.app"):
            logger.warning("frontend_origin mismatch: state=%s request=%s", origin_host, request_origin)


def _public_athlete(athlete: dict | None) -> dict:
    """Restituisce una vista pubblica e sicura dei dati di un atleta."""
    if not athlete:
        return {}
    return {
        "id": athlete.get("id"),
        "name": athlete.get("name", ""),
        "picture": athlete.get("picture"),
        "age": athlete.get("age"),
        "weight_kg": athlete.get("weight_kg"),
        "height_cm": athlete.get("height_cm"),
        "experience_level": athlete.get("experience_level", "Beginner"),
        "goals": athlete.get("goals"),
        "equipment": athlete.get("equipment"),
        "ftp_watts": athlete.get("ftp_watts"),
        "tenant_id": athlete.get("tenant_id", 0),
    }


# ---------------------------------------------------------------------------
# Hub Auth Router
# ---------------------------------------------------------------------------

hub_auth_router = APIRouter(tags=["auth"])


@hub_auth_router.post("/auth/login")
@limiter.limit("5/minute")
async def hub_login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """Hub login — always uses PostgreSQL."""
    from sqlalchemy import select as sa_select

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = sa_select(UserModel).where(UserModel.username == form_data.username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        user_id = user.id if user else "anonymous"
        if not await check_rate_limit(user_id, "/auth/login", limit=5, window=60):
            raise HTTPException(status_code=429, detail="Too many login attempts")

        if not user or not verify_password(form_data.password, user.password_hash or ""):
            raise HTTPException(status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})

        access_token = create_access_token(
            subject=str(user.id), is_admin=user.is_admin, tenant_id=user.id, is_client=user.is_client
        )
        refresh_token = create_refresh_token(
            user.id, is_admin=user.is_admin, tenant_id=user.id, is_client=user.is_client
        )
        await save_refresh_token(user.id, refresh_token)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "username": user.username,
            "id": user.id,
            "is_admin": user.is_admin,
        }


@hub_auth_router.post("/auth/logout")
async def hub_logout(request: Request, current_user: dict = Depends(get_current_user)):
    """Logout Hub: revoca il token di accesso e quello di refresh dell'utente."""
    auth_header = request.headers.get("authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            padding = 4 - len(parts[1]) % 4
            decoded = json.loads(__import__("base64").b64decode(parts[1] + ("=" * padding)))
            jti = decoded.get("jti")
            if jti:
                await revoke_token(jti)
            athlete_id = decoded.get("sub")
            if athlete_id:
                await revoke_refresh_token(int(athlete_id))
    except Exception as exc:
        logger.warning("Hub logout: failed to revoke token: %s", exc)
    return {"msg": "Logged out successfully"}


@hub_auth_router.post("/auth/refresh")
@limiter.limit("10/minute")
async def hub_refresh_token(request: Request, payload: dict = Body(...)):
    """Rinnova l'access token a partire da un refresh token ancora valido."""
    refresh_token = payload.get("refresh_token")
    jwt_payload = await decode_token_with_fallback(refresh_token)
    if not jwt_payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if jwt_payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")
    user_id = jwt_payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    jti = jwt_payload.get("jti")
    if jti and await is_token_revoked(jti):
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    is_admin = bool(jwt_payload.get("is_admin", False))
    is_client = bool(jwt_payload.get("is_client", False))
    tenant_id = jwt_payload.get("tenant_id")
    resolved_tenant = int(tenant_id) if tenant_id is not None else int(user_id)
    return {
        "access_token": create_access_token(
            subject=str(user_id), is_admin=is_admin, tenant_id=resolved_tenant, is_client=is_client
        ),
        "token_type": "bearer",
    }


@hub_auth_router.post("/auth/register")
@limiter.limit("3/minute")
async def hub_register(
    request: Request,
    username: str = Body(..., min_length=3, max_length=64),
    password: str = Body(..., min_length=8, max_length=128),
    email: str = Body(None),
):
    """Registra un nuovo utente (e atleta) sul database Hub PostgreSQL."""
    from sqlalchemy import insert as sa_insert
    from sqlalchemy import select as sa_select

    session_factory = get_session_factory()
    async with session_factory() as session:
        if email:
            stmt = sa_select(UserModel).where((UserModel.username == username) | (UserModel.email == email))
        else:
            stmt = sa_select(UserModel).where(UserModel.username == username)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            detail = "Email already registered" if email and existing.email == email else "Username already exists"
            raise HTTPException(status_code=400, detail=detail)

        password_hash = hash_password(password)
        stmt = (
            sa_insert(UserModel)
            .values(
                username=username,
                email=email,
                password_hash=password_hash,
                is_admin=False,
                is_client=False,
                is_active=True,
                created_at=datetime.now(UTC),
            )
            .returning(UserModel.id)
        )
        result = await session.execute(stmt)
        user_id = result.scalar_one()
        await session.commit()

        athlete = AthleteModel(
            id=user_id,
            name=username,
            email=email,
            experience_level="Beginner",
            tenant_id=user_id,
            created_at=datetime.now(UTC),
        )
        session.add(athlete)
        await session.commit()
        return {
            "username": username,
            "email": email,
            "msg": "Utente creato",
            "is_admin": False,
            "id": user_id,
            "profile_complete": False,
        }


@hub_auth_router.get("/auth/me")
async def hub_get_me(current_user: dict = Depends(get_current_user)):
    """Restituisce il profilo e lo stato dell'utente correntemente autenticato."""
    from sqlalchemy import select as sa_select

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = sa_select(AthleteModel).where(AthleteModel.id == current_user["id"])
        result = await session.execute(stmt)
        athlete = result.scalar_one_or_none()

    if not athlete:
        return {
            "id": current_user["id"],
            "username": "",
            "email": None,
            "picture": None,
            "is_admin": current_user.get("is_admin", False),
            "is_client": current_user.get("is_client", False),
            "tenant_id": current_user.get("tenant_id", current_user["id"]),
            "profile_complete": False,
        }
    profile_complete = (
        athlete.age is not None and athlete.weight_kg is not None and (athlete.experience_level or "").strip() != ""
    )
    return {
        "id": athlete.id,
        "username": athlete.name or "",
        "email": athlete.email,
        "picture": athlete.picture,
        "is_admin": current_user.get("is_admin", False),
        "is_client": current_user.get("is_client", False),
        "tenant_id": current_user.get("tenant_id", current_user["id"]),
        "profile_complete": profile_complete,
    }


@hub_auth_router.put("/auth/profile")
async def hub_update_profile(
    profile_data: dict = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """Aggiorna i campi profilo consentiti dell'atleta autenticato."""
    from sqlalchemy import select as sa_select
    from sqlalchemy import update as sa_update

    allowed_fields = {
        "name",
        "email",
        "age",
        "weight_kg",
        "height_cm",
        "experience_level",
        "goals",
        "preferred_terrain",
        "weekly_volume_km",
        "ftp_watts",
        "equipment",
        "medical_notes",
    }
    update_data = {k: v for k, v in profile_data.items() if k in allowed_fields and v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = sa_update(AthleteModel).where(AthleteModel.id == current_user["id"]).values(**update_data)
        await session.execute(stmt)
        await session.commit()

        stmt = sa_select(AthleteModel).where(AthleteModel.id == current_user["id"])
        result = await session.execute(stmt)
        athlete = result.scalar_one_or_none()

    if not athlete:
        raise HTTPException(status_code=404, detail="User not found")
    return _public_athlete(
        {
            "id": athlete.id,
            "name": athlete.name,
            "email": athlete.email,
            "picture": athlete.picture,
            "age": athlete.age,
            "weight_kg": athlete.weight_kg,
            "height_cm": athlete.height_cm,
            "experience_level": athlete.experience_level,
            "goals": athlete.goals,
            "equipment": athlete.equipment,
            "ftp_watts": athlete.ftp_watts,
            "tenant_id": athlete.tenant_id,
        }
    )


@hub_auth_router.post("/auth/change-password")
async def hub_change_password(
    current_password: str = Body(..., min_length=6, embed=True),
    new_password: str = Body(..., min_length=8, max_length=100, embed=True),
    current_user: dict = Depends(get_current_user),
):
    """Cambia la password dell'utente previa verifica di quella attuale."""
    from sqlalchemy import select as sa_select

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = sa_select(AthleteModel).where(AthleteModel.id == current_user["id"])
        result = await session.execute(stmt)
        athlete = result.scalar_one_or_none()

    if not athlete:
        raise HTTPException(status_code=404, detail="User not found")
    stored_hash = athlete.password_hash or ""
    if not verify_password(current_password, stored_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    new_hash = hash_password(new_password)
    from sqlalchemy import update as sa_update

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = sa_update(AthleteModel).where(AthleteModel.id == current_user["id"]).values(password_hash=new_hash)
        await session.execute(stmt)
        await session.commit()
    return {"msg": "Password changed successfully"}


@hub_auth_router.get("/auth/google")
@limiter.limit("10/minute")
async def hub_google_oauth_login(
    request: Request,
    redirect_uri: str | None = Query(None),
    frontend_origin: str | None = Query(None),
    state: str = "",
):
    """Avvia il flusso OAuth di Google restituendo l'URL di autorizzazione."""
    from bike_analyzer.backend.auth.google_auth import get_google_oauth_url

    if not _s.google_client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")
    redirect_uri = redirect_uri or _build_redirect_uri(request, "/api/v1/auth/google/callback")
    _validate_redirect_uri(redirect_uri, request)
    if frontend_origin:
        _validate_redirect_uri(frontend_origin, request)
    state = _issue_oauth_state(redirect_uri, frontend_origin=frontend_origin)
    auth_url = get_google_oauth_url(_s.google_client_id, redirect_uri=redirect_uri, state=state)
    return {"auth_url": auth_url}


@hub_auth_router.get("/auth/google/callback")
@limiter.limit("10/minute")
async def hub_google_oauth_callback_get(
    request: Request,
    code: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
    redirect_uri: str | None = Query(None),
    state: str = Query(""),
):
    """Gestisce il callback OAuth di Google creando sessione e utente se necessario."""
    from bike_analyzer.backend.auth.google_auth import (
        create_google_session,
        exchange_google_code,
        get_google_user_info,
    )

    if not _s.google_client_id or not _s.google_client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    state_data = _verify_oauth_state(state)
    if not state_data:
        return _build_oauth_error_url(request, redirect_uri or "", "invalid_state")

    redirect_uri = state_data.get("redirect_uri", redirect_uri or "")
    frontend_origin = state_data.get("frontend_origin")
    _validate_redirect_uri(redirect_uri, request)
    _validate_frontend_origin(frontend_origin, request)
    if frontend_origin:
        _validate_redirect_uri(frontend_origin, request)

    error_target = frontend_origin or redirect_uri

    if error:
        message = error_description or error
        return _build_oauth_error_url(request, error_target, message)
    if not code:
        return _build_oauth_error_url(request, error_target, "missing_code")

    cache_key = f"oauth:code:{code}"
    try:
        cached_result = await _cached(cache_key)
        if cached_result:
            return RedirectResponse(url=cached_result["redirect_url"])

        token_data = await asyncio.to_thread(
            exchange_google_code, _s.google_client_id, _s.google_client_secret, code, redirect_uri
        )
    except Exception as exc:
        response = getattr(exc, "response", None)
        error_body = response.text if response is not None else str(exc)
        return _build_oauth_error_url(request, error_target, f"token_exchange_failed:{error_body[:200]}")

    access_token = token_data.get("access_token")
    if not access_token:
        return _build_oauth_error_url(request, error_target, "no_access_token")

    try:
        user_info = await asyncio.to_thread(get_google_user_info, access_token)
    except Exception as exc:
        response = getattr(exc, "response", None)
        error_body = response.text if response is not None else str(exc)
        return _build_oauth_error_url(request, error_target, f"userinfo_failed:{error_body[:200]}")

    google_sub = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name")
    if not google_sub:
        return _build_oauth_error_url(request, error_target, "invalid_user_info")

    from sqlalchemy import select as sa_select

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = sa_select(AthleteModel).where(AthleteModel.email == email)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            from bike_analyzer.backend.redis_client import get_redis

            lock_key = f"oauth:lock:athlete:{email or google_sub}"
            r = await get_redis()
            lock_acquired = True
            if r is not None:
                lock_acquired = await r.set(lock_key, "1", ex=10, nx=True)
            try:
                if lock_acquired:
                    stmt = sa_select(AthleteModel).where(AthleteModel.email == email)
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()
                    if not existing:
                        athlete = AthleteModel(
                            name=name or email or google_sub,
                            email=email,
                            picture=user_info.get("picture"),
                            experience_level="Beginner",
                            created_at=datetime.now(UTC),
                        )
                        session.add(athlete)
                        await session.flush()
                        existing = athlete
            finally:
                if r is not None:
                    await r.delete(lock_key)

        if not existing:
            return _build_oauth_error_url(request, error_target, "user_creation_failed")

        jwt_token = create_google_session(user_info, athlete_id=existing.id)["access_token"]
        redirect_target = frontend_origin or redirect_uri
        redirect_url = _build_oauth_success_url(redirect_target, jwt_token, email or "", existing.id)
        await _cache_set(f"oauth:code:{code}", {"redirect_url": redirect_url}, ttl=300)
        return RedirectResponse(url=redirect_url)


@hub_auth_router.post("/auth/google/code-exchange")
@limiter.limit("10/minute")
async def hub_google_code_exchange(
    request: Request,
    payload: dict = Body(...),
):
    """Scambia il code OAuth di Google per un access token e una sessione locale."""
    code = payload.get("code")
    redirect_uri = payload.get("redirect_uri")
    if not code or not redirect_uri:
        raise HTTPException(status_code=400, detail="code and redirect_uri required")

    from bike_analyzer.backend.auth.google_auth import exchange_google_code, get_google_user_info

    try:
        token_data = await asyncio.to_thread(
            exchange_google_code, _s.google_client_id, _s.google_client_secret, code, redirect_uri
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail="code_exchange_failed") from exc

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="no_access_token")

    try:
        user_info = await asyncio.to_thread(get_google_user_info, access_token)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="userinfo_failed") from exc

    google_sub = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name")
    if not google_sub:
        raise HTTPException(status_code=400, detail="invalid_user_info")

    from sqlalchemy import select as sa_select

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = sa_select(AthleteModel).where(AthleteModel.email == email)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            athlete = AthleteModel(
                name=name or email or google_sub,
                email=email,
                picture=user_info.get("picture"),
                experience_level="Beginner",
                created_at=datetime.now(UTC),
            )
            session.add(athlete)
            await session.flush()
            existing = athlete

        from bike_analyzer.backend.auth.google_auth import create_google_session

        jwt_token = create_google_session(user_info, athlete_id=existing.id)["access_token"]

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "email": email,
        "user_id": existing.id,
    }


# ---------------------------------------------------------------------------
# Hub Admin Router
# ---------------------------------------------------------------------------

hub_admin_router = APIRouter(tags=["admin"])


@hub_admin_router.get("/athletes")
async def hub_list_all_athletes(current_user: dict = Depends(get_admin_user)):
    """Elenca tutti gli atleti presenti nel database Hub (solo admin)."""
    from sqlalchemy import select as sa_select

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = sa_select(AthleteModel)
        result = await session.execute(stmt)
        athletes = result.scalars().all()
    return {
        "athletes": [
            {
                "id": a.id,
                "name": a.name,
                "email": a.email,
                "experience_level": a.experience_level,
                "tenant_id": a.tenant_id,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in athletes
        ]
    }


@hub_admin_router.get("/backup")
async def hub_create_backup(current_user: dict = Depends(get_admin_user)):
    """Esporta un backup JSON di utenti, atleti, ride e cronologia chat (solo admin)."""
    import hashlib
    import logging

    from fastapi.responses import JSONResponse
    from sqlalchemy import select as sa_select

    logger = logging.getLogger(__name__)
    session_factory = get_session_factory()
    async with session_factory() as session:
        users_result = await session.execute(sa_select(UserModel))
        users_result.scalars().all()
        athletes_result = await session.execute(sa_select(AthleteModel))
        athletes_result.scalars().all()
        rides_result = await session.execute(sa_select(RideModel))
        rides_result.scalars().all()
        chat_result = await session.execute(sa_select(ChatHistoryModel))
        chat_result.scalars().all()

    def _dump(model):
        """Serializza le righe di un modello SQLAlchemy in lista di dizionari."""
        return [{c.name: getattr(row, c.name) for c in model.__table__.columns} for row in model]

    payload = {
        "users": _dump(UserModel),
        "athletes": _dump(AthleteModel),
        "rides": _dump(RideModel),
        "chat_history": _dump(ChatHistoryModel),
    }
    backup_hash = hashlib.sha256(str(payload).encode()).hexdigest()[:16]
    log_action(current_user["id"], "download_backup", "database", details={"hash": backup_hash})
    logger.info(
        "Admin user=%s downloaded hub JSON backup hash=%s",
        current_user["id"],
        backup_hash,
    )
    return JSONResponse(content=payload, media_type="application/json")


@hub_admin_router.post("/backup/scheduled")
async def hub_scheduled_backup(current_user: dict = Depends(get_admin_user)):
    """Esegue un backup pianificato e ritorna il conteggio di ride e atleti."""
    from sqlalchemy import func

    session_factory = get_session_factory()
    async with session_factory() as session:
        rides_count = (await session.execute(select(func.count(RideModel.id)))).scalar_one()
        athletes_count = (await session.execute(select(func.count(AthleteModel.id)))).scalar_one()
    log_action(current_user["id"], "scheduled_backup", "database")
    return {
        "status": "scheduled_backup_complete",
        "rides_count": rides_count,
        "athletes_count": athletes_count,
    }


@hub_admin_router.post("/indexes")
async def hub_create_db_indexes(current_user: dict = Depends(get_admin_user)):
    """Crea gli indici PostgreSQL mancanti sulle tabelle principali (solo admin)."""
    from sqlalchemy import text

    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(text("CREATE INDEX IF NOT EXISTS idx_rides_athlete_date ON rides (athlete_id, date)"))
        await session.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_history_athlete ON chat_history (athlete_id)"))
        await session.execute(text("CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_topic ON knowledge_chunks (topic)"))
        await session.commit()
    log_action(current_user["id"], "create_indexes", "database")
    return {"status": "indexes_created"}


@hub_admin_router.get("/stats")
async def hub_get_system_stats(current_user: dict = Depends(get_admin_user)):
    """Restituisce statistiche di sistema aggregate (ride, km, durata, atleti)."""
    from sqlalchemy import select as sa_select

    session_factory = get_session_factory()
    async with session_factory() as session:
        rides_result = await session.execute(sa_select(RideModel))
        rides = rides_result.scalars().all()
        athletes_result = await session.execute(sa_select(AthleteModel))
        athletes = athletes_result.scalars().all()

    total_km = sum(r.distance_km or 0 for r in rides)
    total_duration = sum(r.duration_minutes or 0 for r in rides)
    log_action(current_user["id"], "view_stats", "system")
    return {
        "rides_count": len(rides),
        "total_km": round(total_km, 1),
        "total_duration_hours": round(total_duration / 60, 1),
        "athletes_count": len(athletes),
    }


@hub_admin_router.post("/reset-demo")
async def hub_reset_demo_data(current_user: dict = Depends(get_admin_user)):
    """Cancella i dati demo (ride e chat) dal database Hub (solo admin)."""
    from sqlalchemy import delete as sa_delete

    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(sa_delete(RideModel))
        await session.execute(sa_delete(ChatHistoryModel))
        await session.commit()
    log_action(current_user["id"], "reset_demo", "system")
    return {"status": "demo_reset", "message": "Hub demo data cleared"}


@hub_admin_router.get("/ceo")
async def hub_ceo_analytics(current_user: dict = Depends(get_admin_user)):
    """Calcola le metriche di analytics executive (CEO) su atleti e ride."""
    from sqlalchemy import select as sa_select

    session_factory = get_session_factory()
    async with session_factory() as session:
        rides_result = await session.execute(sa_select(RideModel))
        rides = rides_result.scalars().all()
        athletes_result = await session.execute(sa_select(AthleteModel))
        athletes = athletes_result.scalars().all()

    now = datetime.now(UTC)
    total_rides = len(rides)
    total_athletes = len(athletes)
    total_km = sum(r.distance_km or 0 for r in rides)
    total_hours = sum(r.duration_minutes or 0 for r in rides) / 60
    total_calories = sum(r.calories or 0 for r in rides)
    this_month = sum(1 for r in rides if (r.date or "").startswith(now.strftime("%Y-%m")))
    last_month = sum(
        1
        for r in rides
        if (r.date or "").startswith(f"{now.year}-{now.month - 1:02d}" if now.month > 1 else f"{now.year - 1}-12")
    )
    level_counts = {"Beginner": 0, "Amateur": 0, "Intermediate": 0, "Advanced": 0, "Elite": 0}
    for a in athletes:
        level = a.experience_level or "Beginner"
        if level in level_counts:
            level_counts[level] += 1
    log_action(current_user["id"], "view_ceo_analytics", "system")
    return {
        "overview": {
            "total_athletes": total_athletes,
            "total_rides": total_rides,
            "total_kilometers": round(total_km, 1),
            "total_training_hours": round(total_hours, 1),
            "total_calories_burned": int(total_calories),
        },
        "growth": {
            "rides_this_month": this_month,
            "rides_last_month": last_month,
            "growth_rate": round((this_month - last_month) / last_month * 100, 1) if last_month else 0,
        },
        "engagement": {
            "rides_per_athlete": round(total_rides / total_athletes, 1) if total_athletes else 0,
            "avg_km_per_ride": round(total_km / total_rides, 2) if total_rides else 0,
            "avg_calories_per_ride": int(total_calories / total_rides) if total_rides else 0,
        },
        "athletes_by_level": level_counts,
        "system": {
            "database_type": "PostgreSQL",
            "last_updated": now.isoformat(),
        },
    }


@hub_admin_router.get("/test-sentry")
async def hub_test_sentry(current_user: dict = Depends(get_admin_user)):
    """Invia un evento di test a Sentry per verificarne l'integrazione."""
    import sentry_sdk

    sentry_sdk.capture_exception(Exception("Test Sentry integration - bikemaster hub"))
    return {"status": "test_event_sent", "message": "Check Sentry dashboard for error event"}


@hub_admin_router.get("/audit-logs")
async def hub_get_audit_logs(limit: int = Query(100, ge=1, le=500), current_user: dict = Depends(get_admin_user)):
    """Restituisce gli ultimi log di audit del sistema (solo admin)."""
    log_action(current_user["id"], "view_audit_logs", "audit")
    return {"logs": read_audit_logs(limit=limit)}


# ---------------------------------------------------------------------------
# Hub Knowledge Router
# ---------------------------------------------------------------------------

hub_knowledge_router = APIRouter(tags=["knowledge"])


@hub_knowledge_router.get("/knowledge")
async def hub_list_knowledge():
    """Elenca i topic e le statistiche della knowledge base condivisa."""
    stats = get_kb_stats()
    return {
        "topics": stats["topics"],
        "chunks_per_topic": stats["chunks_per_topic"],
        "total_chunks": stats["total_chunks"],
        "total_words": stats["total_words"],
    }


@hub_knowledge_router.get("/knowledge/search")
@limiter.limit("10/minute")
async def hub_search_knowledge(request: Request, query: str = "", max_chunks: int = 4, min_score: float = 0.05):
    """Cerca nella knowledge base e restituisce risultati e contesto per LLM."""
    if not query or not query.strip():
        return {"results": [], "context": "", "count": 0}
    results = search_knowledge_base(query.strip(), max_chunks=max_chunks, min_score=min_score)
    context = format_context_for_llm(results)
    return {
        "results": results,
        "context": context,
        "count": len(results),
        "query": query,
        "topics_matched": sorted({r["topic"] for r in results}),
    }


@hub_knowledge_router.get("/knowledge/stats")
async def hub_knowledge_stats(current_user: dict = Depends(get_current_user)):
    """Restituisce le statistiche della knowledge base per l'utente autenticato."""
    stats = get_kb_stats()
    return {
        "topics": stats.get("topics", []),
        "chunks_per_topic": stats.get("chunks_per_topic", {}),
        "total_chunks": stats.get("total_chunks", 0),
        "total_words": stats.get("total_words", 0),
    }


@hub_knowledge_router.post("/knowledge/reload")
async def hub_reload_knowledge(current_user: dict = Depends(get_admin_user)):
    """Ricarica la knowledge base dal disco (solo admin)."""
    return reload_kb()


@hub_knowledge_router.post("/knowledge/init-embeddings")
async def hub_init_kb_embeddings(current_user: dict = Depends(get_admin_user)):
    """Inizializza gli embeddings della KB su pgvector e su ChromaDB (solo admin)."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        pg_result = init_kb_embeddings(session)
    chroma_result = init_chroma_db()
    return {"pgvector": pg_result, "chromadb": chroma_result}


# ---------------------------------------------------------------------------
# Public router aggregator (used by hub/main.py)
# ---------------------------------------------------------------------------

hub_router = APIRouter()
hub_router.include_router(hub_auth_router, prefix="/api/v1", tags=["auth"])
hub_router.include_router(hub_admin_router, prefix="/api/v1/admin", tags=["admin"])
hub_router.include_router(hub_knowledge_router, prefix="/api/v1", tags=["knowledge"])
