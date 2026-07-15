"""API routes."""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import json
import os
import secrets
import tempfile
import time
from collections.abc import AsyncGenerator
from dataclasses import fields
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
import requests
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy import insert
from starlette.background import BackgroundTask

from ..analytics.analytics import calculate_summary
from ..analytics.badges import calculate_badges, get_heatmap_points
from ..analytics.calories import calories_per_km, estimate_calories
from ..analytics.fatigue import (
    calculate_fatigue_score,
)
from ..analytics.granfondo_planner import generate_granfondo_plan
from ..audit_log import log_action, read_audit_logs
from ..maps.map_renderer import create_route_map
from ..maps.osm_maps import get_local_results, search_nearby, search_places
from ..models.models import AthleteProfile, GPSPoint, Ride
from ..rate_limiter import limiter
from ..redis_client import cache_delete as _cache_delete
from ..redis_client import cache_set as _cache_set
from ..redis_client import cached as _cached
from ..redis_client import check_rate_limit
from ..security import ALGORITHM, JWT_AUDIENCE, JWT_ISSUER, get_admin_user, get_current_user
from ..settings import get_settings
from ..utils.logger import get_logger
from .schemas import (
    AthleteCreate,
    AthleteUpdate,
    BenchmarkCompareRequest,
    CalendarEventCreate,
    CalendarEventUpdate,
    CoachChatRequest,
    GarminCallbackRequest,
    GoogleFitImportPayload,
    GoogleFitTokenRequest,
    GoogleHealthImportPayload,
    GranfondoPlanRequest,
    GranfondoSaveRequest,
    MetricCreate,
    POICreate,
    POIResponse,
    ProfileUpdate,
    RefreshTokenRequest,
    RideAnalysisRequest,
    RideCreate,
    RideUpdate,
    StravaCallbackRequest,
    WahooCallbackRequest,
)
from .utils import _trusted_forwarded_value

_s = get_settings()

_PLACE_CACHE: dict[str, tuple[Any, float]] = {}
_PLACE_CACHE_TTL_S = 600

logger = get_logger(__name__)


def _place_cache_get(key: str) -> Any | None:
    entry = _PLACE_CACHE.get(key)
    if entry is None:
        return None
    value, ts = entry
    if time.time() - ts > _PLACE_CACHE_TTL_S:
        del _PLACE_CACHE[key]
        return None
    return value


def _place_cache_set(key: str, value: Any) -> None:
    _PLACE_CACHE[key] = (value, time.time())


router = APIRouter()
admin_router = APIRouter()

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


def _build_redirect_uri(request: Request, path: str) -> str:
    proto = _trusted_forwarded_value(request, "x-forwarded-proto") or request.url.scheme
    host = (
        _trusted_forwarded_value(request, "x-forwarded-host") or request.headers.get("host") or request.url.netloc
    )
    return f"{proto}://{host}{path}"


def _build_frontend_redirect_url(
    request: Request,
    redirect_uri: str | None,
    fragment_keys: set[str] | None = None,
    **query_values: str,
) -> str:
    parsed = urlparse(redirect_uri or "")
    origin = (
        f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else _build_redirect_uri(request, "")
    )
    fragment_keys = fragment_keys or set()
    params = {key: value for key, value in query_values.items() if key not in fragment_keys and value is not None}
    fragment_params = {key: value for key, value in query_values.items() if key in fragment_keys and value is not None}
    base = origin.rstrip("/")
    query_suffix = f"?{urlencode(params)}" if params else ""
    fragment_suffix = f"#{urlencode(fragment_params)}" if fragment_params else ""
    return f"{base}/{query_suffix}{fragment_suffix}"


def _build_oauth_error_url(request: Request, redirect_uri: str, error: str) -> "RedirectResponse":  # noqa: F821,UP037
    """Redirect back to the SPA with an ``oauth_error`` query param.

    The error is delivered as a query param (not a fragment) so the SPA can read
    it even on a full document load. The ``redirect_uri`` comes from the signed
    OAuth state, so it is already host-validated.
    """
    from fastapi.responses import RedirectResponse

    return RedirectResponse(
        url=_build_frontend_redirect_url(request, redirect_uri, oauth_error=error)
    )


def _build_oauth_success_url(redirect_uri: str, token: str, email: str, user_id: Any) -> str:
    """Build the post-login redirect URL that hands the JWT to the SPA.

    - Mobile / custom app schemes (e.g. ``com.bikemaster.app://callback``):
      deliver the token as a query string on the deep-link target.
    - Web SPA: redirect to the SPA origin root with the token in the URL
      *fragment*. Fragments are never sent to the server, so the JWT never
      appears in backend access logs, proxies or Referer headers. The SPA
      consumes the fragment and immediately strips it via ``history.replaceState``.
    """
    parsed = urlparse(redirect_uri or "")
    if parsed.scheme and parsed.scheme not in ("http", "https"):
        target = f"{parsed.scheme}://{parsed.netloc or parsed.path.lstrip('/')}"
        return f"{target}?{urlencode({'token': token, 'email': email or '', 'user_id': str(user_id)})}"

    origin = f"{parsed.scheme}://{parsed.netloc}/" if parsed.scheme else "/"
    return f"{origin}#{urlencode({'token': token, 'email': email or '', 'user_id': str(user_id)})}"


def _validate_redirect_uri(redirect_uri: str, request: Request | None = None) -> None:
    parsed = urlparse(redirect_uri)
    if not parsed.scheme:
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")
    # Custom (non-http/https) URI schemes, e.g. mobile deep links like
    # "com.bikemaster.app://callback". Validate against the configured allow-list.
    if parsed.scheme not in ("http", "https"):
        allowed_schemes = (
            _s.oauth_redirect_schemes_list if hasattr(_s, "oauth_redirect_schemes_list") else set()
        )
        if parsed.scheme.lower() in allowed_schemes and parsed.netloc:
            return
        raise HTTPException(status_code=400, detail="Invalid redirect_uri scheme")
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")
    host_lower = parsed.hostname.lower()
    cors_hosts = set()
    try:
        cors_list = _s.cors_origins_list if hasattr(_s, "cors_origins_list") else []
        for origin in cors_list:
            with contextlib.suppress(ValueError):
                cors_hosts.add(urlparse(origin).hostname.lower())
    except Exception:
        logger.debug("Failed to parse CORS origins", exc_info=True)
    configured_hosts = set()
    if hasattr(_s, "oauth_allowed_hosts_list"):
        configured_hosts = set(_s.oauth_allowed_hosts_list)
    localhost_ports = {"localhost", "127.0.0.1", "0.0.0.0"}  # noqa: S104
    if host_lower in localhost_ports:
        return
    # NOTE: the request Origin header is intentionally NOT trusted here.
    # Allowing it would let an attacker craft redirect_uri=https://evil.com with
    # Origin: https://evil.com and achieve an open redirect.
    allowed_hosts = (
        {"bikemaster.onrender.com", "bikemaster-api.onrender.com", "bikemaster-xi.vercel.app", "testserver"}
        | cors_hosts
        | configured_hosts
    )
    if host_lower not in allowed_hosts:
        # Allow any Vercel preview/production deployment. This keeps the OAuth
        # redirect_uri validation consistent with the CORS allow_origin_regex
        # (r"https://.*\.vercel\.app") instead of hardcoding a single subdomain,
        # so newly generated Vercel deploy URLs keep working for login.
        if host_lower.endswith(".vercel.app"):
            return
        raise HTTPException(status_code=400, detail="Invalid redirect_uri host")


OAUTH_STATE_TTL_MIN = 10


def _issue_oauth_state(redirect_uri: str, pkce_id: str | None = None) -> str:
    """Issue a signed, server-only OAuth state (random nonce + redirect_uri + pkce_id).

    Replaces the previous client-generated ``base64({redirect_uri})`` state which was
    predictable and provided no CSRF protection.
    """
    payload = {
        "nonce": secrets.token_urlsafe(32),
        "redirect_uri": redirect_uri,
        "pkce_id": pkce_id,
        "exp": datetime.now(UTC) + timedelta(minutes=OAUTH_STATE_TTL_MIN),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "type": "oauth_state",
    }
    return jwt.encode(payload, _s.secret_key, algorithm=ALGORITHM)


def _verify_oauth_state(state: str) -> dict | None:
    """Verify a signed OAuth state. Returns {redirect_uri, pkce_id} or None if invalid/expired."""
    if not state:
        return None
    try:
        payload = jwt.decode(
            state, _s.secret_key, algorithms=[ALGORITHM], issuer=JWT_ISSUER, audience=JWT_AUDIENCE
        )
    except JWTError:
        return None
    if payload.get("type") != "oauth_state":
        return None
    redirect_uri = payload.get("redirect_uri")
    if not isinstance(redirect_uri, str):
        return None
    return {"redirect_uri": redirect_uri, "pkce_id": payload.get("pkce_id")}


def _http_error_detail(exc: Exception, fallback: str) -> str:
    response = getattr(exc, "response", None)
    body = response.text if response is not None else str(exc)
    return f"{fallback}: {body[:500]}"


def _user_id(current_user: dict) -> int:
    return int(current_user["id"])


def _public_athlete(athlete: dict | None) -> dict:
    if athlete is None:
        return {}
    return {k: v for k, v in athlete.items() if k != "password_hash"}


def _athlete_profile_data(athlete: dict | None) -> dict | None:
    if athlete is None:
        return None
    allowed_fields = {field.name for field in fields(AthleteProfile)}
    return {k: v for k, v in athlete.items() if k in allowed_fields}


def _ensure_int_user_id(current_user: dict) -> int:
    try:
        return int(current_user["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Token utente non valido") from exc


def _ensure_athlete_access(athlete_id: int, current_user: dict) -> None:
    if current_user.get("is_admin"):
        return
    if int(athlete_id) != _ensure_int_user_id(current_user):
        raise HTTPException(status_code=403, detail="Access denied to this athlete")


def _ensure_ride_access(ride: dict, current_user: dict) -> None:
    if not current_user.get("is_admin"):
        user_id = _user_id(current_user)
        user_tenant_id = current_user.get("tenant_id", user_id)
        ride_athlete_id = ride.get("athlete_id")
        ride_tenant_id = ride.get("tenant_id")
        if ride_athlete_id != user_id and ride_tenant_id != user_tenant_id:
            raise HTTPException(status_code=403, detail="Access denied to this ride")


def _get_athlete_rides(athlete_id: int, current_user: dict) -> list[Ride]:
    """Fetch rides for athlete with access control."""
    from ..db.database import get_rides_by_athlete

    _ensure_athlete_access(athlete_id, current_user)
    return [Ride(**r) for r in get_rides_by_athlete(athlete_id)]


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


def _make_streaming_response(generator: AsyncGenerator[str, None], event_type: str = "chunk") -> StreamingResponse:
    async def stream_gen() -> AsyncGenerator[str, None]:
        try:
            async for chunk in generator:
                yield _sse(event_type, chunk.replace("\n", " "))
        except Exception:
            yield _sse("error", "Internal server error")
            yield _sse("done", "")

    return StreamingResponse(
        stream_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _google_fit_message_html(message: dict) -> HTMLResponse:
    payload = json.dumps(message)
    return HTMLResponse(
        f"<script>window.opener.postMessage({payload}, window.location.origin); window.close();</script>"
    )


def _google_health_message_html(message: dict) -> HTMLResponse:
    payload = json.dumps(message)
    return HTMLResponse(
        f"<script>window.opener.postMessage({payload}, window.location.origin); window.close();</script>"
    )


def _strava_message_html(message: dict) -> HTMLResponse:
    payload = json.dumps(message)
    return HTMLResponse(
        f"<script>window.opener.postMessage({payload}, window.location.origin); window.close();</script>"
    )


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "bikemaster"}


@router.post("/alerts/webhook")
async def alerts_webhook(request: Request):
    """Receive alerts from Prometheus Alertmanager."""
    expected_token = os.getenv("ALERTMANAGER_WEBHOOK_TOKEN")
    if expected_token:
        provided = request.headers.get("X-Alertmanager-Webhook-Token", "")
        if not provided or not hmac.compare_digest(provided, expected_token):
            raise HTTPException(status_code=401, detail="Invalid webhook token")
    elif _s.environment.lower() in ("production", "prod", "staging"):
        logger.warning("ALERTMANAGER_WEBHOOK_TOKEN not set: /alerts/webhook is unauthenticated")
    body = await request.json()
    logger.info("Alert received: %s", body.get("receiver", "unknown"))
    return {"status": "ok"}


@router.get("/sentry-debug")
async def sentry_debug():
    """Debug endpoint to verify Sentry error tracking.

    Only available outside production to avoid exposing a crash endpoint.
    """
    if _s.environment.lower() in ("production", "prod"):
        raise HTTPException(status_code=404, detail="Not found")
    raise ZeroDivisionError("Sentry sentinel")


@router.get("/health/redis")
async def health_redis():
    from ..redis_client import get_redis

    r = await get_redis()
    if r is None:
        return {"redis": "unavailable", "cache": "disabled"}
    try:
        info = await r.ping()
        return {"redis": "connected", "status": "ok", "ping": "pong" if info is True else "ok"}
    except Exception as e:
        return {"redis": "error", "error": str(e)}


@router.get("/config/google-maps-key")
async def google_maps_key(request: Request, current_user: dict = Depends(get_current_user)):
    # The Maps JS key is inherently client-side, so it MUST be restricted via
    # HTTP-referrer in Google Cloud. As defense in depth, only serve it to
    # requests originating from the app's own configured origins.
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    allowed = {urlparse(o).netloc for o in _s.cors_origins_list}
    if origin and urlparse(origin).netloc not in allowed:
            raise HTTPException(status_code=403, detail="Origin not allowed")
    return {"google_maps_api_key": _s.google_maps_api_key or ""}


@router.get("/maps/pois/nearby")
async def get_nearby_pois(
    lat: float = Query(..., ge=-90, le=90, description="Latitude of the search center"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude of the search center"),
    radius: float = Query(5.0, ge=0.1, le=200, description="Search radius in km"),
):
    """Return Points of Interest within ``radius`` km of (lat, lon)."""
    from ..analytics.repositories.poi_repository import POIRepository
    from ..db.async_db import get_session_factory

    try:
        repo = POIRepository(session_factory=get_session_factory())
    except RuntimeError:
        repo = POIRepository()
    pois = await repo.get_nearby(lat, lon, radius)
    return {"pois": pois}


@router.get("/maps/pois")
async def list_pois_endpoint(itinerary_id: int | None = None):
    """List all POIs, optionally filtered by itinerary_id."""
    from ..db.database import list_pois

    return {"pois": list_pois(itinerary_id)}


@router.post("/maps/pois", response_model=POIResponse)
async def create_poi(poi: POICreate, current_user: dict = Depends(get_current_user)):
    """Create a Point of Interest owned by the current user."""
    from ..db.database import get_poi, save_poi

    data = poi.model_dump()
    data["created_by"] = current_user["id"]
    data["tenant_id"] = current_user.get("tenant_id", current_user["id"])
    poi_id = save_poi(data)
    created = get_poi(poi_id)
    if created is None:
        raise HTTPException(status_code=500, detail="Failed to create POI")
    return created


@router.get("/maps/pois/{poi_id}", response_model=POIResponse)
async def get_poi_endpoint(poi_id: int):
    from ..db.database import get_poi

    poi = get_poi(poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    return poi


@router.delete("/maps/pois/{poi_id}")
async def delete_poi_endpoint(
    poi_id: int, current_user: dict = Depends(get_current_user)
):
    from ..db.database import delete_poi, get_poi

    poi = get_poi(poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    if poi["created_by"] != current_user["id"] and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not allowed to delete this POI")
    delete_poi(poi_id)
    return {"deleted": True}


@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    from ..security import (
        create_access_token,
        create_refresh_token,
        save_refresh_token,
        verify_password,
    )

    if _s.database_url:
        from sqlalchemy import select

        from ..db.async_db import get_session_factory
        from ..db.models import UserModel

        session_factory = get_session_factory()
        async with session_factory() as session:
            stmt = select(UserModel).where(UserModel.username == form_data.username)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            user_id = user.id if user else None
            if not await check_rate_limit(user_id, "/auth/login", limit=5, window=60):
                raise HTTPException(
                    status_code=429, detail="Too many login attempts"
                )

            if not user or not verify_password(form_data.password, user.password_hash or ""):
                raise HTTPException(
                    status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"}
                )

            access_token = create_access_token(subject=str(user.id), is_admin=user.is_admin, tenant_id=user.id)
            refresh_token = create_refresh_token(user.id, is_admin=user.is_admin, tenant_id=user.id)
            await save_refresh_token(user.id, refresh_token)
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "username": user.username,
                "id": user.id,
                "is_admin": user.is_admin,
            }

    from ..db.database import get_db_connection

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, password_hash, experience_level FROM athletes WHERE name = ?",
            (form_data.username,),
        )
        row = cur.fetchone()
    if not row or not verify_password(form_data.password, row[2] or ""):
        raise HTTPException(status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    athlete_id = int(row[0])
    access_token = create_access_token(subject=str(athlete_id), is_admin=False, tenant_id=athlete_id)
    refresh_token = create_refresh_token(athlete_id, is_admin=False, tenant_id=athlete_id)
    await save_refresh_token(athlete_id, refresh_token)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "username": row[1],
        "id": athlete_id,
        "is_admin": False,
    }


@router.post("/auth/logout")
async def logout(request: Request, current_user: dict = Depends(get_current_user)):
    from ..security import revoke_refresh_token, revoke_token

    auth_header = request.headers.get("authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        import base64
        import json

        parts = token.split(".")
        if len(parts) >= 2:
            padding = 4 - len(parts[1]) % 4
            payload = parts[1] + ("=" * padding)
            decoded = base64.b64decode(payload)
            payload_data = json.loads(decoded)
            jti = payload_data.get("jti")
            if jti:
                revoked = await revoke_token(jti)
                if not revoked:
                    logger.warning("Logout: access token revocation failed for jti=%s", jti)
            athlete_id = payload_data.get("sub")
            if athlete_id:
                refresh_revoked = await revoke_refresh_token(int(athlete_id))
                if not refresh_revoked:
                    logger.warning("Logout: refresh token revocation failed for athlete_id=%s", athlete_id)
    except Exception as exc:
        logger.warning("Logout: failed to revoke token: %s", exc)
    return {"msg": "Logged out successfully"}


@router.post("/auth/refresh")
@limiter.limit("10/minute")
async def refresh_token(request: Request, payload: RefreshTokenRequest):
    from ..security import create_access_token, decode_token_with_fallback, is_token_revoked

    refresh_token = payload.refresh_token
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
    tenant_id = jwt_payload.get("tenant_id")
    resolved_tenant = int(tenant_id) if tenant_id is not None else int(user_id)
    return {
        "access_token": create_access_token(
            subject=str(user_id), is_admin=is_admin, tenant_id=resolved_tenant
        ),
        "token_type": "bearer",
    }


@router.post("/auth/register")
@limiter.limit("3/minute")
async def register(
    request: Request,
    username: str = Body(..., min_length=3, max_length=64),
    password: str = Body(..., min_length=8, max_length=128),
    email: str = Body(None),
):
    from ..db.database import get_athlete_by_email, get_athlete_by_name, save_athlete
    from ..security import hash_password

    if not await check_rate_limit(None, "/auth/register", limit=3, window=60):
        raise HTTPException(
            status_code=429, detail="Too many registration attempts"
        )

    if len(username) < 3 or len(username) > 64 or len(password) < 8 or len(password) > 128:
        raise HTTPException(
            status_code=400,
            detail="Username must be 3-64 chars, password 8-128 chars",
        )

    if _s.database_url:
        from sqlalchemy import select

        from ..db.async_db import get_session_factory
        from ..db.models import AthleteModel, UserModel

        session_factory = get_session_factory()
        async with session_factory() as session:
            if email:
                stmt = select(UserModel).where((UserModel.username == username) | (UserModel.email == email))
            else:
                stmt = select(UserModel).where(UserModel.username == username)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                detail = "Email already registered" if email and existing.email == email else "Username already exists"
                raise HTTPException(status_code=400, detail=detail)

            password_hash = hash_password(password)
            stmt = (
                insert(UserModel)
                .values(
                    username=username,
                    email=email,
                    password_hash=password_hash,
                    is_admin=False,
                    is_active=True,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
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

    if email:
        existing_email = get_athlete_by_email(email)
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
    existing = get_athlete_by_name(username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    password_hash = hash_password(password)
    athlete_id = save_athlete(
        {
            "name": username,
            "email": email,
            "experience_level": "Beginner",
            "password_hash": password_hash,
        }
    )
    if athlete_id:
        from ..db.database import update_athlete

        update_athlete(athlete_id, {"tenant_id": athlete_id})
    return {
        "username": username,
        "email": email,
        "msg": "Utente creato",
        "is_admin": False,
        "id": athlete_id,
        "profile_complete": False,
    }


@router.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    from ..db.database import get_athlete as _get_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete = _get_athlete(current_user["id"], tenant_id)
    if not athlete:
        return {
            "id": current_user["id"],
            "username": "",
            "email": None,
            "picture": None,
            "is_admin": current_user.get("is_admin", False),
            "tenant_id": current_user.get("tenant_id", current_user["id"]),
            "profile_complete": False,
        }
    profile_complete = (
        athlete.get("age") is not None
        and athlete.get("weight_kg") is not None
        and (athlete.get("experience_level") or "").strip() != ""
    )
    return {
        "id": athlete["id"],
        "username": athlete.get("name", ""),
        "email": athlete.get("email"),
        "picture": athlete.get("picture"),
        "is_admin": current_user.get("is_admin", False),
        "tenant_id": current_user.get("tenant_id", current_user["id"]),
        "profile_complete": profile_complete,
    }


@router.put("/auth/profile")
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
):
    from ..db.database import get_athlete as _get_athlete
    from ..db.database import update_athlete as _update_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
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
    update_data = {k: v for k, v in profile_data.model_dump().items() if k in allowed_fields and v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    _update_athlete(current_user["id"], update_data)
    athlete = _get_athlete(current_user["id"], tenant_id)
    return _public_athlete(athlete)


@router.post("/auth/change-password")
async def change_password(
    current_password: str = Body(..., min_length=6, embed=True),
    new_password: str = Body(..., min_length=8, max_length=100, embed=True),
    current_user: dict = Depends(get_current_user),
):
    from ..db.database import get_athlete as _get_athlete
    from ..security import hash_password, verify_password

    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete = _get_athlete(current_user["id"], tenant_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="User not found")
    stored_hash = athlete.get("password_hash", "")
    if not verify_password(current_password, stored_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    new_hash = hash_password(new_password)
    from ..db.database import update_athlete

    update_athlete(current_user["id"], {"password_hash": new_hash})
    return {"msg": "Password changed successfully"}


@router.get("/auth/google")
@limiter.limit("10/minute")
async def google_oauth_login(
    request: Request,
    redirect_uri: str | None = Query(None),
    state: str = "",
):
    """Get Google OAuth2 authorization URL."""
    from ..auth.google_auth import get_google_oauth_url

    if not _s.google_client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")
    redirect_uri = redirect_uri or _build_redirect_uri(request, "/api/v1/auth/google/callback")
    _validate_redirect_uri(redirect_uri, request)
    state = _issue_oauth_state(redirect_uri)
    auth_url = get_google_oauth_url(_s.google_client_id, redirect_uri=redirect_uri, state=state)
    return {"auth_url": auth_url}


@router.get("/auth/google/callback")
@limiter.limit("10/minute")
async def google_oauth_callback_get(
    request: Request,
    code: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
    redirect_uri: str | None = Query(None),
    state: str = Query(""),
):
    """Handle Google OAuth2 callback - exchange code for token and create/login user."""
    from fastapi.responses import RedirectResponse

    from ..auth.google_auth import create_google_session, exchange_google_code, get_google_user_info
    from ..db.database import get_athlete, get_athlete_by_email, save_athlete

    if not _s.google_client_id or not _s.google_client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    state_data = _verify_oauth_state(state)
    if not state_data:
        return _build_oauth_error_url(
            request, _build_redirect_uri(request, "/api/v1/auth/google/callback"), "invalid_state"
        )
    redirect_uri = state_data["redirect_uri"]
    _validate_redirect_uri(redirect_uri, request)

    if error:
        message = error_description or error
        return _build_oauth_error_url(request, redirect_uri, message)

    if not code:
        return _build_oauth_error_url(request, redirect_uri, "missing_code")

    cache_key = f"oauth:code:{code}"
    try:
        cached_result = await _cached(cache_key)
        if cached_result:
            return RedirectResponse(url=cached_result["redirect_url"])

        try:
            token_data = await asyncio.to_thread(
                exchange_google_code, _s.google_client_id, _s.google_client_secret, code, redirect_uri
            )
        except Exception as exc:
            response = getattr(exc, "response", None)
            if response is not None and getattr(response, "status_code", None) == 400:
                return _build_oauth_error_url(request, redirect_uri, "oauth_error")
            error_body = response.text if response is not None else str(exc)
            error_detail = f"token_exchange_failed:{error_body[:200]}"
            return _build_oauth_error_url(request, redirect_uri, error_detail)
        access_token = token_data.get("access_token")
        if not access_token:
            return _build_oauth_error_url(request, redirect_uri, "no_access_token")

        try:
            user_info = await asyncio.to_thread(get_google_user_info, access_token)
        except Exception as exc:
            response = getattr(exc, "response", None)
            error_body = response.text if response is not None else str(exc)
            return _build_oauth_error_url(request, redirect_uri, f"userinfo_failed:{error_body[:200]}")
        google_sub = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name")

        if not google_sub:
            return _build_oauth_error_url(request, redirect_uri, "invalid_user_info")

        existing = await asyncio.to_thread(get_athlete_by_email, email) if email else None
        if not existing:
            from ..redis_client import get_redis

            lock_key = f"oauth:lock:athlete:{email or google_sub}"
            r = await get_redis()
            if r is not None:
                lock_acquired = await r.set(lock_key, "1", ex=10, nx=True)
            else:
                lock_acquired = True
            try:
                if lock_acquired:

                    def _create_athlete():
                        result = get_athlete_by_email(email) if email else None
                        if not result:
                            athlete_id = save_athlete(
                                {
                                    "name": name or email or google_sub,
                                    "email": email,
                                    "picture": user_info.get("picture"),
                                    "experience_level": "Beginner",
                                }
                            )
                            if athlete_id:
                                from ..db.database import update_athlete
                                update_athlete(athlete_id, {"tenant_id": athlete_id})
                            result = get_athlete(athlete_id)
                        return result

                    existing = await asyncio.to_thread(_create_athlete)
            finally:
                if r is not None:
                    await r.delete(lock_key)

        if not existing:
            return _build_oauth_error_url(request, redirect_uri, "user_creation_failed")

        jwt_token = create_google_session(user_info, athlete_id=existing["id"])["access_token"]
        redirect_url = _build_oauth_success_url(redirect_uri, jwt_token, email or "", existing["id"])
        await _cache_set(f"oauth:code:{code}", {"redirect_url": redirect_url}, ttl=300)
        return RedirectResponse(url=redirect_url)
    except Exception as exc:
        logger.exception("Google OAuth callback failed: %s", exc)
        return _build_oauth_error_url(request, redirect_uri, "server_error")


@router.post("/auth/google/code-exchange")
@limiter.limit("10/minute")
async def google_code_exchange(
    request: Request,
    payload: dict[str, str] = Body(...),
):
    code = payload.get("code")
    redirect_uri = payload.get("redirect_uri")
    if not code or not redirect_uri:
        raise HTTPException(status_code=400, detail="code and redirect_uri required")
    from ..auth.google_auth import create_google_session, exchange_google_code, get_google_user_info

    if not _s.google_client_id or not _s.google_client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    _validate_redirect_uri(redirect_uri, request)
    try:
        token_data = await asyncio.to_thread(
            exchange_google_code, _s.google_client_id, _s.google_client_secret, code, redirect_uri
        )
    except requests.exceptions.HTTPError as exc:
        response = getattr(exc, "response", None)
        error_body = response.text if response is not None else str(exc)
        raise HTTPException(status_code=400, detail=f"token_exchange_failed:{error_body[:200]}") from None
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="no_access_token")
    try:
        user_info = await asyncio.to_thread(get_google_user_info, access_token)
    except requests.exceptions.HTTPError as exc:
        response = getattr(exc, "response", None)
        error_body = response.text if response is not None else str(exc)
        raise HTTPException(status_code=400, detail=f"userinfo_failed:{error_body[:200]}") from None
    google_sub = user_info.get("sub")
    email = user_info.get("email")
    if not google_sub:
        raise HTTPException(status_code=400, detail="invalid_user_info")
    from ..db.database import get_athlete, get_athlete_by_email, save_athlete
    existing = await asyncio.to_thread(get_athlete_by_email, email) if email else None
    if not existing:
        athlete_id = await asyncio.to_thread(
            save_athlete,
            {
                "name": user_info.get("name") or email or google_sub,
                "email": email,
                "picture": user_info.get("picture"),
                "experience_level": "Beginner",
            },
        )
        if athlete_id:
            from ..db.database import update_athlete
            update_athlete(athlete_id, {"tenant_id": athlete_id})
        existing = get_athlete(athlete_id)
    if not existing:
        raise HTTPException(status_code=500, detail="user_creation_failed")
    jwt_token = create_google_session(user_info, athlete_id=existing["id"])["access_token"]
    return {"access_token": jwt_token, "email": email or "", "user_id": str(existing["id"])}


@router.post("/rides")
async def create_ride(ride_data: RideCreate, current_user: dict = Depends(get_current_user)):
    """Create ride - automatically assigned to current user."""
    from ..db.database import save_ride

    ride_dict = ride_data.model_dump()
    ride_dict["athlete_id"] = current_user["id"]
    ride_dict["tenant_id"] = current_user["id"]
    points = ride_dict.get("gps_points", [])
    if points:
        ride_dict["gps_points"] = points
    if (
        not ride_dict.get("avg_speed_kmh")
        and ride_dict.get("distance_km")
        and ride_dict.get("duration_minutes")
        and ride_dict["duration_minutes"] > 0
    ):
        ride_dict["avg_speed_kmh"] = ride_dict["distance_km"] / (ride_dict["duration_minutes"] / 60)
    if not ride_dict.get("calories"):
        ride = Ride(**{k: v for k, v in ride_dict.items() if k not in ("gps_points", "tenant_id")})
        method = "physics" if ride_dict.get("avg_speed_kmh") else "met"
        ride_dict["calories"] = estimate_calories(ride, method=method)
    ride_id = save_ride(ride_dict)
    from ..events import RideCreated, publish

    await publish(
        RideCreated.type,
        {
            "ride_id": int(ride_id),
            "athlete_id": current_user["id"],
            "distance_km": ride_dict.get("distance_km"),
            "duration_minutes": ride_dict.get("duration_minutes"),
        },
    )
    await _cache_delete(f"dashboard:{current_user['id']}")
    return {"id": int(ride_id), **ride_dict}


@router.get("/rides")
async def list_rides(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("date", pattern="^(date|distance|duration)$"),
    current_user: dict = Depends(get_current_user),
):
    """List rides - only for current user."""
    from ..analytics.calories import ensure_calories
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    all_rides = get_rides_by_athlete(current_user["id"], tenant_id)
    start = (page - 1) * page_size
    rides = all_rides[start : start + page_size]
    for ride in rides:
        if not ride.get("calories"):
            try:
                ride["calories"] = ensure_calories(Ride(**{k: v for k, v in ride.items() if k in Ride.__dataclass_fields__}))
            except Exception:
                logger.debug("Calorie estimate failed for ride list", exc_info=True)
    return {
        "rides": rides,
        "total": len(all_rides),
        "page": page,
        "page_size": page_size,
    }


@router.get("/rides/count")
async def count_rides(current_user: dict = Depends(get_current_user)):
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    return {"count": len(get_rides_by_athlete(current_user["id"], tenant_id))}


@router.get("/rides/{ride_id}")
async def get_ride(ride_id: int, current_user: dict = Depends(get_current_user)):
    """Get ride - user can only see owned rides."""
    from ..db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    r = Ride(**ride)
    ride["fatigue_score"] = round(calculate_fatigue_score(r), 1)
    ride["calories_per_km"] = round(calories_per_km(r), 0) if r.distance_km else 0
    return ride


@router.get("/rides/{ride_id}/map")
async def generate_ride_map(
    ride_id: int,
    provider: str = Query("folium", description="Map provider: folium or aethermap"),
    current_user: dict = Depends(get_current_user),
):
    from pathlib import Path

    from ..db.database import get_ride as _get_ride
    from ..models.models import GPSPoint

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points for this ride")
    normalized = []
    for p in gps_points:
        if "altitude" not in p and "elevation" in p:
            normalized.append({**p, "altitude": p.get("elevation")})
        else:
            normalized.append(p)
    points = [GPSPoint(**p) for p in normalized]
    base_dir = Path(__file__).resolve().parent.parent / "static"
    safe_id = "".join(c if c.isalnum() or c == "_" else "_" for c in str(ride_id))

    if provider == "aethermap":
        try:
            from ..maps.aethermap_adapter import create_route_map as aether_create_route_map
        except ImportError as exc:
            raise HTTPException(status_code=500, detail="AetherMap provider not available") from exc
        from ..models.models import RouteStatistics

        stats = None
        if ride.get("distance_km") and ride.get("duration_minutes"):
            stats = RouteStatistics(
                total_distance_m=ride.get("distance_km", 0.0) * 1000.0,
                total_duration_s=ride.get("duration_minutes", 0.0) * 60.0,
                avg_speed_km_h=ride.get("avg_speed_kmh", 0.0),
                max_speed_km_h=ride.get("max_speed_kmh", 0.0),
                total_elevation_gain_m=ride.get("elevation_gain_m", 0.0),
            )
        path = base_dir / f"ride_{safe_id}_map.json"
        resolved = path.resolve()
        if not resolved.is_relative_to(base_dir.resolve()):
            raise HTTPException(status_code=400, detail="Invalid path")
        try:
            aether_create_route_map(points, statistics=stats, output_path=str(resolved))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Map generation failed: {exc}") from exc
        return {"map_url": f"/static/{resolved.name}", "engine": "aethermap"}

    from ..maps.map_renderer import create_route_map

    path = base_dir / f"ride_{safe_id}_map.html"
    resolved = path.resolve()
    if not resolved.is_relative_to(base_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid path")
    try:
        create_route_map(points, output_path=str(resolved))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Map generation failed: {exc}") from exc
    return {"map_url": f"/static/{resolved.name}"}


@router.post("/rides/analyze")
async def analyze_rides(request: Request, payload: RideAnalysisRequest, current_user: dict = Depends(get_current_user)):
    from ..analytics.analytics import calculate_summary
    from ..models.models import Ride

    return calculate_summary([Ride(**r.model_dump()) for r in payload.rides])


@router.post("/rides/{ride_id}/analyze")
async def analyze_single_ride(ride_id: int, ride_data: RideCreate, current_user: dict = Depends(get_current_user)):
    from ..analytics.analytics import analyze_ride
    from ..models.models import Ride

    return analyze_ride(Ride(id=ride_id, **ride_data.model_dump()))


@router.delete("/rides/{ride_id}")
async def delete_ride(ride_id: int, current_user: dict = Depends(get_current_user)):
    """Delete ride - user can only delete owned rides."""
    from ..db.database import delete_ride as _delete
    from ..db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if ride:
        _ensure_ride_access(ride, current_user)
    if not _delete(ride_id):
        raise HTTPException(status_code=404, detail="Ride not found")
    await _cache_delete(f"dashboard:{current_user['id']}")
    return {"deleted": True}


@router.get("/rides/{ride_id}/segments")
async def get_ride_segments(
    ride_id: int, min_distance_m: int = Query(1000), current_user: dict = Depends(get_current_user)
):
    """Detect and return significant segments from ride GPS points."""
    from ..db.database import get_ride as _get_ride
    from ..models.models import GPSPoint

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)

    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points for this ride")
    normalized = []
    for p in gps_points:
        if "altitude" not in p and "elevation" in p:
            normalized.append({**p, "altitude": p.get("elevation")})
        else:
            normalized.append(p)
    points = [GPSPoint(**p) for p in normalized]
    base_dir = Path(__file__).resolve().parent.parent / "static"
    safe_id = "".join(c if c.isalnum() or c == "_" else "_" for c in str(ride_id))
    path = base_dir / f"ride_{safe_id}_map.html"
    resolved = path.resolve()
    if not resolved.is_relative_to(base_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid path")
    create_route_map(points, output_path=str(resolved))
    return {"map_url": f"/static/{resolved.name}"}


def _validate_gpx_fit_import(ride_data: dict, user_id: int) -> None:
    """Validate a parsed ride before persisting it.

    Each GPS point is run through ``ValidatedGPSPoint`` (invalid points are dropped);
    the assembled ride is validated with ``ValidatedRide``. Raises HTTPException (400)
    on failure so malformed uploads are rejected instead of being stored.
    """
    from ..core.validation import ValidatedGPSPoint, ValidatedRide

    gps = ride_data.get("gps_points") or []
    valid_points: list[dict] = []
    for p in gps:
        try:
            valid_points.append(ValidatedGPSPoint(**p).model_dump(mode="json"))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Dropping invalid GPS point during import: %s (%s)", p, exc)
    if len(valid_points) < 2:
        raise HTTPException(
            status_code=400, detail="Serve almeno 2 punti GPS validi per importare la corsa."
        )
    try:
        ValidatedRide(
            athlete_id=user_id,
            date=ride_data["date"],
            distance_km=ride_data["distance_km"],
            duration_minutes=ride_data["duration_minutes"],
            avg_speed_kmh=ride_data.get("avg_speed_kmh"),
            elevation_gain_m=ride_data.get("elevation_gain_m"),
            calories=ride_data.get("calories"),
            gps_points=valid_points,
            title=ride_data.get("title"),
            external_source=ride_data.get("external_source"),
            external_id=ride_data.get("external_id"),
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Dati corsa non validi: {exc}") from exc
    ride_data["gps_points"] = valid_points


@router.post("/import/gpx")
async def import_gpx(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    from ..db.database import save_ride
    from ..ingestion.gps_parser import parse_gpx_file, points_to_ride

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")
    user_id = _user_id(current_user)
    tenant_id = current_user["id"]
    filename = file.filename

    def _work() -> dict:
        t0 = time.perf_counter()
        points_data = parse_gpx_file(content.decode())
        t1 = time.perf_counter()
        ride_data = points_to_ride(points_data, name=filename, max_points=5000)
        t2 = time.perf_counter()
        if "error" not in ride_data:
            _validate_gpx_fit_import(ride_data, user_id)
            ride_data["athlete_id"] = user_id
            ride_data["tenant_id"] = tenant_id
            ride_id = save_ride({k: v for k, v in ride_data.items() if k != "id"})
            ride_data["id"] = int(ride_id)
        t3 = time.perf_counter()
        logger.info(
            "gpx_import_timing parse_ms=%.1f process_ms=%.1f db_ms=%.1f points=%d",
            (t1 - t0) * 1000,
            (t2 - t1) * 1000,
            (t3 - t2) * 1000,
            len(points_data),
        )
        return ride_data

    ride_data = await asyncio.to_thread(_work)
    if "error" not in ride_data:
        from ..monitoring import record_gps_import

        record_gps_import("gpx", "upload")
    return ride_data


@router.post("/import/fit")
async def import_fit(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    import tempfile

    from ..db.database import save_ride
    from ..ingestion.gps_parser import parse_fit_file, points_to_ride

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")
    user_id = _user_id(current_user)
    tenant_id = current_user["id"]
    filename = file.filename

    def _work() -> dict:
        with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as tmp:
            tmp.write(content)
            temp_path = tmp.name
        try:
            try:
                points_data = parse_fit_file(temp_path)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Invalid FIT file: {exc}") from exc
        finally:
            import os

            os.unlink(temp_path)
        ride_data = points_to_ride(points_data, name=filename, max_points=5000)
        if "error" not in ride_data:
            _validate_gpx_fit_import(ride_data, user_id)
            ride_data["athlete_id"] = user_id
            ride_data["tenant_id"] = tenant_id
            ride_id = save_ride({k: v for k, v in ride_data.items() if k != "id"})
            ride_data["id"] = int(ride_id)
        return ride_data

    ride_data = await asyncio.to_thread(_work)
    if "error" not in ride_data:
        from ..monitoring import record_gps_import

        record_gps_import("fit", "upload")
    return ride_data


@router.get("/health/detailed")
async def health_detailed(request: Request):
    from ..db.database import get_all_athletes, get_all_rides

    rides = get_all_rides()
    athletes = get_all_athletes()
    db_size = Path(_s.db_path).stat().st_size if Path(_s.db_path).exists() else 0
    return {
        "service": "bikemaster",
        "status": "ok",
        "version": "0.1.0",
        "rides_count": len(rides),
        "athletes_count": len(athletes),
        "database_size_bytes": db_size,
    }


@router.get("/coach/history")
async def coach_chat_history(athlete_id: int = Query(...), current_user: dict = Depends(get_current_user)):
    from ..db.database import get_chat_history

    _ensure_athlete_access(athlete_id, current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    history = get_chat_history(athlete_id, tenant_id=tenant_id)
    return {"athlete_id": athlete_id, "history": history}


@router.post("/import/multiple")
async def import_multiple(files: list[UploadFile] = File(...), current_user: dict = Depends(get_current_user)):
    import tempfile

    from ..db.database import save_ride
    from ..ingestion.gps_parser import parse_fit_file, parse_gpx_file, points_to_ride

    user_id = _user_id(current_user)
    tenant_id = current_user["id"]

    contents = []
    total_size = 0
    for file in files:
        content = await file.read()
        total_size += len(content)
        if total_size > MAX_UPLOAD_SIZE * 2:
            raise HTTPException(status_code=413, detail="Total upload size exceeds 100MB limit.")
        contents.append((file.filename, content))

    def _process(filename: str | None, raw: bytes) -> dict:
        ext = filename.lower().split(".")[-1] if filename else ""
        if ext == "gpx":
            points = parse_gpx_file(raw.decode())
        elif ext in ("fit", "fitf"):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as tmp:
                tmp.write(raw)
                temp_path = tmp.name
            try:
                points = parse_fit_file(temp_path)
            finally:
                import os

                os.unlink(temp_path)
        else:
            points = []
        ride_data = points_to_ride(points, name=filename, max_points=5000)
        if "error" not in ride_data:
            ride_data["athlete_id"] = user_id
            ride_data["tenant_id"] = tenant_id
            ride_id = save_ride({k: v for k, v in ride_data.items() if k != "id"})
            ride_data["id"] = int(ride_id)
            from ..monitoring import record_gps_import

            record_gps_import(ext or "unknown", "upload")
        return ride_data

    results = await asyncio.gather(
        *(asyncio.to_thread(_process, fn, c) for fn, c in contents),
        return_exceptions=True,
    )

    imported = []
    failed = []
    for filename, result in zip((fn for fn, _ in contents), results, strict=True):
        if isinstance(result, Exception):
            failed.append({"filename": filename, "error": str(result)})
        elif "error" not in result:
            imported.append(result)
    return {
        "imported": imported,
        "failed": failed,
        "count": len(imported),
        "total_files": len(files),
    }


@router.get("/rides/export/json")
async def export_json(current_user: dict = Depends(get_current_user)):
    from fastapi.responses import FileResponse

    from ..analytics.analytics import export_rides_json
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(current_user["id"], tenant_id)]
    with tempfile.NamedTemporaryFile(prefix=f"rides_export_{current_user['id']}_", suffix=".json", delete=False) as tmp:
        path = tmp.name
    export_rides_json(rides, path)
    return FileResponse(
        path,
        media_type="application/json",
        filename="rides.json",
        background=BackgroundTask(os.remove, path),
    )


@router.get("/rides/export/csv")
async def export_csv(current_user: dict = Depends(get_current_user)):
    from fastapi.responses import FileResponse

    from ..analytics.analytics import export_rides_csv
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(current_user["id"], tenant_id)]
    with tempfile.NamedTemporaryFile(prefix=f"rides_export_{current_user['id']}_", suffix=".csv", delete=False) as tmp:
        path = tmp.name
    export_rides_csv(rides, path)
    return FileResponse(
        path,
        media_type="text/csv",
        filename="rides.csv",
        background=BackgroundTask(os.remove, path),
    )


@router.get("/rides/{ride_id}/report")
async def get_ride_report(ride_id: int, current_user: dict = Depends(get_current_user)):
    from ..analytics.analytics import generate_text_report
    from ..db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    return {"report": generate_text_report(Ride(**ride))}


@router.get("/charts/speed/{ride_id}")
async def speed_chart(ride_id: int, current_user: dict = Depends(get_current_user)):
    from ..analytics.analytics import create_speed_chart
    from ..db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points")
    points = [GPSPoint(**p) for p in gps_points]
    from ..processing.processing import build_segments

    segments = build_segments(points)
    path = f"ride_{ride_id}_speed.png"
    await asyncio.to_thread(create_speed_chart, segments, path)
    from fastapi.responses import FileResponse

    return FileResponse(path, media_type="image/png", filename="speed.png")


@router.get("/charts/duration")
async def duration_chart(current_user: dict = Depends(get_current_user)):
    from ..analytics.analytics import create_duration_chart
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(current_user["id"], tenant_id)]
    path = "duration_chart.png"
    await asyncio.to_thread(create_duration_chart, rides, path)
    from fastapi.responses import FileResponse

    return FileResponse(path, media_type="image/png", filename="duration.png")


@router.get("/charts/distance/{ride_id}")
async def distance_chart(ride_id: int, current_user: dict = Depends(get_current_user)):
    from ..analytics.analytics import create_distance_chart
    from ..db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points")
    points = [GPSPoint(**p) for p in gps_points]
    from ..processing.processing import build_segments

    segments = build_segments(points)
    path = f"ride_{ride_id}_distance.png"
    await asyncio.to_thread(create_distance_chart, segments, path)
    from fastapi.responses import FileResponse

    return FileResponse(path, media_type="image/png", filename="distance.png")


@router.get("/charts/elevation/{ride_id}")
async def elevation_chart(ride_id: int, current_user: dict = Depends(get_current_user)):
    from ..analytics.analytics import create_elevation_chart
    from ..db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points")
    points = [GPSPoint(**p) for p in gps_points]
    from ..processing.processing import build_segments

    segments = build_segments(points)
    path = f"ride_{ride_id}_elevation.png"
    await asyncio.to_thread(create_elevation_chart, segments, path)
    from fastapi.responses import FileResponse

    return FileResponse(path, media_type="image/png", filename="elevation.png")


@router.post("/athletes", response_model=dict)
async def create_athlete(athlete_data: AthleteCreate, current_user: dict = Depends(get_current_user)):
    """Create or update the authenticated user's athlete profile."""
    from ..db.database import get_athlete as _get_athlete
    from ..db.database import get_athlete_by_name, save_athlete
    from ..db.database import update_athlete as _update

    tenant_id = current_user.get("tenant_id", current_user["id"])
    target_athlete_id = _ensure_int_user_id(current_user)
    existing = _get_athlete(target_athlete_id, tenant_id)
    if not existing:
        existing = _get_athlete(target_athlete_id, None)
    if athlete_data.name:
        existing_by_name = get_athlete_by_name(athlete_data.name)
        if existing_by_name and existing_by_name["id"] != target_athlete_id:
            raise HTTPException(status_code=409, detail="Nome atleta già in uso")

    data = athlete_data.model_dump()
    if existing:
        _update(target_athlete_id, data)
        result = _public_athlete(_get_athlete(target_athlete_id, tenant_id))
        created = False
    else:
        athlete_id = save_athlete(data, athlete_id=target_athlete_id)
        result = _public_athlete(_get_athlete(athlete_id, tenant_id))
        created = True

    from ..events import AthleteUpdated, publish

    await publish(AthleteUpdated.type, {"athlete_id": target_athlete_id, "created": created})
    return result


@router.get("/athletes")
async def list_athletes(current_user: dict = Depends(get_current_user)):
    """Get current user's athlete profile."""
    from ..db.database import get_athlete as _get_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete = _get_athlete(current_user["id"], tenant_id)
    if not athlete:
        return {"athletes": []}
    return {"athletes": [_public_athlete(athlete)]}


@router.get("/athletes/me")
async def get_my_athlete_profile(current_user: dict = Depends(get_current_user)):
    """Get the authenticated user's own athlete profile."""
    from ..db.database import get_athlete as _get_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete = _get_athlete(current_user["id"], tenant_id)
    if not athlete:
        return {"athlete": None, "profile_complete": False}
    profile_complete = (
        athlete.get("age") is not None
        and athlete.get("weight_kg") is not None
        and (athlete.get("experience_level") or "").strip() != ""
    )
    return {"athlete": _public_athlete(athlete), "profile_complete": profile_complete}


@admin_router.get("/athletes")
async def list_all_athletes(current_user: dict = Depends(get_admin_user)):
    """Get all athletes - admin only."""
    from ..db.database import get_all_athletes as _get_all

    athletes = _get_all()
    return {"athletes": athletes}


@router.get("/athletes/{athlete_id}")
async def get_athlete_endpoint(athlete_id: int, current_user: dict = Depends(get_current_user)):
    """Get athlete - user can only see own profile."""
    from ..db.database import get_athlete as _get_athlete

    _ensure_athlete_access(athlete_id, current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    athlete = _get_athlete(athlete_id, tenant_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    return _public_athlete(athlete)


@router.post("/athletes/{athlete_id}/metrics")
async def add_metric(athlete_id: int, metric_data: MetricCreate, current_user: dict = Depends(get_current_user)):
    """Add metric - user can only add metrics to own profile."""
    _ensure_athlete_access(athlete_id, current_user)
    from ..db.database import save_metric

    tenant_id = current_user.get("tenant_id", athlete_id)
    metric_id = save_metric({"athlete_id": athlete_id, "tenant_id": tenant_id, **metric_data.model_dump()})
    return {"id": int(metric_id), "athlete_id": athlete_id, **metric_data.model_dump()}


@router.put("/athletes/{athlete_id}")
async def update_athlete(
    athlete_id: int,
    athlete_data: AthleteUpdate,
    current_user: dict = Depends(get_current_user),
):
    _ensure_athlete_access(athlete_id, current_user)
    from ..db.database import get_athlete as _get
    from ..db.database import get_athlete_by_name
    from ..db.database import update_athlete as _update

    if not _get(athlete_id):
        raise HTTPException(status_code=404, detail="Athlete not found")
    update_data = athlete_data.model_dump(exclude_none=True)
    if update_data.get("name"):
        existing = get_athlete_by_name(update_data["name"])
        if existing and existing["id"] != athlete_id:
            raise HTTPException(status_code=409, detail="Nome atleta già in uso")
    _update(athlete_id, update_data)
    from ..events import AthleteUpdated, publish

    await publish(
        AthleteUpdated.type,
        {"athlete_id": athlete_id, "updated_fields": update_data, "created": False},
    )
    return _public_athlete(_get(athlete_id))


@router.get("/import/google-fit/auth")
async def google_fit_auth(
    request: Request,
    client_id: str | None = Query(None),
    redirect_uri: str | None = Query(None),
    state: str = Query(""),
):
    logger.warning("Deprecated Google Fit OAuth route accessed; use Google Health instead")
    from ..ingestion.google_fit import get_authorization_url

    google_client_id = client_id or _s.google_fit_client_id
    if not google_client_id:
        raise HTTPException(status_code=500, detail="Google Fit OAuth not configured")
    redirect_uri = redirect_uri or _build_redirect_uri(request, "/api/v1/import/google-fit/callback")
    _validate_redirect_uri(redirect_uri, request)
    state = _issue_oauth_state(redirect_uri)
    auth_url = get_authorization_url(google_client_id, redirect_uri=redirect_uri, state=state)
    return {"auth_url": auth_url}


@router.get("/import/google-health/auth")
@limiter.limit("10/minute")
async def google_health_auth(
    request: Request,
    redirect_uri: str | None = Query(None),
    state: str = Query(""),
):
    from ..ingestion.google_health import _compute_code_challenge, _generate_code_verifier, get_authorization_url

    if not _s.google_health_client_id:
        raise HTTPException(status_code=500, detail="Google Health OAuth not configured")
    redirect_uri = redirect_uri or _build_redirect_uri(request, "/api/v1/import/google-health/callback")
    _validate_redirect_uri(redirect_uri, request)
    code_verifier = _generate_code_verifier()
    code_challenge = _compute_code_challenge(code_verifier)
    pkce_id = secrets.token_urlsafe(8)
    pkce_key = f"oauth:pkce:google-health:{pkce_id}"
    await _cache_set(pkce_key, {"code_verifier": code_verifier, "redirect_uri": redirect_uri}, ttl=600)
    state = _issue_oauth_state(redirect_uri, pkce_id=pkce_id)
    auth_url = get_authorization_url(
        _s.google_health_client_id,
        redirect_uri=redirect_uri,
        state=state,
        code_challenge=code_challenge,
    )
    return {"auth_url": auth_url}


@router.get("/import/google-health/callback")
async def google_health_callback(
    request: Request,
    code: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
    redirect_uri: str | None = Query(None),
    state: str = Query(""),
):
    from ..ingestion.google_health import exchange_code_for_token

    if not _s.google_health_client_id or not _s.google_health_client_secret:
        raise HTTPException(status_code=500, detail="Google Health OAuth not configured")
    state_data = _verify_oauth_state(state)
    if not state_data:
        return _google_health_message_html(
            {
                "type": "google-health-error",
                "error": "invalid_state",
                "error_description": "OAuth Google Health: state non valido o scaduto",
            }
        )
    redirect_uri = state_data["redirect_uri"]
    _validate_redirect_uri(redirect_uri, request)

    if error:
        return _google_health_message_html(
            {
                "type": "google-health-error",
                "error": error,
                "error_description": error_description or "OAuth Google Health fallito",
            }
        )

    if not code:
        return _google_health_message_html(
            {
                "type": "google-health-error",
                "error": "missing_code",
                "error_description": "Callback OAuth Google Health ricevuto senza codice",
            }
        )

    code_verifier = ""
    pkce_id = state_data.get("pkce_id") if isinstance(state_data, dict) else None
    if pkce_id:
        pkce_key = f"oauth:pkce:google-health:{pkce_id}"
        pkce_data = await _cached(pkce_key)
        if pkce_data:
            code_verifier = pkce_data.get("code_verifier", "")
    try:
        token_data = exchange_code_for_token(
            _s.google_health_client_id,
            _s.google_health_client_secret,
            code,
            redirect_uri,
            code_verifier=code_verifier,
        )
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 400:
            body = exc.response.text or ""
            if "invalid_grant" in body:
                return _google_health_message_html(
                    {
                        "type": "google-health-error",
                        "error": "invalid_grant",
                        "error_description": "Codice OAuth non valido o scaduto. Riprova l'autorizzazione.",
                    }
                )
        raise HTTPException(
            status_code=502,
            detail=_http_error_detail(exc, "Google Health token exchange failed"),
        ) from exc
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to get access token from Google Health")

    return _google_health_message_html(
        {
            "type": "google-health-success",
            "token": access_token,
            "refresh_token": token_data.get("refresh_token", ""),
        }
    )


@router.post("/import/google-health")
async def import_google_health(payload: GoogleHealthImportPayload, current_user: dict = Depends(get_current_user)):
    from ..db.database import save_ride
    from ..ingestion.google_health import google_health_to_rides
    from ..ingestion.google_oauth_store import get_valid_google_token, store_google_token

    athlete_id = int(current_user["id"])

    access_token = payload.access_token
    refresh_token = payload.refresh_token
    if access_token and refresh_token:
        with contextlib.suppress(Exception):
            store_google_token(
                athlete_id,
                "google_health",
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                },
            )

    stored_token = get_valid_google_token(athlete_id, "google_health")
    if stored_token:
        access_token = stored_token
    elif not access_token:
        raise HTTPException(status_code=400, detail="access_token required or re-authorize Google Health")

    try:
        rides_data = google_health_to_rides(access_token, athlete_id=athlete_id)
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 403:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Google Health access denied: missing or invalid scopes. "
                    "Re-authorize with Google Health permissions."
                ),
            ) from exc
        raise HTTPException(
            status_code=502,
            detail=_http_error_detail(exc, "Google Health import failed"),
        ) from exc
    imported = []
    for ride_data in rides_data:
        ride_data = {k: v for k, v in ride_data.items() if k != "id"}
        ride_data["athlete_id"] = athlete_id
        ride_id = save_ride(ride_data)
        ride_data["id"] = int(ride_id)
        imported.append(ride_data)
    return {"imported": imported, "count": len(imported)}


@router.post("/import/google-fit/token")
async def google_fit_exchange_token(
    request: Request,
    payload: GoogleFitTokenRequest,
    current_user: dict = Depends(get_current_user),
):
    logger.warning("Deprecated Google Fit token exchange route accessed; use Google Health instead")
    from ..ingestion.google_fit import exchange_code_for_token

    client_id = payload.get("client_id") or _s.google_fit_client_id
    client_secret = payload.get("client_secret") or _s.google_fit_client_secret
    if not client_id or not isinstance(client_id, str) or len(client_id) > 256:
        raise HTTPException(status_code=400, detail="Invalid client_id")

    redirect_uri = payload.get("redirect_uri") or _build_redirect_uri(request, "/api/v1/import/google-fit/callback")
    _validate_redirect_uri(redirect_uri, request)

    try:
        token_data = exchange_code_for_token(
            client_id,
            client_secret,
            payload.get("code"),
            redirect_uri,
        )
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 400:
            body = exc.response.text or ""
            if "invalid_grant" in body:
                raise HTTPException(
                    status_code=400,
                    detail="Codice OAuth non valido o scaduto. Riprova l'autorizzazione.",
                ) from exc
        raise HTTPException(
            status_code=400,
            detail=_http_error_detail(exc, "Google Fit token exchange failed"),
        ) from exc
    return {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "expires_in": token_data.get("expires_in"),
    }


@router.get("/import/google-fit/callback")
async def google_fit_callback(
    request: Request,
    code: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
    redirect_uri: str | None = Query(None),
    state: str = Query(""),
):
    """Handle Google Fit OAuth callback - exchange code for token."""
    logger.warning("Deprecated Google Fit callback route accessed; use Google Health instead")
    from ..ingestion.google_fit import exchange_code_for_token

    if not _s.google_fit_client_id or not _s.google_fit_client_secret:
        raise HTTPException(status_code=500, detail="Google Fit OAuth not configured")
    state_data = _verify_oauth_state(state)
    if not state_data:
        return _google_fit_message_html(
            {
                "type": "google-fit-error",
                "error": "invalid_state",
                "error_description": "OAuth Google Fit: state non valido o scaduto",
            }
        )
    redirect_uri = state_data["redirect_uri"]
    _validate_redirect_uri(redirect_uri, request)

    if error:
        return _google_fit_message_html(
            {
                "type": "google-fit-error",
                "error": error,
                "error_description": error_description or "OAuth Google Fit fallito",
            }
        )

    if not code:
        return _google_fit_message_html(
            {
                "type": "google-fit-error",
                "error": "missing_code",
                "error_description": "Callback OAuth Google Fit ricevuto senza codice",
            }
        )

    cache_key = f"oauth:code:google-fit:{code}"
    cached_result = await _cached(cache_key)
    if cached_result:
        return HTMLResponse(content=cached_result["html"])

    try:
        token_data = exchange_code_for_token(_s.google_fit_client_id, _s.google_fit_client_secret, code, redirect_uri)
    except requests.exceptions.HTTPError as exc:
        response = getattr(exc, "response", None)
        if response is not None and response.status_code == 400:
            cached_retry = await _cached(cache_key)
            if cached_retry:
                return HTMLResponse(content=cached_retry["html"])
            return _google_fit_message_html(
                {
                    "type": "google-fit-error",
                    "error": "oauth_error",
                    "error_description": "Codice OAuth già utilizzato o non valido",
                }
            )
        error_body = response.text if response is not None else str(exc)
        return _google_fit_message_html(
            {
                "type": "google-fit-error",
                "error": "token_exchange_failed",
                "error_description": error_body[:200],
            }
        )
    access_token = token_data.get("access_token")
    if not access_token:
        return _google_fit_message_html(
            {
                "type": "google-fit-error",
                "error": "no_access_token",
                "error_description": "Impossibile ottenere access token da Google Fit",
            }
        )

    payload = {
        "type": "google-fit-success",
        "token": access_token,
        "refresh_token": token_data.get("refresh_token", ""),
    }
    html_content = f"<script>window.opener.postMessage({json.dumps(payload)}, window.location.origin); window.close();</script>"
    await _cache_set(cache_key, {"html": html_content}, ttl=300)
    return HTMLResponse(content=html_content)


@router.post("/import/google-fit")
async def import_google_fit(payload: GoogleFitImportPayload, current_user: dict = Depends(get_current_user)):
    logger.warning("Deprecated Google Fit import route accessed; use Google Health instead")
    from ..db.database import save_ride
    from ..ingestion.google_fit import fetch_cycling_activities, google_fit_to_ride
    from ..ingestion.google_oauth_store import get_valid_google_token, store_google_token

    athlete_id = int(current_user["id"])

    access_token = payload.access_token
    refresh_token = payload.refresh_token
    if access_token and refresh_token:
        with contextlib.suppress(Exception):
            store_google_token(
                athlete_id,
                "google_fit",
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                },
            )

    stored_token = get_valid_google_token(athlete_id, "google_fit")
    if stored_token:
        access_token = stored_token
    elif not access_token:
        raise HTTPException(status_code=400, detail="access_token required or re-authorize Google Fit")

    try:
        activities = fetch_cycling_activities(access_token)
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 403:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Google Fit API access denied (HTTP 403). "
                    "Google Fit API has been deprecated by Google. "
                    "Please use Google Health instead."
                ),
            ) from exc
        raise HTTPException(
            status_code=502,
            detail=_http_error_detail(exc, "Google Fit import failed"),
        ) from exc
    rides_data = google_fit_to_ride(activities)
    imported = []
    from ..monitoring import record_gps_import

    for ride_data in rides_data:
        ride_data = {k: v for k, v in ride_data.items() if k != "id"}
        ride_data["athlete_id"] = athlete_id
        ride_data["tenant_id"] = athlete_id
        ride_id = save_ride(ride_data)
        ride_data["id"] = int(ride_id)
        imported.append(ride_data)
        record_gps_import("google_fit_api", "google_fit")
    return {"imported": imported, "count": len(imported)}


@router.get("/scores/athlete/{athlete_id}")
async def get_athlete_scores(athlete_id: int, current_user: dict = Depends(get_current_user)):
    from ..analytics.performance import (
        calculate_efficiency_score,
        calculate_endurance_score,
        calculate_performance_score,
        get_experience_level,
    )
    from ..db.database import get_athlete, get_rides_by_athlete

    # Users can only see their own scores (admin can see all)
    _ensure_athlete_access(athlete_id, current_user)
    athlete = get_athlete(athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    athlete_public = {k: v for k, v in athlete.items() if k != "password_hash"}
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id)]
    if rides:
        latest = rides[-1]
        return {
            "athlete": athlete_public,
            "scores": {
                "performance_score": calculate_performance_score(latest),
                "endurance_score": calculate_endurance_score(rides),
                "efficiency_score": calculate_efficiency_score(latest),
                "experience_level": get_experience_level(AthleteProfile(**_athlete_profile_data(athlete_public))),
            },
        }
    return {
        "athlete": athlete_public,
        "scores": {
            "performance_score": 0,
            "endurance_score": 0,
            "efficiency_score": 0,
            "experience_level": "Beginner",
        },
    }


@router.post("/benchmark/compare")
async def benchmark_compare(ride_data: BenchmarkCompareRequest, current_user: dict = Depends(get_current_user)):
    from ..analytics.benchmark import compare_athlete_to_benchmark
    from ..models.models import AthleteProfile, Ride

    ride = Ride(
        date=ride_data.date,
        distance_km=ride_data.distance_km,
        duration_minutes=ride_data.duration_minutes,
        avg_speed_kmh=ride_data.avg_speed_kmh or 0.0,
        elevation_gain_m=ride_data.elevation_gain_m or 0.0,
    )
    return compare_athlete_to_benchmark(AthleteProfile(), ride.distance_km, ride.avg_speed_kmh, ride.duration_hours)


@router.get("/knowledge")
async def list_knowledge():
    from ..analytics.knowledge_base import get_kb_stats

    stats = get_kb_stats()
    return {
        "topics": stats["topics"],
        "chunks_per_topic": stats["chunks_per_topic"],
        "total_chunks": stats["total_chunks"],
        "total_words": stats["total_words"],
    }


@router.get("/knowledge/search")
@limiter.limit("10/minute")
async def search_knowledge_endpoint(request: Request, query: str = "", max_chunks: int = 4, min_score: float = 0.05):
    from ..analytics.knowledge_base import format_context_for_llm, search_knowledge_base

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


@router.get("/knowledge/stats")
async def knowledge_stats(current_user: dict = Depends(get_current_user)):
    from ..analytics.knowledge_base import get_kb_stats

    stats = get_kb_stats()
    return {
        "topics": stats.get("topics", []),
        "chunks_per_topic": stats.get("chunks_per_topic", {}),
        "total_chunks": stats.get("total_chunks", 0),
        "total_words": stats.get("total_words", 0),
    }


@router.post("/knowledge/reload")
async def reload_knowledge(current_user: dict = Depends(get_admin_user)):
    from ..analytics.knowledge_base import reload_kb

    return reload_kb()


@router.post("/knowledge/init-embeddings")
async def init_kb_embeddings_endpoint(current_user: dict = Depends(get_admin_user)):
    from ..analytics.knowledge_base import init_chroma_db, init_kb_embeddings
    from ..db.postgres_db import get_session

    with get_session() as session:
        pg_result = init_kb_embeddings(session)

    chroma_result = init_chroma_db()

    return {"pgvector": pg_result, "chromadb": chroma_result}


@router.get("/coach/workout")
@limiter.limit("10/minute")
async def workout_recommendations(
    request: Request,
    athlete_id: int = 0,
    current_user: dict = Depends(get_current_user),
):
    from ..analytics.ai_coach import generate_workout_recommendations
    from ..db.database import get_athlete, get_rides_by_athlete
    from ..models.models import AthleteProfile

    try:
        resolved_id = athlete_id if athlete_id else current_user["id"]
        _ensure_athlete_access(resolved_id, current_user)
        rides = [Ride(**r) for r in get_rides_by_athlete(resolved_id)]
        athlete_data = get_athlete(resolved_id)
        if athlete_data:
            athlete_data = _public_athlete(athlete_data)
        athlete = AthleteProfile(**_athlete_profile_data(athlete_data)) if athlete_data else AthleteProfile()
        result = generate_workout_recommendations(athlete, rides)
        return {"recommendations": result}
    except HTTPException:
        raise
    except Exception:
        logger.exception("AI Coach error in workout recommendations")
        return {"recommendations": "AI Coach error. Please try again later."}


@router.get("/coach/full")
@limiter.limit("5/minute")
async def coach_full_data(
    request: Request,
    athlete_id: int = 0,
    current_user: dict = Depends(get_current_user),
):
    from ..analytics.ai_coach import ai_coach_full
    from ..db.database import (
        get_athlete,
        get_rides_by_athlete,
        save_chat_message,
    )
    from ..models.models import AthleteProfile

    try:
        resolved_id = athlete_id
        if athlete_id:
            _ensure_athlete_access(athlete_id, current_user)
        if not resolved_id:
            resolved_id = current_user["id"]
        if not resolved_id:
            profile_message = "Create an athlete profile in the Dashboard to receive personalized recommendations."
            return {
                "training_advice": profile_message,
                "recovery_advice": profile_message,
                "historical_analysis": "",
                "training_scores": [],
                "recovery_scores": [],
                "charts": [],
            }
        rides = [Ride(**r) for r in get_rides_by_athlete(resolved_id)]
        athlete_data = get_athlete(resolved_id)
        if not athlete_data:
            return {
                "training_advice": "Athlete not found. Create a profile in the Dashboard.",
                "recovery_advice": "Athlete not found. Create a profile in the Dashboard.",
                "historical_analysis": "",
                "training_scores": [],
                "recovery_scores": [],
                "charts": [],
            }
        athlete_data = {k: v for k, v in athlete_data.items() if k != "password_hash"}
        athlete = AthleteProfile(**_athlete_profile_data(athlete_data))
        result = ai_coach_full(athlete, rides, resolved_id)
        if athlete_id and result.get("training_advice"):
            tenant_id = current_user.get("tenant_id", resolved_id)
            save_chat_message(resolved_id, "assistant", result["training_advice"][:500], tenant_id)
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("AI Coach error in full report")
        return {
            "training_advice": "AI Coach error. Please try again later.",
            "recovery_advice": "AI Coach error. Please try again later.",
            "historical_analysis": "",
            "training_scores": [],
            "recovery_scores": [],
            "charts": [],
        }


@router.get("/coach/page", response_class=HTMLResponse)
async def coach_page():
    page = Path(__file__).parent.parent / "static" / "ai_coach.html"
    if page.exists():
        return page.read_text(encoding="utf-8")
    return HTMLResponse("<h1>AI Coach page not available</h1>", status_code=404)


@router.get("/coach/recovery")
async def recovery_recommendations(
    fatigue_score: float = 5.0,
    ride_id: int = 0,
    current_user: dict = Depends(get_current_user),
):
    from ..analytics.ai_coach import generate_recovery_recommendations
    from ..db.database import get_athlete, get_ride, get_rides_by_athlete
    from ..models.models import AthleteProfile, Ride

    try:
        ride_obj = None
        athlete_data = None
        if ride_id:
            ride_data = get_ride(ride_id)
            if ride_data:
                _ensure_ride_access(ride_data, current_user)
                ride_obj = Ride(**ride_data)
                athlete_data = get_athlete(ride_data.get("athlete_id"))
        elif current_user:
            tenant_id = current_user.get("tenant_id", current_user["id"])
            rides = get_rides_by_athlete(current_user["id"], tenant_id)
            if rides:
                athlete_data = get_athlete(current_user["id"], tenant_id)
        if athlete_data:
            athlete_data = {k: v for k, v in athlete_data.items() if k != "password_hash"}
        athlete = AthleteProfile(**_athlete_profile_data(athlete_data)) if athlete_data else AthleteProfile()
        result = generate_recovery_recommendations(athlete, [ride_obj] if ride_obj else [], fatigue_score)
        return {"recommendations": result}
    except HTTPException:
        raise
    except Exception:
        logger.exception("AI Coach error in recovery recommendations")
        return {"recommendations": "AI Coach error. Please try again later."}


@router.get("/coach/trends")
async def historical_trends(current_user: dict = Depends(get_current_user)):
    from ..analytics.ai_coach import analyze_historical_trends
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(current_user["id"], tenant_id)]
    return analyze_historical_trends(rides)


@router.get("/rides/{ride_id}/map/google")
async def google_static_map(
    ride_id: int,
    colored: bool = Query(False, description="Color path by speed (green=fast, yellow=medium, red=slow)"),
    current_user: dict = Depends(get_current_user),
):
    from fastapi.responses import FileResponse

    from ..db.database import get_ride as _get_ride
    from ..maps.google_maps import create_google_static_map, get_google_api_key

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points")
    api_key = get_google_api_key()
    if not api_key:
        logger.warning("Google static map requested for ride %d but API key not configured", ride_id)
        raise HTTPException(status_code=500, detail="GOOGLE_MAPS_API_KEY not configured")
    points = [GPSPoint(**p) for p in gps_points]
    suffix = "_colored" if colored else ""
    path = f"ride_{ride_id}_google_map{suffix}.png"
    try:
        create_google_static_map(points, api_key, path, colored=colored)
        logger.info("Google static map generated: %s (colored=%s, %d points)", path, colored, len(points))
    except RuntimeError as exc:
        logger.error("Google static map failed for ride %d: %s", ride_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return FileResponse(path, media_type="image/png", filename="map.png")


@router.get("/rides/{ride_id}/speed-path")
async def ride_speed_path(
    ride_id: int,
    current_user: dict = Depends(get_current_user),
):
    from ..db.database import get_ride as _get_ride
    from ..maps.google_maps import build_speed_colored_path
    from ..models.models import GPSPoint

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points", [])
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points")
    points = [GPSPoint(**p) for p in gps_points]
    segments = build_speed_colored_path(points)
    speeds = [p.speed for p in points if p.speed is not None]
    min_spd = min(speeds) if speeds else 0.0
    max_spd = max(speeds) if speeds else 35.0
    center_lat = sum(p.lat for p in points) / len(points) if points else 0.0
    center_lon = sum(p.lon for p in points) / len(points) if points else 0.0
    return {
        "ride_id": ride_id,
        "segments": segments,
        "min_speed": min_spd,
        "max_speed": max_spd,
        "point_count": len(points),
        "center": {
            "lat": center_lat,
            "lon": center_lon,
        },
    }


@admin_router.get("/backup")
async def create_backup(current_user: dict = Depends(get_admin_user)):
    from fastapi.responses import FileResponse

    from ..db.database import backup_database

    path = backup_database()
    log_action(current_user["id"], "download_backup", "database")
    return FileResponse(path, media_type="application/octet-stream", filename="backup.db")


@admin_router.post("/backup/scheduled")
async def create_scheduled_backup(current_user: dict = Depends(get_admin_user)):
    from ..db.database import scheduled_backup

    result = scheduled_backup(max_backups=10)
    log_action(current_user["id"], "scheduled_backup", "database")
    return result


@admin_router.post("/indexes")
async def create_db_indexes(current_user: dict = Depends(get_admin_user)):
    from ..db.database import create_indices

    create_indices()
    log_action(current_user["id"], "create_indexes", "database")
    return {"status": "indexes_created"}


@admin_router.get("/stats")
async def get_system_stats(current_user: dict = Depends(get_admin_user)):
    from ..db.database import get_all_rides

    rides = get_all_rides()
    total_km = sum(r.get("distance_km", 0) for r in rides)
    total_duration = sum(r.get("duration_minutes", 0) for r in rides)
    db_size = Path(_s.db_path).stat().st_size if Path(_s.db_path).exists() else 0
    log_action(current_user["id"], "view_stats", "system")
    return {
        "rides_count": len(rides),
        "total_km": round(total_km, 1),
        "total_duration_hours": round(total_duration / 60, 1),
        "db_size_bytes": db_size,
    }


@admin_router.post("/reset-demo")
async def reset_demo_data(current_user: dict = Depends(get_admin_user)):
    from ..db.database import delete_ride, get_all_rides

    rides = get_all_rides()
    for r in rides:
        if "demo" in r.get("date", ""):
            delete_ride(r["id"])
    from scripts.generate_sample_ride import generate_sample_ride

    generate_sample_ride()
    log_action(current_user["id"], "reset_demo", "system")
    return {"status": "demo_reset", "message": "Demo data regenerated"}


@admin_router.get("/ceo")
async def ceo_analytics(current_user: dict = Depends(get_admin_user)):
    from ..db.database import get_all_athletes, get_all_rides

    rides = get_all_rides()
    athletes = get_all_athletes()
    total_rides = len(rides)
    total_athletes = len(athletes)
    total_km = sum(r.get("distance_km", 0) for r in rides)
    total_hours = sum(r.get("duration_minutes", 0) for r in rides) / 60
    total_calories = sum(r.get("calories", 0) for r in rides)
    from datetime import datetime

    now = datetime.now()
    this_month = sum(1 for r in rides if r.get("date", "").startswith(now.strftime("%Y-%m")))
    last_month = sum(
        1
        for r in rides
        if r.get("date", "").startswith(f"{now.year}-{now.month - 1:02d}" if now.month > 1 else f"{now.year - 1}-12")
    )
    db_size = Path(_s.db_path).stat().st_size if Path(_s.db_path).exists() else 0
    level_counts = {"Beginner": 0, "Amateur": 0, "Intermediate": 0, "Advanced": 0, "Elite": 0}
    for a in athletes:
        level = a.get("experience_level", "Beginner")
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
            "database_size_bytes": db_size,
            "database_size_mb": round(db_size / (1024 * 1024), 2),
            "last_updated": now.isoformat(),
        },
    }


@router.put("/rides/{ride_id}")
async def update_ride(ride_id: int, ride: RideUpdate, current_user: dict = Depends(get_current_user)):
    from ..db.database import get_ride as _get_ride
    from ..db.database import update_ride as _update_ride

    existing = _get_ride(ride_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(existing, current_user)
    protected = {k: v for k, v in existing.items() if k in ("id", "athlete_id", "created_at")}
    update_data = {k: v for k, v in ride.model_dump().items() if v is not None and k not in protected}
    merged = {**existing, **update_data}
    _update_ride(ride_id, merged)
    return merged


@router.get("/coach/chat")
async def coach_chat(
    athlete_id: int = Query(...),
    message: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    return await _process_chat(athlete_id, message, current_user)


@router.post("/coach/chat")
async def coach_chat_post(
    request: Request,
    current_user: dict = Depends(get_current_user),
):

    body = await request.json()
    chat_req = CoachChatRequest(**body)
    athlete_id = chat_req.athlete_id or current_user["id"]
    return await _process_chat(athlete_id, chat_req.message, current_user)


async def _process_chat(athlete_id: int, message: str, current_user: dict):
    from ..analytics.ai_coach import generate_training_advice
    from ..db.database import (
        get_athlete,
        get_chat_history,
        get_rides_by_athlete,
        save_athlete,
        save_chat_message,
    )
    from ..models.models import AthleteProfile

    tenant_id = current_user.get("tenant_id", athlete_id)
    _ensure_athlete_access(athlete_id, current_user)

    # The chat_history table has a FK on athlete_id. If the athlete row is
    # missing (e.g. the SQLite DB was reset after a redeploy while the client
    # still holds a valid token) the INSERT would raise IntegrityError and
    # surface as an unhandled 500. Provision the profile so the chat works.
    if get_athlete(athlete_id) is None:
        save_athlete(
            {
                "name": current_user.get("name") or f"Athlete {athlete_id}",
                "email": current_user.get("email"),
                "picture": current_user.get("picture"),
                "experience_level": "Beginner",
                "tenant_id": tenant_id,
            },
            athlete_id=athlete_id,
            tenant_id=tenant_id,
        )

    save_chat_message(athlete_id, "user", message[:500], tenant_id)
    athlete_data = get_athlete(athlete_id, tenant_id)
    if athlete_data:
        athlete_data = {k: v for k, v in athlete_data.items() if k != "password_hash"}
    athlete = AthleteProfile(**_athlete_profile_data(athlete_data)) if athlete_data else AthleteProfile()
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id, tenant_id=tenant_id)]
    response = generate_training_advice(athlete, rides, athlete_id)
    save_chat_message(athlete_id, "assistant", response[:500], tenant_id)
    return {"response": response, "history": get_chat_history(athlete_id, tenant_id=tenant_id)}


@router.get("/analytics/speed-data")
async def speed_analytics(limit: int = Query(10, ge=1, le=50), current_user: dict = Depends(get_current_user)):
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = get_rides_by_athlete(current_user["id"], tenant_id)
    recent = rides[-limit:] if len(rides) > limit else rides
    return {
        "labels": [r.get("date", "Ride")[-10:] if r.get("date") else "Ride" for r in recent],
        "speeds": [r.get("avg_speed_kmh", 0) for r in recent],
        "distances": [r.get("distance_km", 0) for r in recent],
    }


@router.get("/maps/places/nearby")
async def nearby_places(
    ride_id: int,
    query: str = Query(..., description="e.g.: cafe, bakery, restaurant"),
    use_osm: bool = Query(False),
    current_user: dict = Depends(get_current_user),
):
    """Get nearby places for a ride - uses OSM (no API key) or SerpApi."""
    from ..db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points for this ride")
    points = [GPSPoint(**p) for p in gps_points]
    center_lat = round(sum(p.lat for p in points) / len(points), 3)
    center_lon = round(sum(p.lon for p in points) / len(points), 3)
    cache_key_str = f"places:nearby:{use_osm}:{query}:{center_lat}:{center_lon}"
    cached_result = _place_cache_get(cache_key_str)
    if cached_result is not None:
        logger.debug("Place search cache hit: nearby %s", query)
        return cached_result
    if use_osm:
        from ..maps.osm_maps import get_local_results as osm_search

        results = await osm_search(points, query=query)
    else:
        results = await get_local_results(points, query=query)
    if results is None:
        raise HTTPException(status_code=502, detail="Place search request failed")
    resp = {"query": query, "count": len(results), "results": results}
    _place_cache_set(cache_key_str, resp)
    logger.debug("Place search cached: nearby %s (%d results)", query, len(results))
    return resp


@router.get("/maps/places/osm-search")
async def osm_places_search(
    lat: float = Query(...),
    lon: float = Query(...),
    query: str = Query(...),
    limit: int = Query(10),
):
    """OpenStreetMap search for places - no API key required."""
    cache_key_str = f"places:osm:{query}:{round(lat, 3)}:{round(lon, 3)}:{limit}"
    cached_result = _place_cache_get(cache_key_str)
    if cached_result is not None:
        logger.debug("Place search cache hit: osm %s", query)
        return cached_result
    result = await search_places(query, lat=lat, lon=lon, limit=limit)
    resp = {"query": query, "results": result.get("results", []) if result else []}
    _place_cache_set(cache_key_str, resp)
    logger.debug("Place search cached: osm %s", query)
    return resp


@router.get("/maps/places/search")
async def search_places_endpoint(
    ride_id: int,
    query: str = Query(..., description="Place search query"),
    current_user: dict = Depends(get_current_user),
):
    """Search places using SerpApi for a ride - user must own the ride."""
    from ..db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points for this ride")
    points = [GPSPoint(**p) for p in gps_points]
    if not _s.serpapi_api_key:
        raise HTTPException(status_code=500, detail="SERPAPI_API_KEY not configured")
    data = await search_nearby(points, query=query)
    if data is None:
        raise HTTPException(status_code=502, detail="SerpApi request failed")
    return data


@router.post("/calendar/events")
async def create_calendar_event(event_data: CalendarEventCreate, current_user: dict = Depends(get_current_user)):
    from ..db.database import get_calendar_event, save_calendar_event
    from ..utils.dates import date_only

    event_data_dict = event_data.model_dump()
    event_data_dict["date"] = date_only(event_data_dict.get("date"))
    event_data_dict["tenant_id"] = current_user.get("tenant_id", current_user["id"])
    _ensure_athlete_access(event_data_dict["athlete_id"], current_user)
    event_id = save_calendar_event(event_data_dict)
    event = get_calendar_event(int(event_id))
    return event


@router.get("/calendar/events")
async def list_calendar_events(
    athlete_id: int = Query(...),
    year: int = Query(...),
    month: int = Query(...),
    current_user: dict = Depends(get_current_user),
):
    from ..db.database import get_events_by_month

    tenant_id = current_user.get("tenant_id", athlete_id)
    _ensure_athlete_access(athlete_id, current_user)
    events = get_events_by_month(athlete_id, year, month, tenant_id)
    return {"events": events}


@router.get("/calendar/events/range")
async def list_events_by_range(
    athlete_id: int = Query(...),
    start: str = Query(...),
    end: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    from ..db.database import get_events_by_date_range

    tenant_id = current_user.get("tenant_id", athlete_id)
    _ensure_athlete_access(athlete_id, current_user)
    events = get_events_by_date_range(athlete_id, start, end, tenant_id)
    return {"events": events}


@router.get("/calendar/events/{event_id}")
async def get_calendar_event_endpoint(event_id: int, current_user: dict = Depends(get_current_user)):
    from ..db.database import get_calendar_event

    event = get_calendar_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    _ensure_athlete_access(event["athlete_id"], current_user)
    return event


@router.put("/calendar/events/{event_id}")
async def update_calendar_event_endpoint(
    event_id: int, event_data: CalendarEventUpdate, current_user: dict = Depends(get_current_user)
):
    from ..db.database import get_calendar_event, update_calendar_event
    from ..utils.dates import date_only

    update_dict = event_data.model_dump(exclude_none=True)
    if update_dict.get("date"):
        update_dict["date"] = date_only(update_dict.get("date"))
    event = get_calendar_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    _ensure_athlete_access(event["athlete_id"], current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    ok = update_calendar_event(event_id, update_dict, tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found")
    from ..db.database import get_calendar_event

    return get_calendar_event(event_id)


@router.delete("/calendar/events/{event_id}")
async def delete_calendar_event_endpoint(event_id: int, current_user: dict = Depends(get_current_user)):
    from ..db.database import delete_calendar_event, get_calendar_event

    event = get_calendar_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    _ensure_athlete_access(event["athlete_id"], current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    ok = delete_calendar_event(event_id, tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"deleted": True}


@router.post("/calendar/events/{event_id}/complete")
async def toggle_event_complete(event_id: int, current_user: dict = Depends(get_current_user)):
    from ..db.database import get_calendar_event, update_calendar_event

    event = get_calendar_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    _ensure_athlete_access(event["athlete_id"], current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    update_calendar_event(event_id, {"completed": not event["completed"]}, tenant_id)
    return get_calendar_event(event_id)


@router.get("/training/load")
async def get_training_load(
    athlete_id: int = Query(...),
    days: int = Query(30, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
):
    """Get ATL/CTL/TSB training load metrics for athlete."""
    from ..analytics.training_load import calculate_atl_ctl_tsb
    from ..db.database import get_rides_by_athlete

    # Users can only see their own training load (admin can see all)
    _ensure_athlete_access(athlete_id, current_user)
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id)]
    loads = calculate_atl_ctl_tsb(rides)
    recent = loads[-days:] if len(loads) > days else loads
    return {"athlete_id": athlete_id, "days": days, "training_loads": list(recent)}


@router.get("/training/status")
async def get_training_status(athlete_id: int = Query(...), current_user: dict = Depends(get_current_user)):
    """Get current fitness status with ATL/CTL/TSB recommendation."""
    from ..analytics.training_load import get_current_training_status
    from ..db.database import get_rides_by_athlete

    # Users can only see their own training status (admin can see all)
    _ensure_athlete_access(athlete_id, current_user)
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id)]
    status = get_current_training_status(rides)
    return {"athlete_id": athlete_id, **status}


@router.get("/training/summary")
async def get_7day_summary(athlete_id: int = Query(...), current_user: dict = Depends(get_current_user)):
    """Get 7-day fitness summary for dashboard."""
    from ..analytics.training_load import get_7day_fitness_summary
    from ..db.database import get_rides_by_athlete

    # Users can only see their own summary (admin can see all)
    _ensure_athlete_access(athlete_id, current_user)
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id)]
    summary = get_7day_fitness_summary(rides)
    return {"athlete_id": athlete_id, "summary": summary}


@router.post("/training/goals")
async def create_training_goal(goal_data: dict, current_user: dict = Depends(get_current_user)):
    """Create a training goal for an athlete."""
    from ..db.postgres_db import SQLALCHEMY_AVAILABLE, save_training_goal

    if not SQLALCHEMY_AVAILABLE:
        raise HTTPException(status_code=500, detail="SQLAlchemy not available")
    goal_athlete_id = goal_data.get("athlete_id") or current_user["id"]
    _ensure_athlete_access(goal_athlete_id, current_user)
    goal = {
        "athlete_id": goal_athlete_id,
        "title": goal_data.get("title", ""),
        "description": goal_data.get("description"),
        "goal_type": goal_data.get("goal_type", "granfondo"),
        "target_date": goal_data.get("target_date"),
        "target_distance_km": goal_data.get("target_distance_km"),
        "target_elevation_m": goal_data.get("target_elevation_m"),
        "status": "active",
    }
    goal_id = save_training_goal(goal["athlete_id"], goal)
    return {"id": goal_id, **goal}


@router.get("/training/goals")
async def list_training_goals(
    athlete_id: int = Query(...),
    status: str = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """List training goals for athlete."""
    from ..db.postgres_db import SQLALCHEMY_AVAILABLE, get_training_goals

    if not SQLALCHEMY_AVAILABLE:
        raise HTTPException(status_code=500, detail="SQLAlchemy not available")
    # Users can only see their own goals (admin can see all)
    _ensure_athlete_access(athlete_id, current_user)
    goals = get_training_goals(athlete_id, status)
    return {"goals": goals}


@router.post("/training/workouts/generate")
async def generate_workouts(
    goal_id: int = Body(...),
    event_count: int = Body(12, ge=4, le=20),
    current_user: dict = Depends(get_current_user),
):
    """Generate planned workouts for a granfondo goal."""
    from datetime import datetime, timedelta

    from ..analytics.training_load import get_current_training_status
    from ..db.database import get_rides_by_athlete
    from ..db.postgres_db import PlannedWorkoutModel, TrainingGoalModel, get_session
    from ..models.models import Ride

    with get_session() as session:
        goal = session.query(TrainingGoalModel).filter(TrainingGoalModel.id == goal_id).first()
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        if goal.athlete_id is None:
            raise HTTPException(status_code=422, detail="Goal has no associated athlete")
        _ensure_athlete_access(goal.athlete_id, current_user)

        rides = [Ride(**r) for r in get_rides_by_athlete(goal.athlete_id)]
        get_current_training_status(rides) if rides else {"ctl": 0}

        workouts_to_create = []
        start_date = datetime.now()

        workout_plan = [
            ("Base aerobica", "endurance", 0.5),
            ("Progressivo", "endurance", 0.6),
            ("Base aerobica", "endurance", 0.5),
            ("Thresholds", "threshold", 0.75),
            ("Recupero", "recovery", 0.4),
            ("Base aerobica", "endurance", 0.55),
            ("Progressivo", "sweetspot", 0.8),
            ("Recupero", "recovery", 0.45),
            ("Thresholds", "threshold", 0.75),
            ("Base aerobica", "endurance", 0.5),
            ("Pre-gara", "openers", 0.65),
            ("Giorno gara", "race", 0.9),
        ]

        for i in range(min(event_count, len(workout_plan))):
            workout_date = (start_date + timedelta(days=7 * i)).strftime("%Y-%m-%d")
            title, wtype, intensity = workout_plan[i]
            workouts_to_create.append(
                PlannedWorkoutModel(
                    athlete_id=goal.athlete_id,
                    goal_id=goal_id,
                    date=workout_date,
                    title=title,
                    workout_type=wtype,
                    duration_minutes=90,
                    target_intensity=intensity,
                )
            )

        session.add_all(workouts_to_create)
        return {"generated": len(workouts_to_create), "goal_id": goal_id}


@router.get("/weather")
async def get_weather(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    date: str | None = Query(None, description="Date (YYYY-MM-DD) or today"),
):
    """Get weather for coordinates, optionally for a specific date."""
    from ..weather.weather_service import (
        get_forecast_for_date,
        get_weather_for_coordinates,
        get_weather_score,
    )

    if not _s.weather_api_key:
        raise HTTPException(status_code=500, detail="WEATHER_API_KEY not configured in .env file")

    weather = get_forecast_for_date(lat, lon, date) if date else get_weather_for_coordinates(lat, lon)

    if "error" in weather:
        raise HTTPException(status_code=502, detail=weather["error"])

    temp = weather.get("temperature")
    humidity = weather.get("humidity")

    score, advice = (
        get_weather_score(temp, humidity)
        if temp is not None and humidity is not None
        else (5, "Weather data not available")
    )

    weather["score"] = score
    weather["advice"] = advice

    return weather


@router.get("/weather/forecast")
async def get_weather_forecast(
    lat: float = Query(..., description="Latitudine"),
    lon: float = Query(..., description="Longitudine"),
    days: int = Query(7, ge=1, le=5),
):
    """Get multi-day weather forecast."""
    from datetime import datetime, timedelta

    from ..weather.weather_service import get_forecast_for_date, get_weather_score

    if not _s.weather_api_key:
        raise HTTPException(status_code=500, detail="WEATHER_API_KEY not configured in .env file")

    forecasts = []
    today = datetime.now()

    for i in range(days):
        date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        weather = get_forecast_for_date(lat, lon, date)
        if "error" not in weather:
            temp = weather.get("temperature")
            humidity = weather.get("humidity")
            score, advice = get_weather_score(temp, humidity) if temp and humidity else (5, "")
            weather["score"] = score
            weather["advice"] = advice
            weather["date"] = date
        forecasts.append(weather)

    return {"forecasts": forecasts}


@router.get("/analytics/trends")
async def get_fitness_trends(
    metric: str = Query("distance_km"),
    window: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
):
    """Get fitness trend analysis for athlete's rides."""
    from ..analytics.analytics_trends import calculate_fitness_trends
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(current_user["id"], tenant_id)]
    return calculate_fitness_trends(rides, metric=metric, window=window)


@router.get("/analytics/monthly")
async def get_monthly_progression(current_user: dict = Depends(get_current_user)):
    """Get monthly aggregated metrics for athlete's rides."""
    from ..analytics.analytics_trends import calculate_monthly_progression
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = get_rides_by_athlete(current_user["id"], tenant_id)
    return calculate_monthly_progression(rides)


@router.get("/analytics/comparison")
async def get_period_comparison(
    period_days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
):
    """Compare recent vs previous period for athlete's rides."""
    from ..analytics.analytics_trends import calculate_period_comparison
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(current_user["id"], tenant_id)]
    return calculate_period_comparison(rides, period_days=period_days)


@router.get("/analytics/projection")
async def get_volume_projection(
    target_days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Project future training volume based on historical trend for athlete's rides."""
    from ..analytics.analytics_trends import calculate_training_volume_projection
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(current_user["id"], tenant_id)]
    return calculate_training_volume_projection(rides, target_days=target_days)


@router.get("/heatmap")
async def get_heatmap(athlete_id: int = Query(0), current_user: dict = Depends(get_current_user)):
    """Get heatmap data from all GPS points for an athlete."""
    from ..db.database import get_rides_by_athlete

    target_id = athlete_id if athlete_id and current_user.get("is_admin") else current_user["id"]
    if athlete_id:
        _ensure_athlete_access(athlete_id, current_user)
    rides = [Ride(**r) for r in get_rides_by_athlete(target_id)]
    rides_dict = [r.to_dict() for r in rides]
    data = get_heatmap_points(rides_dict)
    return data


@router.get("/badges")
async def get_badges(athlete_id: int = Query(...), current_user: dict = Depends(get_current_user)):
    """Get badge achievements for an athlete."""
    from ..db.database import get_athlete, get_rides_by_athlete

    # Users can only see their own badges (admin can see all)
    _ensure_athlete_access(athlete_id, current_user)
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id)]
    athlete = get_athlete(athlete_id)
    badges = calculate_badges(athlete_id, [r.to_dict() for r in rides], athlete)
    achieved_count = sum(1 for b in badges if b["achieved"])
    from ..events import BadgeEarned, publish

    for badge in badges:
        if badge.get("achieved"):
            await publish(
                BadgeEarned.type,
                {
                    "athlete_id": athlete_id,
                    "badge_id": badge.get("id"),
                    "badge_name": badge.get("name"),
                },
            )
    return {
        "athlete_id": athlete_id,
        "badges": badges,
        "total_badges": len(badges),
        "achieved": achieved_count,
    }


@router.post("/training/granfondo/plan")
async def generate_granfondo_workouts(
    request: GranfondoPlanRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generate granfondo training plan with tapering."""
    start_date = request.start_date
    weeks = request.target_weeks
    athlete_id = request.athlete_id if request.athlete_id else current_user["id"]
    _ensure_athlete_access(athlete_id, current_user)
    plan = generate_granfondo_plan(start_date, weeks)
    from ..events import TrainingGenerated, publish

    await publish(
        TrainingGenerated.type,
        {"athlete_id": athlete_id, "type": "granfondo_plan", "weeks": weeks},
    )
    return {
        "athlete_id": athlete_id,
        "start_date": start_date,
        "weeks": weeks,
        "plan": plan,
        "total_workouts": len(plan),
    }


def _granfondo_event_type(workout_type: str) -> str:
    """Map a granfondo workout type to a valid calendar event type."""
    if workout_type == "race":
        return "race"
    if workout_type == "recovery":
        return "recovery"
    return "training"


@router.post("/training/granfondo/save")
async def save_granfondo_plan(
    request: GranfondoSaveRequest,
    current_user: dict = Depends(get_current_user),
):
    """Persist a generated granfondo plan as calendar events."""
    from ..db.database import save_calendar_event
    from ..utils.dates import date_only

    athlete_id = request.athlete_id if request.athlete_id else current_user["id"]
    _ensure_athlete_access(athlete_id, current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])

    event_ids: list[int] = []
    for workout in request.plan:
        event = {
            "athlete_id": athlete_id,
            "title": workout.title,
            "event_type": _granfondo_event_type(workout.workout_type),
            "date": date_only(workout.date),
            "duration_minutes": workout.duration_minutes,
            "description": workout.description or "",
            "completed": False,
            "tenant_id": tenant_id,
        }
        event_ids.append(int(save_calendar_event(event)))

    return {
        "saved": len(event_ids),
        "event_ids": event_ids,
        "athlete_id": athlete_id,
    }


@router.get("/analytics/multi-classify")
async def multi_classify_rides(
    athlete_id: int | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Classify athlete rides into multiple performance categories."""
    from ..analytics.multi_classifier import classify_rides

    rides = _get_athlete_rides(athlete_id or current_user["id"], current_user)
    results = classify_rides(rides)
    return {
        "athlete_id": athlete_id or current_user["id"],
        "total_rides": len(results),
        "rides": [
            {
                "ride_id": r.ride_id,
                "date": r.date,
                "categories": r.categories,
                "primary_category": r.primary_category,
                "confidence": r.confidence,
                "metrics": r.metrics,
            }
            for r in results
        ],
    }


@router.get("/analytics/vip")
async def get_vip_prediction(
    athlete_id: int | None = None,
    ftp: float = Query(250.0),
    current_user: dict = Depends(get_current_user),
):
    """Get VIP (Very Important Performance) prediction for athlete."""
    from ..analytics.vip_predictor import estimate_vip

    rides = _get_athlete_rides(athlete_id or current_user["id"], current_user)
    result = estimate_vip(rides, athlete_ftp=ftp)
    return {
        "athlete_id": athlete_id or current_user["id"],
        "probability_index": result.probability_index,
        "readiness_score": result.readiness_score,
        "recommendation": result.recommendation,
        "risk_factors": result.risk_factors,
    }


@router.get("/analytics/inactivity")
async def get_inactivity_report(
    athlete_id: int | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Estimate fitness decay after inactivity."""
    from ..analytics.inactivity_estimator import estimate_inactivity

    rides = _get_athlete_rides(athlete_id or current_user["id"], current_user)
    result = estimate_inactivity(rides)
    return {
        "athlete_id": athlete_id or current_user["id"],
        "current_streak_days": result.current_streak_days,
        "estimated_ftp_loss_pct": result.estimated_ftp_loss_pct,
        "estimated_endurance_loss_pct": result.estimated_endurance_loss_pct,
        "recovery_plan_days": result.recovery_plan_days,
        "advice": result.advice,
    }


@router.get("/analytics/route-suggestions")
async def get_route_suggestions(
    athlete_id: int | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Suggest ride routes based on historical preferences."""
    from ..analytics.ride_route_estimator import estimate_route_preferences
    from ..db.database import get_athlete

    athlete_id = athlete_id or current_user["id"]
    athlete_data = get_athlete(athlete_id)
    if not athlete_data:
        athlete_data = {"name": "Unknown", "preferred_terrain": "mixed", "ftp_watts": 250.0}
    athlete = AthleteProfile(**athlete_data)
    rides = _get_athlete_rides(athlete_id, current_user)
    suggestions = estimate_route_preferences(athlete, rides)
    return {
        "athlete_id": athlete_id,
        "total_suggestions": len(suggestions),
        "routes": [
            {
                "name": s.name,
                "distance_km": s.distance_km,
                "elevation_gain_m": s.elevation_gain_m,
                "avg_speed_target_kmh": s.avg_speed_target_kmh,
                "duration_minutes": s.duration_minutes,
                "terrain": s.terrain,
                "rationale": s.rationale,
            }
            for s in suggestions
        ],
    }


@router.get("/rides/{ride_id}/power-metrics")
async def get_ride_power_metrics(
    ride_id: int,
    ftp: float = Query(250.0, description="FTP in watts"),
    current_user: dict = Depends(get_current_user),
):
    """Get advanced power metrics for a ride with power data."""
    from ..analytics.power_model import calculate_advanced_power_metrics
    from ..db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points for this ride")
    points = [GPSPoint(**p) for p in gps_points]
    metrics = calculate_advanced_power_metrics(points, ftp=ftp)
    return {"ride_id": ride_id, "ftp": ftp, **metrics}


@router.get("/traffic/road-types")
async def get_road_types(lat: float = Query(...), lon: float = Query(...), radius_km: float = Query(2.0)):
    """Get road type distribution for an area using OSM Overpass."""
    from ..traffic.overpass_client import get_road_type_summary

    points = [{"lat": lat, "lon": lon}]
    summary = get_road_type_summary(points)
    return {"lat": lat, "lon": lon, "radius_km": radius_km, "road_types": summary}


@router.get("/traffic/bike-infrastructure")
async def get_bike_infrastructure(lat: float = Query(...), lon: float = Query(...), radius_km: float = Query(2.0)):
    """Get bike lanes and cycleways for an area using OSM Overpass."""
    from ..traffic.overpass_client import fetch_bike_lanes

    points = [{"lat": lat, "lon": lon}]
    data = fetch_bike_lanes(points, include_geometry=False)
    count = len(data.get("elements", [])) if data else 0
    return {
        "lat": lat,
        "lon": lon,
        "radius_km": radius_km,
        "bike_lanes_count": count,
        "elements": data.get("elements", []) if data else [],
    }


@router.get("/traffic/incidents")
async def get_traffic_incidents(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_km: float = Query(5.0),
    days: int = Query(90, ge=1, le=365),
):
    """Get traffic incidents near coordinates."""
    from ..traffic.incident_fetcher import fetch_incidents, get_incident_stats

    radius = radius_km if radius_km > 0 else _s.incident_radius_km
    lookback = days if days > 0 else _s.incident_days
    incidents = fetch_incidents(lat, lon, radius_km=radius, days=lookback)
    stats = get_incident_stats(incidents)
    return {
        "lat": lat,
        "lon": lon,
        "radius_km": radius,
        "days": lookback,
        "incidents": incidents,
        "stats": stats,
    }


@router.get("/rides/{ride_id}/safety")
async def analyze_ride_safety(ride_id: int, current_user: dict = Depends(get_current_user)):
    """Analyze route safety for a ride using OSM data and incident data."""
    from ..db.database import get_ride as _get_ride
    from ..db.database import get_route_safety_score
    from ..traffic.incident_fetcher import fetch_incidents
    from ..traffic.safety_analyzer import analyze_route_safety

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    existing = get_route_safety_score(ride_id, tenant_id)
    if existing and existing.get("computed_at"):
        return existing
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points for this ride")
    points = [{"lat": p["lat"], "lon": p["lon"]} for p in gps_points]
    lats = [p["lat"] for p in points]
    lons = [p["lon"] for p in points]
    center_lat = sum(lats) / len(lats) if lats else 0.0
    center_lon = sum(lons) / len(lons) if lons else 0.0
    incidents = fetch_incidents(center_lat, center_lon, radius_km=_s.incident_radius_km, days=_s.incident_days)
    safety = await analyze_route_safety(points, incidents=incidents)
    safety["ride_id"] = ride_id
    safety["athlete_id"] = ride.get("athlete_id")
    safety["tenant_id"] = current_user.get("tenant_id", current_user["id"])
    from ..db.database import save_route_safety_score

    score_id = save_route_safety_score(safety)
    safety["id"] = score_id
    safety["computed_at"] = datetime.now(UTC).isoformat()
    return safety


# ------------------------------------------------------------------
# Strava integration routes
# ------------------------------------------------------------------


def _strava_redirect_uri_for(request: Request) -> str:
    """Resolve the Strava OAuth redirect URI.

    Prefers the explicitly configured ``STRAVA_REDIRECT_URI`` (set per
    environment in ``.env`` / ``render.yaml`` and pre-registered in the Strava
    app). Only falls back to the request host when no redirect URI is
    configured, so the value always matches what Strava expects.
    """
    if _s.strava_redirect_uri:
        return _s.strava_redirect_uri
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if not host:
        return "http://localhost:8000/api/v1/import/strava/callback"
    return f"{proto}://{host}/api/v1/import/strava/callback"


@router.get("/import/strava/auth")
async def strava_auth(
    request: Request,
    state: str = "",
    current_user: dict = Depends(get_current_user),
):
    from ..ingestion.strava_client import get_authorization_url

    try:
        result = get_authorization_url(
            state=state, redirect_uri=_strava_redirect_uri_for(request)
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    logger.debug(
        "Strava auth redirect_uri=%s", _strava_redirect_uri_for(request)
    )
    result["athlete_id"] = current_user["id"]
    return result


@router.get("/import/strava/callback")
async def strava_callback_page(
    code: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
    state: str = Query(""),
):
    """Handle Strava OAuth redirect (popup) and relay the result to the opener.

    The Strava popup cannot be polled via `popup.location` when the app sets
    `Cross-Origin-Opener-Policy: same-origin` (it blocks the cross-origin window
    access). Instead we serve a tiny page that postMessages the result back to
    the opener window, which is COOP-safe.
    """
    if error:
        return _strava_message_html(
            {
                "type": "strava-error",
                "error": error,
                "error_description": error_description or "Strava OAuth fallito",
            }
        )
    if not code:
        return _strava_message_html(
            {
                "type": "strava-error",
                "error": "missing_code",
                "error_description": "Callback Strava ricevuto senza codice",
            }
        )
    return _strava_message_html({"type": "strava-success", "code": code})


@router.post("/import/strava/callback")
async def strava_callback(
    payload: StravaCallbackRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    from ..ingestion.strava_client import exchange_code_for_token, store_token

    code = payload.code
    code_verifier = payload.code_verifier
    redirect_uri = _strava_redirect_uri_for(request)
    logger.debug("Strava token exchange redirect_uri=%s", redirect_uri)
    try:
        token_data = await exchange_code_for_token(
            code, code_verifier, redirect_uri=redirect_uri
        )
    except httpx.HTTPStatusError as exc:
        detail = f"Strava token exchange failed: {exc}"
        if exc.response is not None and exc.response.text:
            detail += f" | Strava: {exc.response.text}"
        raise HTTPException(status_code=502, detail=detail) from exc
    store_token(current_user["id"], token_data)
    return {
        "status": "connected",
        "athlete_id": current_user["id"],
        "athlete_name": token_data.get("athlete", {}).get("firstname", ""),
    }


@router.post("/import/strava/sync")
async def strava_sync(
    background: bool = True,
    current_user: dict = Depends(get_current_user),
):
    from ..task_queue import get_task_queue

    payload = {"athlete_id": current_user["id"]}
    if background:
        task = await get_task_queue().enqueue("strava_sync", payload)
        return {"task_id": task.id, "status": "queued", "athlete_id": current_user["id"]}
    from ..db.database import save_ride
    from ..ingestion.strava_client import (
        StravaRateLimitError,
        fetch_all_activities,
        get_valid_token,
        strava_to_ride,
        strava_to_ride_with_streams,
    )

    access_token = await get_valid_token(current_user["id"])
    if not access_token:
        raise HTTPException(status_code=401, detail="No Strava token. Connect first.")
    try:
        activities = await fetch_all_activities(access_token)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Strava API error: {exc}") from exc
    imported = []
    imported_ids: set[int] = set()
    from ..monitoring import record_gps_import

    streams_rate_limited = False
    for act in activities:
        if streams_rate_limited:
            ride_data = strava_to_ride(act)
        else:
            try:
                ride_data = await strava_to_ride_with_streams(act, access_token)
            except StravaRateLimitError:
                streams_rate_limited = True
                ride_data = strava_to_ride(act)
        if ride_data.get("skipped") or "error" in ride_data:
            continue
        ride_data["athlete_id"] = current_user["id"]
        ride_data["tenant_id"] = current_user["id"]
        db_ride = {k: v for k, v in ride_data.items() if k != "id"}
        try:
            ride_id = save_ride(db_ride)
        except Exception:
            logger.exception("Failed to save ride %s", ride_data.get("external_id"))
            continue
        if ride_id not in imported_ids:
            imported.append({"id": int(ride_id), **ride_data})
            imported_ids.add(int(ride_id))
            record_gps_import("strava_api", "strava")
    return {"imported": len(imported), "total_fetched": len(activities), "rides": imported}


@router.delete("/import/strava/disconnect")
async def strava_disconnect(current_user: dict = Depends(get_current_user)):
    from ..ingestion.strava_client import revoke_token

    revoke_token(current_user["id"])
    return {"status": "disconnected"}


@router.delete("/import/google-fit/disconnect")
async def google_fit_disconnect(current_user: dict = Depends(get_current_user)):
    logger.warning("Deprecated Google Fit disconnect route accessed; use Google Health instead")
    from ..ingestion.google_oauth_store import delete_google_token

    delete_google_token(int(current_user["id"]), "google_fit")
    return {"status": "disconnected"}


@router.delete("/import/google-health/disconnect")
async def google_health_disconnect(current_user: dict = Depends(get_current_user)):
    from ..ingestion.google_oauth_store import delete_google_token

    delete_google_token(int(current_user["id"]), "google_health")
    return {"status": "disconnected"}


# ------------------------------------------------------------------
# Garmin integration routes
# ------------------------------------------------------------------


@router.get("/import/garmin/auth")
async def garmin_auth(
    state: str = "",
    current_user: dict = Depends(get_current_user),
):
    from ..ingestion.garmin_client import get_authorization_url

    try:
        result = get_authorization_url(state=state)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    result["athlete_id"] = current_user["id"]
    return result


@router.post("/import/garmin/callback")
async def garmin_callback(
    payload: GarminCallbackRequest,
    current_user: dict = Depends(get_current_user),
):
    from ..ingestion.garmin_client import exchange_code_for_token, store_token

    code = payload.code
    redirect_uri = payload.redirect_uri
    try:
        token_data = await exchange_code_for_token(code, redirect_uri=redirect_uri or "")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Garmin token exchange failed: {exc}") from exc
    store_token(current_user["id"], token_data)
    return {"status": "connected", "athlete_id": current_user["id"]}


@router.post("/import/garmin/sync")
async def garmin_sync(
    background: bool = True,
    current_user: dict = Depends(get_current_user),
):
    from ..task_queue import get_task_queue

    payload = {"athlete_id": current_user["id"]}
    if background:
        task = await get_task_queue().enqueue("garmin_sync", payload)
        return {"task_id": task.id, "status": "queued", "athlete_id": current_user["id"]}
    from ..db.database import save_ride
    from ..ingestion.garmin_client import fetch_activities, garmin_to_ride, get_valid_token

    access_token = await get_valid_token(current_user["id"])
    if not access_token:
        raise HTTPException(status_code=401, detail="No Garmin token. Connect first.")
    try:
        activities = await fetch_activities(access_token)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Garmin API error: {exc}") from exc
    imported = []
    imported_ids: set[int] = set()
    from ..monitoring import record_gps_import

    for act in activities:
        ride_data = garmin_to_ride(act)
        if ride_data.get("skipped") or "error" in ride_data:
            continue
        ride_data["athlete_id"] = current_user["id"]
        ride_data["tenant_id"] = current_user["id"]
        db_ride = {k: v for k, v in ride_data.items() if k != "id"}
        try:
            ride_id = save_ride(db_ride)
        except Exception:
            logger.exception("Failed to save ride %s", ride_data.get("external_id"))
            continue
        if ride_id not in imported_ids:
            imported.append({"id": int(ride_id), **ride_data})
            imported_ids.add(int(ride_id))
            record_gps_import("garmin_api", "garmin")
    return {"imported": len(imported), "total_fetched": len(activities), "rides": imported}


@router.delete("/import/garmin/disconnect")
async def garmin_disconnect(current_user: dict = Depends(get_current_user)):
    from ..ingestion.garmin_client import revoke_token

    revoke_token(current_user["id"])
    return {"status": "disconnected"}


@router.get("/import/providers")
async def list_import_providers():
    return {
        "google_fit": bool(_s.google_fit_client_id and _s.google_fit_client_secret),
        "google_health": bool(_s.google_health_client_id and _s.google_health_client_secret),
        "wahoo": bool(_s.wahoo_client_id and _s.wahoo_client_secret),
        "strava": bool(_s.strava_client_id and _s.strava_client_secret),
    }


# ------------------------------------------------------------------
# Wahoo integration routes
# ------------------------------------------------------------------


@router.get("/import/wahoo/auth")
async def wahoo_auth(
    state: str = "",
    current_user: dict = Depends(get_current_user),
):
    from ..ingestion.wahoo_client import get_authorization_url

    try:
        result = get_authorization_url(state=state)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    result["athlete_id"] = current_user["id"]
    return result


@router.post("/import/wahoo/callback")
async def wahoo_callback(
    payload: WahooCallbackRequest,
    current_user: dict = Depends(get_current_user),
):
    from ..ingestion.wahoo_client import exchange_code_for_token, store_token

    code = payload.code
    code_verifier = payload.code_verifier
    try:
        token_data = exchange_code_for_token(code, code_verifier)
    except requests.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Wahoo token exchange failed: {exc}") from exc
    store_token(current_user["id"], token_data, code_verifier=code_verifier)
    return {
        "status": "connected",
        "athlete_id": current_user["id"],
        "athlete_name": "",
    }


@router.post("/import/wahoo/sync")
async def wahoo_sync(
    background: bool = True,
    current_user: dict = Depends(get_current_user),
):
    from ..task_queue import get_task_queue

    payload = {"athlete_id": current_user["id"]}
    if background:
        task = await get_task_queue().enqueue("wahoo_sync", payload)
        return {"task_id": task.id, "status": "queued", "athlete_id": current_user["id"]}
    from ..db.database import save_ride
    from ..ingestion.wahoo_client import fetch_workouts, get_valid_token, wahoo_to_ride

    access_token = get_valid_token(current_user["id"])
    if not access_token:
        raise HTTPException(status_code=401, detail="No Wahoo token. Connect first.")
    workouts = fetch_workouts(access_token)
    imported = []
    imported_ids: set[int] = set()
    from ..monitoring import record_gps_import

    for workout in workouts:
        ride_data = wahoo_to_ride(workout)
        if ride_data.get("skipped") or "error" in ride_data:
            continue
        ride_data["athlete_id"] = current_user["id"]
        ride_data["tenant_id"] = current_user["id"]
        db_ride = {k: v for k, v in ride_data.items() if k != "id"}
        ride_id = save_ride(db_ride)
        if ride_id not in imported_ids:
            imported.append({"id": int(ride_id), **ride_data})
            imported_ids.add(int(ride_id))
            record_gps_import("wahoo_api", "wahoo")
    return {"imported": len(imported), "total_fetched": len(workouts), "rides": imported}


@router.delete("/import/wahoo/disconnect")
async def wahoo_disconnect(current_user: dict = Depends(get_current_user)):
    from ..ingestion.wahoo_client import revoke_token

    revoke_token(current_user["id"])
    return {"status": "disconnected"}


@router.get("/dashboard")
@limiter.limit("20/minute")
async def get_dashboard(request: Request, current_user: dict = Depends(get_current_user)):
    """Get consolidated dashboard analytics for authenticated athlete."""
    from ..analytics.dashboard import create_score_dashboard
    from ..analytics.training_load import get_7day_fitness_summary
    from ..db.database import get_athlete, get_rides_by_athlete

    athlete_id = _ensure_int_user_id(current_user)
    cache_key = f"dashboard:{athlete_id}"
    cached_result = await _cached(cache_key, ttl=120)
    if cached_result:
        return cached_result

    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id)]
    athlete = get_athlete(athlete_id)
    athlete_dict = _public_athlete(athlete) if athlete else None

    summary = calculate_summary(rides)
    scores = create_score_dashboard(rides, AthleteProfile(**_athlete_profile_data(athlete_dict or {})))
    fitness = get_7day_fitness_summary(rides)
    trends = {
        "weekly_progress": [r.distance_km for r in rides[-7:]] if rides else [],
        "monthly_stats": None,
    }
    result = {
        "athlete": athlete_dict,
        "summary": summary,
        "scores": scores,
        "fitness": fitness,
        "trends": trends,
        "rides_count": len(rides),
    }
    await _cache_set(cache_key, result, ttl=120)
    return result


@admin_router.get("/test-sentry")
async def test_sentry(current_user: dict = Depends(get_admin_user)):
    """Test endpoint to verify Sentry integration - sends a test exception."""
    import sentry_sdk

    sentry_sdk.capture_exception(Exception("Test Sentry integration - bikemaster"))
    return {"status": "test_event_sent", "message": "Check Sentry dashboard for error event"}


@admin_router.get("/audit-logs")
async def get_audit_logs(limit: int = Query(100, ge=1, le=500), current_user: dict = Depends(get_admin_user)):
    """Return recent admin audit log entries."""
    log_action(current_user["id"], "view_audit_logs", "audit")
    return {"logs": read_audit_logs(limit=limit)}

