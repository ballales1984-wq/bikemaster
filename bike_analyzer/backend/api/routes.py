"""API routes."""

from __future__ import annotations

import base64
import contextlib
import json
import secrets
import time
from collections.abc import AsyncGenerator
from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

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
from sqlalchemy import insert

from ..analytics.analytics import calculate_summary
from ..analytics.badges import calculate_badges, get_heatmap_points
from ..analytics.calories import calories_per_km, estimate_calories
from ..analytics.fatigue import (
    calculate_fatigue_score,
)
from ..analytics.granfondo_planner import generate_granfondo_plan
from ..config import DB_PATH, SECRET_KEY
from ..maps.map_renderer import create_route_map
from ..maps.osm_maps import get_local_results, search_nearby, search_places
from ..models.models import AthleteProfile, GPSPoint, Ride
from ..rate_limiter import limiter
from ..redis_client import cache_delete as _cache_delete
from ..redis_client import cache_set as _cache_set
from ..redis_client import cached as _cached
from ..security import get_admin_user, get_current_user
from ..utils.logger import get_logger
from .schemas import (
    AthleteCreate,
    AthleteUpdate,
    CalendarEventCreate,
    CalendarEventUpdate,
    GranfondoPlanRequest,
    MetricCreate,
    RefreshTokenRequest,
    RideAnalysisRequest,
    RideCreate,
)

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


def _forwarded_value(header_value: str | None) -> str:
    if not header_value:
        return ""
    return header_value.split(",", 1)[0].strip()


def _build_redirect_uri(request: Request, path: str) -> str:
    proto = _forwarded_value(request.headers.get("x-forwarded-proto")) or request.url.scheme
    host = (
        _forwarded_value(request.headers.get("x-forwarded-host")) or request.headers.get("host") or request.url.netloc
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
    query_suffix = f"?{urlencode(params)}" if params else ""
    fragment_suffix = f"#{urlencode(fragment_params)}" if fragment_params else ""
    return f"{origin}/{query_suffix}{fragment_suffix}"


def _validate_redirect_uri(redirect_uri: str) -> None:
    parsed = urlparse(redirect_uri)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")


def _encode_oauth_state(**values: str) -> str:
    payload = json.dumps(values, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_oauth_state(state: str) -> dict:
    if not state:
        return {}
    try:
        padded = state + "=" * (-len(state) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        data = json.loads(decoded)
        return data if isinstance(data, dict) else {}
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return {}


def _redirect_uri_from_state(state: str) -> str | None:
    redirect_uri = _decode_oauth_state(state).get("redirect_uri")
    return redirect_uri if isinstance(redirect_uri, str) else None


def _validate_oauth_state(state: str, expected_redirect_uri: str) -> None:
    decoded = _decode_oauth_state(state)
    if not decoded:
        raise HTTPException(status_code=400, detail="Invalid or missing state parameter")
    state_redirect = decoded.get("redirect_uri")
    if not isinstance(state_redirect, str) or not state_redirect:
        raise HTTPException(status_code=400, detail="State missing redirect_uri")
    if state_redirect != expected_redirect_uri:
        raise HTTPException(status_code=400, detail="State redirect_uri mismatch")


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


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


def _make_streaming_response(generator: AsyncGenerator[str, None], event_type: str = "chunk") -> StreamingResponse:
    async def stream_gen() -> AsyncGenerator[str, None]:
        try:
            async for chunk in generator:
                yield _sse(event_type, chunk.replace("\n", " "))
        except Exception as e:
            yield _sse("error", str(e)[:200])
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


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "bikemaster"}


@router.post("/alerts/webhook")
async def alerts_webhook(request: Request):
    """Receive alerts from Prometheus Alertmanager."""
    body = await request.json()
    logger.info("Alert received: %s", body.get("receiver", "unknown"))
    return {"status": "ok"}


@router.get("/sentry-debug")
async def sentry_debug():
    """Debug endpoint to verify Sentry error tracking."""
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
async def google_maps_key(current_user: dict = Depends(get_current_user)):
    from ..config import GOOGLE_MAPS_API_KEY

    return {"google_maps_api_key": GOOGLE_MAPS_API_KEY or ""}


@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    from ..config import DATABASE_URL
    from ..security import (
        create_access_token,
        create_refresh_token,
        save_refresh_token,
        verify_password,
    )

    if DATABASE_URL:
        from sqlalchemy import select

        from ..db.async_db import get_session_factory
        from ..db.models import UserModel

        session_factory = get_session_factory()
        async with session_factory() as session:
            stmt = select(UserModel).where(UserModel.username == form_data.username)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user or not verify_password(form_data.password, user.password_hash or ""):
                raise HTTPException(
                    status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"}
                )

            access_token = create_access_token(subject=str(user.id), is_admin=user.is_admin, tenant_id=user.id)
            refresh_token = create_refresh_token(user.id)
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
    refresh_token = create_refresh_token(athlete_id)
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
                await revoke_token(jti)
            athlete_id = payload_data.get("sub")
            if athlete_id:
                await revoke_refresh_token(int(athlete_id))
    except Exception as exc:
        logger.warning("Logout: failed to revoke token: %s", exc)
    return {"msg": "Logged out successfully"}


@router.post("/auth/refresh")
@limiter.limit("10/minute")
async def refresh_token(request: Request, payload: RefreshTokenRequest):
    from ..security import _try_decode, create_access_token, is_token_revoked

    refresh_token = payload.refresh_token
    jwt_payload = _try_decode(refresh_token, SECRET_KEY)
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
    return {
        "access_token": create_access_token(subject=str(user_id), is_admin=False, tenant_id=int(user_id)),
        "token_type": "bearer",
    }


@router.post("/auth/register")
@limiter.limit("3/minute")
async def register(
    request: Request,
    username: str = Body(..., min_length=3),
    password: str = Body(..., min_length=6),
    email: str = Body(None),
):
    from ..config import DATABASE_URL
    from ..db.database import get_athlete_by_email, get_athlete_by_name, save_athlete
    from ..security import hash_password

    if len(username) < 3 or len(password) < 6:
        raise HTTPException(status_code=400, detail="Username must be >= 3 chars, password >= 6")

    if DATABASE_URL:
        from sqlalchemy import select

        from ..db.async_db import get_session_factory
        from ..db.models import AthleteModel, UserModel

        session_factory = get_session_factory()
        async with session_factory() as session:
            stmt = select(UserModel).where((UserModel.username == username) | (UserModel.email == email))
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
        and athlete.get("experience_level", "").strip() != ""
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
    profile_data: dict = Body(...),
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
    update_data = {k: v for k, v in profile_data.items() if k in allowed_fields}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    _update_athlete(current_user["id"], update_data)
    athlete = _get_athlete(current_user["id"], tenant_id)
    return _public_athlete(athlete)


@router.post("/auth/change-password")
async def change_password(
    current_password: str = Body(..., embed=True),
    new_password: str = Body(..., min_length=6, embed=True),
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
    from ..config import GOOGLE_CLIENT_ID

    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")
    redirect_uri = redirect_uri or _build_redirect_uri(request, "/api/v1/auth/google/callback")
    _validate_redirect_uri(redirect_uri)
    auth_url = get_google_oauth_url(GOOGLE_CLIENT_ID, redirect_uri=redirect_uri, state=state)
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
    from ..config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
    from ..db.database import get_athlete, get_athlete_by_email, save_athlete

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    redirect_uri = (
        redirect_uri or _redirect_uri_from_state(state) or _build_redirect_uri(request, "/api/v1/auth/google/callback")
    )
    _validate_redirect_uri(redirect_uri)
    if state:
        _validate_oauth_state(state, redirect_uri)

    if error:
        message = error_description or error
        return RedirectResponse(url=_build_frontend_redirect_url(request, redirect_uri, oauth_error=message))

    if not code:
        return RedirectResponse(url=_build_frontend_redirect_url(request, redirect_uri, oauth_error="missing_code"))

    cache_key = f"oauth:code:{code}"
    cached_result = await _cached(cache_key)
    if cached_result:
        return RedirectResponse(url=cached_result["redirect_url"])

    try:
        token_data = exchange_google_code(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, code, redirect_uri)
    except requests.exceptions.HTTPError as exc:
        response = getattr(exc, "response", None)
        if response is not None and response.status_code == 400:
            return RedirectResponse(url=_build_frontend_redirect_url(request, redirect_uri, oauth_error="oauth_error"))
        error_body = response.text if response is not None else str(exc)
        error_detail = f"token_exchange_failed:{error_body[:200]}"
        return RedirectResponse(url=_build_frontend_redirect_url(request, redirect_uri, oauth_error=error_detail))
    access_token = token_data.get("access_token")
    if not access_token:
        return RedirectResponse(url=_build_frontend_redirect_url(request, redirect_uri, oauth_error="no_access_token"))

    try:
        user_info = get_google_user_info(access_token)
    except requests.exceptions.HTTPError as exc:
        response = getattr(exc, "response", None)
        error_body = response.text if response is not None else str(exc)
        return RedirectResponse(
            url=_build_frontend_redirect_url(request, redirect_uri, oauth_error=f"userinfo_failed:{error_body[:200]}")
        )
    google_sub = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name")

    if not google_sub:
        return RedirectResponse(
            url=_build_frontend_redirect_url(request, redirect_uri, oauth_error="invalid_user_info")
        )

    existing = get_athlete_by_email(email) if email else None
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
                existing = get_athlete_by_email(email) if email else None
            if not existing:
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
                existing = get_athlete(athlete_id)
        finally:
            if r is not None:
                await r.delete(lock_key)

    jwt_token = create_google_session(user_info, athlete_id=existing["id"])["access_token"]
    parsed_redirect = urlparse(redirect_uri or "")
    frontend_origin = f"{parsed_redirect.scheme}://{parsed_redirect.netloc}/" if parsed_redirect.scheme else None
    if not frontend_origin or not parsed_redirect.path.endswith("/api/v1/auth/google/callback"):
        frontend_origin = _build_redirect_uri(request, "")
    if frontend_origin and "localhost:8000" in frontend_origin:
        frontend_origin = "http://localhost:5173/"
    redirect_url = (
        f"{frontend_origin}#{urlencode({'token': jwt_token, 'email': email or '', 'user_id': str(existing['id'])})}"
    )
    await _cache_set(f"oauth:code:{code}", {"redirect_url": redirect_url}, ttl=300)
    return RedirectResponse(url=redirect_url)


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
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    all_rides = get_rides_by_athlete(current_user["id"], tenant_id)
    start = (page - 1) * page_size
    rides = all_rides[start : start + page_size]
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
async def generate_ride_map(ride_id: int, current_user: dict = Depends(get_current_user)):
    from pathlib import Path

    from ..db.database import get_ride as _get_ride
    from ..maps.map_renderer import create_route_map
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
    try:
        create_route_map(points, output_path=str(resolved))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Map generation failed: {exc}") from exc
    return {"map_url": f"/static/{resolved.name}"}


@router.post("/rides/analyze")
async def analyze_rides(request: Request, payload: RideAnalysisRequest):
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


@router.post("/import/gpx")
async def import_gpx(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    from ..db.database import save_ride
    from ..ingestion.gps_parser import parse_gpx_file, points_to_ride

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")
    points_data = parse_gpx_file(content.decode())
    ride_data = points_to_ride(points_data, name=file.filename)
    if "error" not in ride_data:
        ride_data["athlete_id"] = _user_id(current_user)
        ride_id = save_ride({k: v for k, v in ride_data.items() if k != "id"})
        ride_data["id"] = int(ride_id)
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
    ride_data = points_to_ride(points_data, name=file.filename)
    if "error" not in ride_data:
        ride_data["athlete_id"] = _user_id(current_user)
        ride_data["tenant_id"] = current_user["id"]
        ride_id = save_ride({k: v for k, v in ride_data.items() if k != "id"})
        ride_data["id"] = int(ride_id)
        from ..monitoring import record_gps_import

        record_gps_import("fit", "upload")
    return ride_data


@router.get("/health/detailed")
async def health_detailed(request: Request):
    from ..db.database import get_all_athletes, get_all_rides

    rides = get_all_rides()
    athletes = get_all_athletes()
    db_size = Path(DB_PATH).stat().st_size if Path(DB_PATH).exists() else 0
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

    imported = []
    failed = []
    total_size = 0
    for file in files:
        content = await file.read()
        total_size += len(content)
        if total_size > MAX_UPLOAD_SIZE * 2:
            raise HTTPException(status_code=413, detail="Total upload size exceeds 100MB limit.")
        try:
            ext = file.filename.lower().split(".")[-1] if file.filename else ""
            if ext == "gpx":
                points = parse_gpx_file(content.decode())
            elif ext in ("fit", "fitf"):
                with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as tmp:
                    tmp.write(content)
                    temp_path = tmp.name
                try:
                    points = parse_fit_file(temp_path)
                finally:
                    import os

                    os.unlink(temp_path)
            else:
                points = []
            ride_data = points_to_ride(points, name=file.filename)
            if "error" not in ride_data:
                ride_data["athlete_id"] = _user_id(current_user)
                ride_data["tenant_id"] = current_user["id"]
                ride_id = save_ride({k: v for k, v in ride_data.items() if k != "id"})
                ride_data["id"] = int(ride_id)
                imported.append(ride_data)
                from ..monitoring import record_gps_import

                record_gps_import(ext or "unknown", "upload")
        except Exception as e:
            failed.append({"filename": file.filename, "error": str(e)})
    return {
        "imported": imported,
        "failed": failed,
        "count": len(imported),
        "total_files": len(files),
    }


@router.get("/rides/export/json")
async def export_json(current_user: dict = Depends(get_current_user)):
    from ..analytics.analytics import export_rides_json
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(current_user["id"], tenant_id)]
    path = export_rides_json(rides, "rides_export.json")
    from fastapi.responses import FileResponse

    return FileResponse(path, media_type="application/json", filename="rides.json")


@router.get("/rides/export/csv")
async def export_csv(current_user: dict = Depends(get_current_user)):
    from ..analytics.analytics import export_rides_csv
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(current_user["id"], tenant_id)]
    path = export_rides_csv(rides, "rides_export.csv")
    from fastapi.responses import FileResponse

    return FileResponse(path, media_type="text/csv", filename="rides.csv")


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
    create_speed_chart(segments, path)
    from fastapi.responses import FileResponse

    return FileResponse(path, media_type="image/png", filename="speed.png")


@router.get("/charts/duration")
async def duration_chart(current_user: dict = Depends(get_current_user)):
    from ..analytics.analytics import create_duration_chart
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(current_user["id"], tenant_id)]
    path = "duration_chart.png"
    create_duration_chart(rides, path)
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
    create_distance_chart(segments, path)
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
    create_elevation_chart(segments, path)
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
        return _public_athlete(_get_athlete(target_athlete_id, tenant_id))

    athlete_id = save_athlete(data, athlete_id=target_athlete_id)
    return _public_athlete(_get_athlete(athlete_id, tenant_id))


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
        and athlete.get("experience_level", "").strip() != ""
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
    return _public_athlete(_get(athlete_id))


@router.get("/import/google-fit/auth")
async def google_fit_auth(
    request: Request,
    client_id: str | None = Query(None),
    redirect_uri: str | None = Query(None),
    state: str = Query(""),
):
    from ..config import GOOGLE_FIT_CLIENT_ID
    from ..ingestion.google_fit import get_authorization_url

    google_client_id = client_id or GOOGLE_FIT_CLIENT_ID
    if not google_client_id:
        raise HTTPException(status_code=500, detail="Google Fit OAuth not configured")
    redirect_uri = redirect_uri or _build_redirect_uri(request, "/api/v1/import/google-fit/callback")
    _validate_redirect_uri(redirect_uri)
    auth_url = get_authorization_url(google_client_id, redirect_uri=redirect_uri, state=state)
    return {"auth_url": auth_url}


@router.get("/import/google-health/auth")
@limiter.limit("10/minute")
async def google_health_auth(
    request: Request,
    redirect_uri: str | None = Query(None),
    state: str = Query(""),
):
    from ..config import GOOGLE_HEALTH_CLIENT_ID
    from ..ingestion.google_health import _compute_code_challenge, _generate_code_verifier, get_authorization_url

    if not GOOGLE_HEALTH_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google Health OAuth not configured")
    redirect_uri = redirect_uri or _build_redirect_uri(request, "/api/v1/import/google-health/callback")
    _validate_redirect_uri(redirect_uri)
    code_verifier = _generate_code_verifier()
    code_challenge = _compute_code_challenge(code_verifier)
    pkce_id = secrets.token_urlsafe(8)
    pkce_key = f"oauth:pkce:google-health:{pkce_id}"
    await _cache_set(pkce_key, {"code_verifier": code_verifier, "redirect_uri": redirect_uri}, ttl=600)
    state_data = _decode_oauth_state(state)
    state_data["pkce_id"] = pkce_id
    state = _encode_oauth_state(**state_data)
    auth_url = get_authorization_url(
        GOOGLE_HEALTH_CLIENT_ID,
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
    from ..config import GOOGLE_HEALTH_CLIENT_ID, GOOGLE_HEALTH_CLIENT_SECRET
    from ..ingestion.google_health import exchange_code_for_token

    if not GOOGLE_HEALTH_CLIENT_ID or not GOOGLE_HEALTH_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google Health OAuth not configured")
    redirect_uri = (
        redirect_uri
        or _redirect_uri_from_state(state)
        or _build_redirect_uri(request, "/api/v1/import/google-health/callback")
    )
    _validate_redirect_uri(redirect_uri)
    if state:
        _validate_oauth_state(state, redirect_uri)

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
    if state:
        state_data = _decode_oauth_state(state)
        pkce_key = f"oauth:pkce:google-health:{state_data.get('pkce_id', '')}"
        pkce_data = await _cached(pkce_key)
        if pkce_data:
            code_verifier = pkce_data.get("code_verifier", "")
    try:
        token_data = exchange_code_for_token(
            GOOGLE_HEALTH_CLIENT_ID,
            GOOGLE_HEALTH_CLIENT_SECRET,
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
    _validate_redirect_uri(redirect_uri)

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

    try:
        token_data = exchange_code_for_token(GOOGLE_HEALTH_CLIENT_ID, GOOGLE_HEALTH_CLIENT_SECRET, code, redirect_uri)
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
async def import_google_health(payload: dict, current_user: dict = Depends(get_current_user)):
    from ..db.database import save_ride
    from ..ingestion.google_health import google_health_to_rides
    from ..ingestion.google_oauth_store import get_valid_google_token, store_google_token

    athlete_id = int(current_user["id"])

    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    if access_token and refresh_token and isinstance(access_token, str) and isinstance(refresh_token, str):
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
    elif not access_token or not isinstance(access_token, str) or len(access_token) > 2048:
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
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    from ..config import GOOGLE_FIT_CLIENT_ID, GOOGLE_FIT_CLIENT_SECRET
    from ..ingestion.google_fit import exchange_code_for_token

    client_id = payload.get("client_id") or GOOGLE_FIT_CLIENT_ID
    client_secret = payload.get("client_secret") or GOOGLE_FIT_CLIENT_SECRET
    if not client_id or not isinstance(client_id, str) or len(client_id) > 256:
        raise HTTPException(status_code=400, detail="Invalid client_id")

    redirect_uri = payload.get("redirect_uri") or _build_redirect_uri(request, "/api/v1/import/google-fit/callback")
    _validate_redirect_uri(redirect_uri)

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
    from ..config import GOOGLE_FIT_CLIENT_ID, GOOGLE_FIT_CLIENT_SECRET
    from ..ingestion.google_fit import exchange_code_for_token

    if not GOOGLE_FIT_CLIENT_ID or not GOOGLE_FIT_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google Fit OAuth not configured")
    redirect_uri = (
        redirect_uri
        or _redirect_uri_from_state(state)
        or _build_redirect_uri(request, "/api/v1/import/google-fit/callback")
    )
    _validate_redirect_uri(redirect_uri)

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
        token_data = exchange_code_for_token(GOOGLE_FIT_CLIENT_ID, GOOGLE_FIT_CLIENT_SECRET, code, redirect_uri)
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
    html_content = f"<script>window.opener.postMessage({json.dumps(payload)}, '*'); window.close();</script>"
    await _cache_set(cache_key, {"html": html_content}, ttl=300)
    return HTMLResponse(content=html_content)


@router.post("/import/google-fit")
async def import_google_fit(payload: dict, current_user: dict = Depends(get_current_user)):
    from ..db.database import save_ride
    from ..ingestion.google_fit import fetch_cycling_activities, google_fit_to_ride
    from ..ingestion.google_oauth_store import get_valid_google_token, store_google_token

    athlete_id = int(current_user["id"])

    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    if access_token and refresh_token and isinstance(access_token, str) and isinstance(refresh_token, str):
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
    elif not access_token or not isinstance(access_token, str) or len(access_token) > 2048:
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
async def benchmark_compare(ride_data: dict, current_user: dict = Depends(get_current_user)):
    from ..analytics.benchmark import compare_athlete_to_benchmark
    from ..models.models import Ride

    ride = Ride(**ride_data)
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
    return FileResponse(path, media_type="application/octet-stream", filename="backup.db")


@admin_router.post("/backup/scheduled")
async def create_scheduled_backup(current_user: dict = Depends(get_admin_user)):
    from ..db.database import scheduled_backup

    result = scheduled_backup(max_backups=10)
    return result


@admin_router.post("/indexes")
async def create_db_indexes(current_user: dict = Depends(get_admin_user)):
    from ..db.database import create_indices

    create_indices()
    return {"status": "indexes_created"}


@admin_router.get("/stats")
async def get_system_stats(current_user: dict = Depends(get_admin_user)):
    from ..db.database import DB_PATH, get_all_rides

    rides = get_all_rides()
    total_km = sum(r.get("distance_km", 0) for r in rides)
    total_duration = sum(r.get("duration_minutes", 0) for r in rides)
    db_size = Path(DB_PATH).stat().st_size if Path(DB_PATH).exists() else 0
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
    db_size = Path(DB_PATH).stat().st_size if Path(DB_PATH).exists() else 0
    level_counts = {"Beginner": 0, "Amateur": 0, "Intermediate": 0, "Advanced": 0, "Elite": 0}
    for a in athletes:
        level = a.get("experience_level", "Beginner")
        if level in level_counts:
            level_counts[level] += 1
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
async def update_ride(ride_id: int, ride: dict = Body(...), current_user: dict = Depends(get_current_user)):
    from ..db.database import get_ride as _get_ride
    from ..db.database import update_ride as _update_ride

    existing = _get_ride(ride_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(existing, current_user)
    protected = {k: v for k, v in existing.items() if k in ("id", "athlete_id", "created_at")}
    merged = {**existing, **{k: v for k, v in ride.items() if k not in protected}}
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
    from .schemas import CoachChatRequest

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
        save_chat_message,
    )
    from ..models.models import AthleteProfile

    tenant_id = current_user.get("tenant_id", athlete_id)
    _ensure_athlete_access(athlete_id, current_user)
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

        results = osm_search(points, query=query)
    else:
        results = get_local_results(points, query=query)
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
    result = search_places(query, lat=lat, lon=lon, limit=limit)
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
    from ..config import SERPAPI_API_KEY

    if not SERPAPI_API_KEY:
        raise HTTPException(status_code=500, detail="SERPAPI_API_KEY not configured")
    data = search_nearby(points, query=query)
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
    from ..config import WEATHER_API_KEY
    from ..weather.weather_service import (
        get_forecast_for_date,
        get_weather_for_coordinates,
        get_weather_score,
    )

    if not WEATHER_API_KEY:
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

    from ..config import WEATHER_API_KEY
    from ..weather.weather_service import get_forecast_for_date, get_weather_score

    if not WEATHER_API_KEY:
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
    return {
        "athlete_id": athlete_id,
        "start_date": start_date,
        "weeks": weeks,
        "plan": plan,
        "total_workouts": len(plan),
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
    from ..config import INCIDENT_DAYS, INCIDENT_RADIUS_KM
    from ..traffic.incident_fetcher import fetch_incidents, get_incident_stats

    radius = radius_km if radius_km > 0 else INCIDENT_RADIUS_KM
    lookback = days if days > 0 else INCIDENT_DAYS
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
    from ..config import INCIDENT_DAYS, INCIDENT_RADIUS_KM
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
    incidents = fetch_incidents(center_lat, center_lon, radius_km=INCIDENT_RADIUS_KM, days=INCIDENT_DAYS)
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


@router.get("/import/strava/auth")
async def strava_auth(
    state: str = "",
    current_user: dict = Depends(get_current_user),
):
    from ..ingestion.strava_client import get_authorization_url

    try:
        result = get_authorization_url(state=state)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    result["athlete_id"] = current_user["id"]
    return result


@router.post("/import/strava/callback")
async def strava_callback(
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    from ..ingestion.strava_client import exchange_code_for_token, store_token

    code = payload.get("code", "")
    code_verifier = payload.get("code_verifier", "")
    if not code or not code_verifier:
        raise HTTPException(status_code=400, detail="code and code_verifier required")
    try:
        token_data = exchange_code_for_token(code, code_verifier)
    except requests.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Strava token exchange failed: {exc}") from exc
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
    from ..ingestion.strava_client import fetch_all_activities, get_valid_token, strava_to_ride

    access_token = get_valid_token(current_user["id"])
    if not access_token:
        raise HTTPException(status_code=401, detail="No Strava token. Connect first.")
    activities = fetch_all_activities(access_token)
    imported = []
    imported_ids: set[int] = set()
    from ..monitoring import record_gps_import

    for act in activities:
        ride_data = strava_to_ride(act)
        if ride_data.get("skipped") or "error" in ride_data:
            continue
        ride_data["athlete_id"] = current_user["id"]
        ride_data["tenant_id"] = current_user["id"]
        db_ride = {k: v for k, v in ride_data.items() if k != "id"}
        ride_id = save_ride(db_ride)
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
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    from ..ingestion.garmin_client import exchange_code_for_token, store_token

    code = payload.get("code", "")
    redirect_uri = payload.get("redirect_uri")
    if not code:
        raise HTTPException(status_code=400, detail="code required")
    try:
        token_data = exchange_code_for_token(code, redirect_uri=redirect_uri or "")
    except requests.HTTPError as exc:
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

    access_token = get_valid_token(current_user["id"])
    if not access_token:
        raise HTTPException(status_code=401, detail="No Garmin token. Connect first.")
    activities = fetch_activities(access_token)
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
        ride_id = save_ride(db_ride)
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
