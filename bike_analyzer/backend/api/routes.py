"""API routes for BikeMaster backend.

Provides REST endpoints for authentication, ride management, GPS import,
OAuth integrations (Google, Strava, Garmin, Wahoo), analytics, coaching,
training plans, maps, notifications, and admin operations.
"""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import html as html_module
import json
import os
import secrets
import sqlite3
import tempfile
import time
from collections.abc import AsyncGenerator
from dataclasses import fields
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
import numpy as np
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
from starlette.concurrency import run_in_threadpool
from jose import JWTError, jwt
from sqlalchemy import insert, text
from starlette.background import BackgroundTask

from ..analytics.analytics import calculate_summary
from ..analytics.badges import calculate_badges, get_heatmap_points
from ..analytics.calories import calories_per_km, estimate_calories
from ..analytics.fatigue import (
    calculate_fatigue_score,
    estimate_recovery_hours,
)
from ..analytics.granfondo_planner import generate_granfondo_plan
from ..analytics.terrain_enrichment import TerrainEnricher
from ..audit_log import log_action, read_audit_logs
from ..db.database import get_user_by_id, save_user
from ..maps.map_renderer import create_route_map
from ..maps.osm_maps import get_local_results, search_nearby, search_places
from ..models.models import AthleteProfile, GPSPoint, Ride
from ..processing.processing import process_route
from ..rate_limiter import limiter
from ..redis_client import cache_delete as _cache_delete
from ..redis_client import cache_set as _cache_set
from ..redis_client import cached as _cached
from ..redis_client import check_rate_limit
from ..security import ALGORITHM, JWT_AUDIENCE, JWT_ISSUER, get_admin_user, get_current_user
from ..settings import get_settings
from ..utils.logger import get_logger
from .schemas import (
    ActivityClassification,
    ActivitySummaryResponse,
    AthleteCreate,
    AthleteUpdate,
    BeckAssessmentCreate,
    BeckAssessmentResponse,
    BeckHistoryResponse,
    BenchmarkCompareRequest,
    BleDeviceOut,
    BleDeviceRegister,
    BleDeviceSync,
    BleDeviceUpdate,
    CalendarEventCreate,
    CalendarEventUpdate,
    CoachChatRequest,
    FoodLogCreate,
    FoodLogUpdate,
    GarminCallbackRequest,
    GoogleFitImportPayload,
    GoogleFitTokenRequest,
    GoogleHealthImportPayload,
    GranfondoPlanRequest,
    GranfondoSaveRequest,
    HealthConnectPayload,
    Hr24hSummary,
    HrMonitoringSettings,
    HrSamplesBulk,
    ItineraryCreate,
    MetabolicCalibrationRequest,
    MetabolicCalibrationResponse,
    MetabolicProfileCreate,
    MetabolicProfileResponse,
    MetabolicReferenceImportRequest,
    MetabolicWeightsResponse,
    MetricCreate,
    MeasurementCreate,
    NotificationContextIn,
    NotificationListOut,
    NotificationOut,
    NotificationPreferences,
    NotificationScoreOut,
    NutritionFoodItemCreate,
    NutritionFoodItemUpdate,
    POICreate,
    POIResponse,
    ProfileUpdate,
    RefreshTokenRequest,
    RideAnalysisRequest,
    RideCreate,
    RideUpdate,
    SensorSamplesBulk,
    StageCreate,
    StravaCallbackRequest,
    UserCreate,
    UserOAuthCredentials,
    UserUpdate,
    WahooCallbackRequest,
)
from .utils import _trusted_forwarded_value

_s = get_settings()

_PLACE_CACHE: dict[str, tuple[Any, float]] = {}
_PLACE_CACHE_TTL_S = 600

logger = get_logger(__name__)

def _place_cache_get(key: str) -> Any | None:
    """Return a cached POI result if still fresh, otherwise evict it."""
    entry = _PLACE_CACHE.get(key)
    if entry is None:
        return None
    value, ts = entry
    if time.time() - ts > _PLACE_CACHE_TTL_S:
        del _PLACE_CACHE[key]
        return None
    return value


def _place_cache_set(key: str, value: Any) -> None:
    """Store a POI result in the in-memory cache with the current timestamp."""
    _PLACE_CACHE[key] = (value, time.time())


_OAUTH_STATE_TTL_S = 600
_OAUTH_STATE_PREFIX = "oauth:state:"


def _generate_oauth_state() -> str:
    return secrets.token_urlsafe(32)


async def _store_oauth_state(state: str, user_id: int, provider: str, extra: dict | None = None) -> bool:
    data = {"user_id": user_id, "provider": provider, "created_at": time.time()}
    if extra:
        data.update(extra)
    return await _cache_set(_OAUTH_STATE_PREFIX + state, data, ttl=_OAUTH_STATE_TTL_S)


async def _validate_oauth_state(state: str, provider: str, user_id: int) -> bool:
    if not state:
        return False
    cached = await _cached(_OAUTH_STATE_PREFIX + state)
    if not cached:
        return False
    if not isinstance(cached, dict):
        return False
    if cached.get("provider") != provider:
        return False
    if cached.get("user_id") != user_id:
        return False
    return True


async def _consume_oauth_state(state: str, provider: str, user_id: int) -> bool:
    if not await _validate_oauth_state(state, provider, user_id):
        return False
    await cache_delete(_OAUTH_STATE_PREFIX + state)
    return True


def _place_cache_set(key: str, value: Any) -> None:
    """Store a POI result in the in-memory cache with the current timestamp."""
    _PLACE_CACHE[key] = (value, time.time())


router = APIRouter()
admin_router = APIRouter()

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


def _build_redirect_uri(request: Request, path: str) -> str:
    """Build an absolute URI honoring X-Forwarded-* headers when behind a proxy."""
    proto = _trusted_forwarded_value(request, "x-forwarded-proto") or request.url.scheme
    host = (
        _trusted_forwarded_value(request, "x-forwarded-host") or request.headers.get("host") or request.url.netloc
    )
    host_lower = host.lower()
    if (
        host_lower.endswith(".ngrok-free.dev")
        or host_lower.endswith(".vercel.app")
        or host_lower.endswith(".onrender.com")
    ):
        proto = "https"
    return f"{proto}://{host}{path}"


def _build_frontend_redirect_url(
    request: Request,
    redirect_uri: str | None,
    fragment_keys: set[str] | None = None,
    frontend_origin: str | None = None,
    **query_values: str,
) -> str:
    """Costruisce l'URL di redirect per il frontend, separando query string e fragment."""
    parsed = urlparse(redirect_uri or "")
    origin = frontend_origin or (
        f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else _build_redirect_uri(request, "")
    )
    fragment_keys = fragment_keys or set()
    params = {key: value for key, value in query_values.items() if key not in fragment_keys and value is not None}
    fragment_params = {key: value for key, value in query_values.items() if key in fragment_keys and value is not None}
    base = origin.rstrip("/")
    query_suffix = f"?{urlencode(params)}" if params else ""
    fragment_suffix = f"#{urlencode(fragment_params)}" if fragment_params else ""
    return f"{base}/{query_suffix}{fragment_suffix}"


def _build_oauth_error_url(request: Request, redirect_uri: str, error: str, frontend_origin: str | None = None) -> "RedirectResponse":  # noqa: F821,UP037
    """Redirect back to the SPA with an ``oauth_error`` query param.

    The error is delivered as a query param (not a fragment) so the SPA can read
    it even on a full document load. The ``redirect_uri`` comes from the signed
    OAuth state, so it is already host-validated. When ``frontend_origin`` is
    provided, the redirect targets the SPA origin instead of the backend origin.
    """
    from fastapi.responses import RedirectResponse

    return RedirectResponse(
        url=_build_frontend_redirect_url(request, redirect_uri, oauth_error=error, frontend_origin=frontend_origin)
    )


def _build_oauth_success_url(redirect_uri: str, token: str, email: str, user_id: Any) -> str:
    """Build the post-login redirect URL that hands the JWT to the SPA.

    - Mobile / custom app schemes (e.g. ``com.bikemaster.app://callback``):
      deliver the token as a query string on the deep-link target.
      NOTE: query-string tokens can be logged by intermediaries; this is an
      accepted tradeoff because native deep-links cannot receive URL fragments.
      The access token is short-lived; future improvement: one-time code exchange.
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


def _oauth_redirect_response(url: str) -> "RedirectResponse":
    from fastapi.responses import RedirectResponse
    resp = RedirectResponse(url=url)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


def _validate_redirect_uri(redirect_uri: str, request: Request | None = None) -> None:
    """Validate an OAuth redirect_uri against the configured allow-list.

    Raises ``HTTPException(400)`` on invalid scheme, missing host, or
    disallowed hostname.
    """
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
        {
            "bikemaster.onrender.com",
            "bikemaster-api.onrender.com",
            "bikemaster-xi.vercel.app",
            "testserver",
        }
        | cors_hosts
        | configured_hosts
    )
    if host_lower not in allowed_hosts:
        if host_lower.endswith(".vercel.app"):
            return
        if host_lower.endswith(".onrender.com"):
            return
        raise HTTPException(status_code=400, detail="Invalid redirect_uri host")


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
        cors_list = _s.cors_origins_list if hasattr(_s, "cors_origins_list") else []
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


OAUTH_STATE_TTL_MIN = 10


def _issue_oauth_state(redirect_uri: str, pkce_id: str | None = None, frontend_origin: str | None = None) -> str:
    """Issue a signed, server-only OAuth state (random nonce + redirect_uri + pkce_id).

    Replaces the previous client-generated ``base64({redirect_uri})`` state which was
    predictable and provided no CSRF protection.
    """
    payload = {
        "nonce": secrets.token_urlsafe(32),
        "redirect_uri": redirect_uri,
        "pkce_id": pkce_id,
        "frontend_origin": frontend_origin,
        "exp": datetime.now(UTC) + timedelta(minutes=OAUTH_STATE_TTL_MIN),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "type": "oauth_state",
    }
    return jwt.encode(payload, _s.secret_key, algorithm=ALGORITHM)


def _verify_oauth_state(state: str) -> dict | None:
    """Verify a signed OAuth state. Returns {redirect_uri, pkce_id, frontend_origin} or None if invalid/expired."""
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
    return {
        "redirect_uri": redirect_uri,
        "pkce_id": payload.get("pkce_id"),
        "frontend_origin": payload.get("frontend_origin"),
    }


def _http_error_detail(exc: Exception, fallback: str) -> str:
    """Extract a safe error message from an HTTP or network exception.

    Upstream provider response bodies are intentionally redacted to avoid
    leaking internal error codes, stack traces, or provider-specific details
    to the client.
    """
    return fallback


def _user_id(current_user: dict) -> int:
    """Extract the integer user/athlete id from the authenticated user dict."""
    try:
        return int(current_user["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid user token") from exc


def _json_safe(value: Any) -> Any:
    """Convert common non-JSON-serializable Python types (especially those
    returned by psycopg2) to types that ``json.dumps`` can encode.

    Handles ``Decimal``, ``datetime``, ``date``, ``time``, ``UUID``,
    ``bytes`` and ``set`` — the set of types that psycopg2 may return
    for PostgreSQL columns but which FastAPI's ``jsonable_encoder``
    may not always handle inside a plain ``dict`` returned from raw SQL.
    """
    import datetime as _dt
    import decimal
    import uuid

    if value is None:
        return None
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (decimal.Decimal,)):
        return float(value) if not _is_nan_decimal(value) else 0.0
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, _dt.time):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, set):
        return sorted(v for v in value if v is not None)
    return value


def _is_nan_decimal(d: decimal.Decimal) -> bool:
    if d.is_nan() or d.is_infinite():
        return True
    try:
        float(d)
        return False
    except (ValueError, OverflowError):
        return True


def _public_athlete(athlete: dict | None) -> dict:
    """Return an athlete dict with sensitive fields stripped and all values
    coerced to JSON-serializable types."""
    if athlete is None:
        return {}
    return {
        k: _json_safe(v)
        for k, v in athlete.items()
        if k not in ("password_hash", "email")
    }


def _athlete_profile_data(athlete: dict | None) -> dict | None:
    """Return only the fields defined in ``AthleteProfile`` from an athlete dict."""
    if athlete is None:
        return None
    allowed_fields = {field.name for field in fields(AthleteProfile)}
    return {k: v for k, v in athlete.items() if k in allowed_fields}


def _ensure_int_user_id(current_user: dict) -> int:
    """Coerce ``current_user["id"]`` to int or raise 401."""
    try:
        return int(current_user["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid user token") from exc


def _current_athlete_id(current_user: dict) -> int:
    """Return the active athlete id from the JWT, falling back to user id."""
    try:
        return int(current_user.get("athlete_id") or current_user["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid user token") from exc


def _ensure_athlete_access(athlete_id: int, current_user: dict) -> None:
    """Raise 403 if ``current_user`` is not the owner or an admin for ``athlete_id``."""
    if current_user.get("is_admin"):
        return
    if int(athlete_id) != _ensure_int_user_id(current_user):
        raise HTTPException(status_code=403, detail="Access denied to this athlete")


def _get_user_oauth_creds(user_id: int, provider: str) -> dict | None:
    from ..db.database import get_user_oauth_credentials as _get_creds

    return _get_creds(user_id, provider)


async def _ensure_users_table() -> None:
    """Ensure the ``users`` table exists in PostgreSQL.

    Used as a fallback when Alembic migrations did not create it yet.
    """
    if not _s.database_url:
        return
    try:
        from ..db.async_db import get_session_factory
        from ..db.models import Base, UserModel

        factory = get_session_factory()
        async with factory() as session:
            stmt = "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users')"
            result = await session.execute(text(stmt))
            exists = result.scalar_one()
            if not exists:
                await session.run_sync(Base.metadata.create_all, tables=[UserModel.__table__])
                await session.commit()
    except Exception:
        pass


def _ensure_ride_access(ride: dict, current_user: dict) -> None:
    """Raise 403 if ``current_user`` is neither the ride owner nor the tenant owner."""
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
    """Format a single Server-Sent Event frame."""
    return f"event: {event}\ndata: {data}\n\n"


def _make_streaming_response(generator: AsyncGenerator[str, None], event_type: str = "chunk") -> StreamingResponse:
    """Wrap an async generator as a Server-Sent Events streaming response."""
    async def stream_gen() -> AsyncGenerator[str, None]:
        """Genera eventi SSE wrappando l'async generator, gestendo errori interni."""
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


def _sanitize_html_message(message: dict) -> dict:
    escaped = {}
    for key, value in message.items():
        if isinstance(value, str):
            escaped[key] = html_module.escape(value)
        elif isinstance(value, dict):
            escaped[key] = _sanitize_html_message(value)
        else:
            escaped[key] = value
    return escaped


_CALLBACK_CSP = "default-src 'self'; script-src 'unsafe-inline' 'self'; style-src 'self'; img-src 'self' data: https:"


def _oauth_callback_response(payload: str, status_code: int = 200, allowed_origin: str | None = None) -> HTMLResponse:
    """Return a tiny HTML page that posts a message to the opener window (OAuth callback).

    Uses postMessage as the primary mechanism. Falls back to localStorage
    events for browsers that clear window.opener after cross-origin navigation
    (e.g. mobile Safari). Also attempts window.close() and falls back to
    about:blank redirect if close is blocked.
    """
    origin = allowed_origin or "self"
    html = (
        "<!DOCTYPE html>"
        '<html><head><meta charset="utf-8"><title>Closing...</title></head>'
        "<body><script>"
        "(function(){"
        "var sent=false;"
        "var targetOrigin=(" + json.dumps(origin) + ");"
        "function doPost(){"
        "if(sent)return;"
        "try{if(window.opener&&!window.opener.closed){window.opener.postMessage(" + payload + ",targetOrigin);sent=true;}}"
        "catch(e){}"
        "try{localStorage.setItem('bikemaster_oauth_result','" + payload + "');}catch(e){}"
        "}"
        "function tryClose(){"
        "try{window.close();}catch(e){}"
        "if(!window.closed){"
        "try{window.location.replace('about:blank');}catch(e){}"
        "}"
        "setTimeout(function(){try{window.close();}catch(e){}},50);"
        "}"
        "doPost();"
        "setTimeout(doPost,50);"
        "setTimeout(doPost,150);"
        "setTimeout(doPost,400);"
        "setTimeout(function(){"
        "if(!sent){try{window.opener&&window.opener.postMessage(" + payload + ",targetOrigin);}catch(e2){}}"
        "try{localStorage.setItem('bikemaster_oauth_result','" + payload + "');}catch(e){}"
        "tryClose();"
        "},50);"
        "})();</script></body></html>"
    )
    response = HTMLResponse(content=html, status_code=status_code)
    response.headers["Content-Security-Policy"] = _CALLBACK_CSP
    return response


def _oauth_html_response(html: str, status_code: int = 200) -> HTMLResponse:
    """HTMLResponse with a permissive CSP for OAuth callback pages (inline scripts)."""
    response = HTMLResponse(content=html, status_code=status_code)
    response.headers["Content-Security-Policy"] = _CALLBACK_CSP
    return response


def _strava_message_html(message: dict, status_code: int = 200, allowed_origin: str | None = None) -> HTMLResponse:
    """Return a tiny HTML page that posts a message to the opener window (OAuth callback)."""
    payload = json.dumps(_sanitize_html_message(message))
    return _oauth_callback_response(payload, status_code=status_code, allowed_origin=allowed_origin)


def _google_fit_message_html(message: dict, allowed_origin: str | None = None) -> HTMLResponse:
    """Return a tiny HTML page that posts a message to the opener window (OAuth callback)."""
    payload = json.dumps(_sanitize_html_message(message))
    return _oauth_callback_response(payload, allowed_origin=allowed_origin)


def _google_health_message_html(message: dict, allowed_origin: str | None = None) -> HTMLResponse:
    """Return a tiny HTML page that posts a message to the opener window (OAuth callback)."""
    payload = json.dumps(_sanitize_html_message(message))
    return _oauth_callback_response(payload, allowed_origin=allowed_origin)


@router.get("/health")
async def health_check():
    """Basic liveness probe for the API service."""
    return {"status": "ok", "service": "bikemaster"}


@router.get("/version")
async def version_check():
    """Return the current application version from package.json."""
    import json as _json

    version = "0.0.0"
    source = "unknown"

    pkg_path = Path(__file__).resolve().parent.parent.parent.parent / "package.json"
    if pkg_path.is_file():
        try:
            data = _json.loads(pkg_path.read_text(encoding="utf-8"))
            version = data.get("version", version)
            source = "package.json"
        except Exception:
            pass

    return {"version": version, "source": source}


@router.post("/cron")
async def cron_job(request: Request):
    """Scheduled maintenance endpoint for Vercel cron jobs.

    Verifies the ``X-Cron-Secret`` header against ``CRON_SECRET`` env var,
    then runs lightweight maintenance tasks (backup rotation).
    """
    expected = os.getenv("CRON_SECRET")
    if not expected:
        logger.warning("/cron called but CRON_SECRET is not configured")
        raise HTTPException(status_code=500, detail="Cron not configured")
    provided = request.headers.get("X-Cron-Secret", "")
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid cron secret")
    try:
        from ..db.database import scheduled_backup

        result = scheduled_backup(max_backups=10)
    except Exception:
        logger.exception("Scheduled cron task failed")
        result = {"status": "error"}
    return result


@router.post("/alerts/webhook")
async def alerts_webhook(request: Request):
    """Receive alerts from Prometheus Alertmanager.

    Validates the ``X-Alertmanager-Webhook-Token`` header against
    ``ALERTMANAGER_WEBHOOK_TOKEN``. Always requires the token to be set.
    Logs the receiver name for audit.
    """
    expected_token = os.getenv("ALERTMANAGER_WEBHOOK_TOKEN")
    if not expected_token:
        if _s.environment.lower() in ("production", "prod", "staging"):
            logger.error("ALERTMANAGER_WEBHOOK_TOKEN not set: refusing /alerts/webhook in production")
            raise HTTPException(status_code=500, detail="Webhook not configured")
        else:
            logger.warning("ALERTMANAGER_WEBHOOK_TOKEN not set: /alerts/webhook is unauthenticated (dev only)")
    provided = request.headers.get("X-Alertmanager-Webhook-Token", "")
    if not provided or not hmac.compare_digest(provided, expected_token or ""):
        raise HTTPException(status_code=401, detail="Invalid webhook token")
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
    raise HTTPException(status_code=500, detail="Sentry sentinel")


@router.get("/health/redis")
async def health_redis():
    """Check Redis connectivity and return connection status."""
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
    """Return the Google Maps JS API key for the frontend.

    The key is served only to allowed origins as defense-in-depth, because
    Maps JS keys are inherently client-side and must be restricted by
    HTTP referrer in Google Cloud Console.

    DEPLOYMENT CHECK: ensure the key in GOOGLE_MAPS_API_KEY has HTTP referrer
    restrictions configured in Google Cloud Console, limited to your Vercel
    and Render domains. Without this, the key can be extracted and abused.
    """
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
    current_user: dict = Depends(get_current_user),
):
    """Return Points of Interest within ``radius`` km of (lat, lon).

    Only POIs belonging to the current user's tenant are returned.
    """
    from ..analytics.repositories.poi_repository import POIRepository
    from ..db.async_db import get_session_factory

    tenant_id = current_user.get("tenant_id", current_user["id"])
    try:
        repo = POIRepository(session_factory=get_session_factory())
    except RuntimeError:
        repo = POIRepository()
    pois = await repo.get_nearby(lat, lon, radius, tenant_id=tenant_id)
    return {"pois": pois}


@router.get("/maps/pois")
async def list_pois_endpoint(
    itinerary_id: int | None = None, current_user: dict = Depends(get_current_user)
):
    """List POIs, optionally filtered by itinerary_id.

    Only POIs belonging to the current user's tenant are returned.
    """
    from ..db.database import list_pois

    tenant_id = current_user.get("tenant_id", current_user["id"])
    return {"pois": list_pois(itinerary_id, tenant_id=tenant_id)}


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
async def get_poi_endpoint(poi_id: int, current_user: dict = Depends(get_current_user)):
    """Retrieve a Point of Interest by ID.

    Only POIs belonging to the current user's tenant are accessible
    (admins can access any).
    """
    from ..db.database import get_poi

    tenant_id = current_user.get("tenant_id", current_user["id"])
    poi = get_poi(poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    if not current_user.get("is_admin") and poi.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this POI")
    return poi


@router.delete("/maps/pois/{poi_id}")
async def delete_poi_endpoint(
    poi_id: int, current_user: dict = Depends(get_current_user)
):
    """Delete a POI if the current user is the owner or an admin."""
    from ..db.database import delete_poi, get_poi

    poi = get_poi(poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    if not current_user.get("is_admin") and poi["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed to delete this POI")
    delete_poi(poi_id)
    return {"deleted": True}


@router.post("/itineraries")
async def create_itinerary(
    payload: ItineraryCreate, current_user: dict = Depends(get_current_user)
):
    """Create a new itinerary owned by the current athlete."""
    from ..db.database import save_itinerary

    athlete_id = _user_id(current_user)
    data = payload.model_dump()
    data["athlete_id"] = athlete_id
    data["tenant_id"] = current_user.get("tenant_id", athlete_id)
    try:
        itinerary_id = save_itinerary(data)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=422, detail=f"Invalid itinerary data: {exc}"
        ) from exc
    return {"id": itinerary_id, **data}


@router.post("/notifications")
async def create_notification(
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    """Create a notification for the current athlete."""
    message = payload.get("message")
    if not message or not isinstance(message, str):
        raise HTTPException(status_code=422, detail="message is required")
    athlete_id = _user_id(current_user)
    return {"id": 0, "athlete_id": athlete_id, "message": message, "read": False}


@router.get("/itineraries")
async def list_itineraries_endpoint(current_user: dict = Depends(get_current_user)):
    """List itineraries for the current athlete."""
    from ..db.database import list_itineraries

    athlete_id = _user_id(current_user)
    if current_user.get("is_admin"):
        return {"itineraries": list_itineraries()}
    return {"itineraries": list_itineraries(athlete_id)}


@router.get("/itineraries/{itinerary_id}")
async def get_itinerary_endpoint(
    itinerary_id: int, current_user: dict = Depends(get_current_user)
):
    """Get a single itinerary with its stages."""
    from ..db.database import get_itinerary, list_stages

    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary["athlete_id"] != _user_id(current_user) and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    return {"itinerary": itinerary, "stages": list_stages(itinerary_id)}


@router.post("/itineraries/{itinerary_id}/stages")
async def create_stage(
    itinerary_id: int,
    payload: StageCreate,
    current_user: dict = Depends(get_current_user),
):
    """Add a stage to an itinerary owned by the current athlete."""
    from ..db.database import get_itinerary, save_stage

    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary["athlete_id"] != _user_id(current_user) and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    data = payload.model_dump(exclude_unset=True)
    data["itinerary_id"] = itinerary_id
    stage_id = save_stage(data)
    return {"id": stage_id, **data}


@router.put("/itineraries/{itinerary_id}")
async def update_itinerary_endpoint(
    itinerary_id: int,
    payload: ItineraryCreate,
    current_user: dict = Depends(get_current_user),
):
    """Update an itinerary owned by the current athlete."""
    from ..db.database import get_itinerary, update_itinerary

    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary["athlete_id"] != _user_id(current_user) and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    tenant_id = current_user.get("tenant_id", itinerary.get("athlete_id"))
    data = payload.model_dump(exclude_unset=True)
    ok = update_itinerary(itinerary_id, data, tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Itinerary not found or no changes")
    updated = get_itinerary(itinerary_id)
    return updated


@router.delete("/itineraries/{itinerary_id}")
async def delete_itinerary_endpoint(
    itinerary_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Delete an itinerary owned by the current athlete."""
    from ..db.database import delete_itinerary, get_itinerary

    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary["athlete_id"] != _user_id(current_user) and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    tenant_id = current_user.get("tenant_id", itinerary.get("athlete_id"))
    ok = delete_itinerary(itinerary_id, tenant_id)
    return {"deleted": ok}


@router.get("/itineraries/{itinerary_id}/stages/{stage_id}")
async def get_stage_endpoint(
    itinerary_id: int,
    stage_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Retrieve a single stage by id."""
    from ..db.database import get_itinerary, get_stage

    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary["athlete_id"] != _user_id(current_user) and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    stage = get_stage(stage_id)
    if not stage or stage.get("itinerary_id") != itinerary_id:
        raise HTTPException(status_code=404, detail="Stage not found")
    return stage


@router.put("/itineraries/{itinerary_id}/stages/{stage_id}")
async def update_stage_endpoint(
    itinerary_id: int,
    stage_id: int,
    payload: StageCreate,
    current_user: dict = Depends(get_current_user),
):
    """Update a stage within an itinerary owned by the current athlete."""
    from ..db.database import get_itinerary, get_stage, update_stage

    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary["athlete_id"] != _user_id(current_user) and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    tenant_id = current_user.get("tenant_id", itinerary.get("athlete_id"))
    stage = get_stage(stage_id)
    if not stage or stage.get("itinerary_id") != itinerary_id:
        raise HTTPException(status_code=404, detail="Stage not found")
    data = payload.model_dump(exclude_unset=True)
    data["itinerary_id"] = itinerary_id
    ok = update_stage(stage_id, data, tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Stage not found or no changes")
    return get_stage(stage_id)


@router.delete("/itineraries/{itinerary_id}/stages/{stage_id}")
async def delete_stage_endpoint(
    itinerary_id: int,
    stage_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Delete a stage from an itinerary owned by the current athlete."""
    from ..db.database import delete_stage, get_itinerary, get_stage

    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary["athlete_id"] != _user_id(current_user) and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    tenant_id = current_user.get("tenant_id", itinerary.get("athlete_id"))
    stage = get_stage(stage_id)
    if not stage or stage.get("itinerary_id") != itinerary_id:
        raise HTTPException(status_code=404, detail="Stage not found")
    ok = delete_stage(stage_id, tenant_id)
    return {"deleted": ok}


@router.put("/itineraries/{itinerary_id}/reorder")
async def reorder_stages_endpoint(
    itinerary_id: int,
    stage_order: list[int],
    current_user: dict = Depends(get_current_user),
):
    """Reorder stages within an itinerary owned by the current athlete."""
    from ..db.database import get_itinerary, reorder_stages

    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary["athlete_id"] != _user_id(current_user) and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    tenant_id = current_user.get("tenant_id", itinerary.get("athlete_id"))
    reorder_stages(itinerary_id, stage_order, tenant_id)
    return {"reordered": True}



@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate athlete and return JWT access/refresh tokens.

    Supports both SQLAlchemy (async) and legacy SQLite backends.
    Rate limited to 5 attempts per minute per IP.
    """
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

            access_token = create_access_token(
                subject=str(user.id),
                is_admin=user.is_admin,
                tenant_id=user.id,
                is_client=user.is_client,
                athlete_id=user.id,
            )
            refresh_token = create_refresh_token(
                user.id,
                is_admin=user.is_admin,
                tenant_id=user.id,
                is_client=user.is_client,
                athlete_id=user.id,
            )
            await save_refresh_token(user.id, refresh_token)
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "username": user.username,
                "id": user.id,
                "athlete_id": user.id,
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
    access_token = create_access_token(
        subject=str(athlete_id),
        is_admin=False,
        tenant_id=athlete_id,
        is_client=False,
        athlete_id=athlete_id,
    )
    refresh_token = create_refresh_token(
        athlete_id,
        is_admin=False,
        tenant_id=athlete_id,
        is_client=False,
        athlete_id=athlete_id,
    )
    await save_refresh_token(athlete_id, refresh_token)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "username": row[1],
        "id": athlete_id,
        "athlete_id": athlete_id,
        "is_admin": False,
    }


@router.post("/auth/logout")
async def logout(request: Request, current_user: dict = Depends(get_current_user)):
    """Revoke the current access and refresh tokens, plus best-effort revocation
    of any connected external OAuth tokens (Strava/Wahoo/Garmin/Google).

    Extracts the JWT jti from the Authorization header to revoke the
    access token, then revokes the stored refresh token for the athlete, and
    finally attempts to revoke external provider tokens so a global logout
    also disconnects linked accounts.
    """
    from ..security import revoke_refresh_token, revoke_token

    auth_header = request.headers.get("authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    athlete_id = current_user.get("id")
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
            sub_id = payload_data.get("sub")
            if sub_id:
                refresh_revoked = await revoke_refresh_token(int(sub_id))
                if not refresh_revoked:
                    logger.warning("Logout: refresh token revocation failed for athlete_id=%s", sub_id)
    except Exception as exc:
        logger.warning("Logout: failed to revoke token: %s", exc)

    # Best-effort revocation of external OAuth tokens for this athlete.
    if athlete_id is not None:
        _revoke_external_tokens(athlete_id)

    return {"msg": "Logged out successfully"}


def _revoke_external_tokens(athlete_id: int) -> None:
    """Revoke Strava/Wahoo/Garmin/Google tokens best-effort (never raises)."""
    providers = [
        ("bike_analyzer.backend.ingestion.strava_client", "revoke_token"),
        ("bike_analyzer.backend.ingestion.wahoo_client", "revoke_token"),
        ("bike_analyzer.backend.ingestion.garmin_client", "revoke_token"),
        ("bike_analyzer.backend.ingestion.google_oauth_store", "delete_google_token"),
    ]
    for module_path, func_name in providers:
        try:
            import importlib

            module = importlib.import_module(module_path)
            func = getattr(module, func_name, None)
            if func is not None:
                if func_name == "delete_google_token":
                    func(athlete_id, "google")
                else:
                    func(athlete_id)
        except Exception as exc:
            logger.warning(
                "Logout: external token revocation failed for %s: %s",
                module_path,
                exc,
            )


@router.post("/auth/refresh")
@limiter.limit("10/minute")
async def refresh_token(request: Request, payload: RefreshTokenRequest):
    """Exchange a valid refresh token for a new access token.

    Validates the refresh token type, checks revocation status, and
    issues a new access token with the same admin/tenant claims.
    """
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
    is_client = bool(jwt_payload.get("is_client", False))
    tenant_id = jwt_payload.get("tenant_id")
    resolved_tenant = int(tenant_id) if tenant_id is not None else int(user_id)
    return {
        "access_token": create_access_token(
            subject=str(user_id), is_admin=is_admin, tenant_id=resolved_tenant, is_client=is_client
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
    """Register a new athlete account.

    Validates uniqueness of username/email, hashes the password, and
    creates both a UserModel (for auth) and an AthleteModel profile.
    Rate limited to 3 attempts per minute per IP.
    """
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

    await _ensure_users_table()

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
            user_values: dict[str, Any] = {
                "username": username,
                "password_hash": password_hash,
                "is_admin": False,
                "is_active": True,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
            if email:
                user_values["email"] = email
            stmt = (
                insert(UserModel)
                .values(**user_values)
                .returning(UserModel.id)
            )
            result = await session.execute(stmt)
            user_id = result.scalar_one()
            await session.commit()

            athlete_values: dict[str, Any] = {
                "id": user_id,
                "user_id": user_id,
                "name": username,
                "experience_level": "Beginner",
                "tenant_id": user_id,
                "created_at": datetime.now(UTC),
            }
            if email:
                athlete_values["email"] = email
            athlete = AthleteModel(**athlete_values)
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
    """Return the authenticated athlete's profile summary.

    Returns profile completeness flag. If no athlete profile exists,
    returns the user info with profile_complete=False and no auto-creation.
    """
    from ..db.database import (
        get_athlete as _get_athlete,
    )

    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete = _get_athlete(current_user["id"], tenant_id)
    if not athlete:
        return {
            "id": current_user["id"],
            "username": current_user.get("username") or current_user.get("email") or str(current_user["id"]),
            "email": current_user.get("email"),
            "picture": current_user.get("picture"),
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
        "age": athlete.get("age"),
        "weight_kg": athlete.get("weight_kg"),
        "height_cm": athlete.get("height_cm"),
        "experience_level": athlete.get("experience_level", "Beginner"),
        "goals": athlete.get("goals"),
        "equipment": athlete.get("equipment"),
        "ftp_watts": athlete.get("ftp_watts"),
        "created_at": athlete.get("created_at"),
        "updated_at": athlete.get("updated_at"),
    }


@router.post("/legal/consent")
async def record_consent(
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    consent_type = str(payload.get("consent_type", "")).strip()
    granted = bool(payload.get("granted", True))
    source = str(payload.get("source", "web"))
    if not consent_type:
        raise HTTPException(status_code=400, detail="consent_type is required")
    from ..db.database import save_consent
    athlete_id = current_user.get("athlete_id") or current_user["id"]
    save_consent(
        athlete_id=athlete_id,
        consent_type=consent_type,
        granted=granted,
        source=source,
        tenant_id=current_user.get("tenant_id", current_user["id"]),
    )
    return {"status": "recorded", "consent_type": consent_type, "granted": granted}


@router.get("/legal/consent")
async def get_my_consents(current_user: dict = Depends(get_current_user)):
    from ..db.database import get_consents_by_athlete
    athlete_id = current_user.get("athlete_id") or current_user["id"]
    return {"consents": get_consents_by_athlete(athlete_id)}


@router.post("/legal/accept")
async def record_legal_acceptance(
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    acceptance_type = str(payload.get("acceptance_type", "")).strip()
    version = str(payload.get("version", "")).strip()
    source = str(payload.get("source", "web"))
    if not acceptance_type or not version:
        raise HTTPException(status_code=400, detail="acceptance_type and version are required")
    from ..db.database import save_legal_acceptance
    athlete_id = current_user.get("athlete_id") or current_user["id"]
    save_legal_acceptance(
        athlete_id=athlete_id,
        acceptance_type=acceptance_type,
        version=version,
        source=source,
        tenant_id=current_user.get("tenant_id", current_user["id"]),
    )
    return {"status": "recorded", "acceptance_type": acceptance_type, "version": version}


@router.get("/legal/acceptances")
async def get_my_acceptances(current_user: dict = Depends(get_current_user)):
    from ..db.database import get_legal_acceptances_by_athlete
    athlete_id = current_user.get("athlete_id") or current_user["id"]
    return {"acceptances": get_legal_acceptances_by_athlete(athlete_id)}


@router.get("/legal/export-all")
async def export_all_my_data(current_user: dict = Depends(get_current_user)):
    import json

    from fastapi.responses import FileResponse

    from ..db.database import (
        get_ai_audit_logs_by_athlete,
        get_athlete,
        get_beck_assessments_by_athlete,
        get_consents_by_athlete,
        get_events_by_athlete,
        get_fitness_states_by_athlete,
        get_food_logs_by_athlete,
        get_legal_acceptances_by_athlete,
        get_metrics_by_athlete,
        get_rides_by_athlete,
        get_training_stress_days,
    )
    athlete_id = current_user.get("athlete_id") or current_user["id"]
    tenant_id = current_user.get("tenant_id", current_user["id"])
    now = datetime.now(UTC).isoformat()
    path = f"bikemaster_export_{current_user['id']}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
    export_data = {
        "user": current_user,
        "athlete": get_athlete(athlete_id, tenant_id),
        "rides": get_rides_by_athlete(athlete_id, tenant_id),
        "metrics": get_metrics_by_athlete(athlete_id, tenant_id),
        "calendar_events": get_events_by_athlete(athlete_id, tenant_id),
        "fitness_states": get_fitness_states_by_athlete(athlete_id, tenant_id),
        "training_stress_days": get_training_stress_days(athlete_id, tenant_id),
        "food_logs": get_food_logs_by_athlete(athlete_id, tenant_id),
        "beck_assessments": get_beck_assessments_by_athlete(athlete_id, tenant_id),
        "legal_acceptances": get_legal_acceptances_by_athlete(athlete_id),
        "consents": get_consents_by_athlete(athlete_id),
        "ai_audit_logs": get_ai_audit_logs_by_athlete(athlete_id, limit=500),
        "exported_at": now,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
    return FileResponse(path, media_type="application/json", filename=path, background=BackgroundTask(os.remove, path))


@router.delete("/legal/delete-account")
async def delete_my_account(current_user: dict = Depends(get_current_user)):
    from ..db.database import (
        delete_athlete as _delete_athlete,
    )
    from ..db.database import (
        get_athlete as _get_athlete,
    )
    athlete_id = current_user.get("athlete_id") or current_user["id"]
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete = _get_athlete(athlete_id, tenant_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    _delete_athlete(athlete_id, current_user["id"])
    return {"status": "deleted"}


@router.put("/auth/profile")
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update the authenticated athlete's profile fields.

    Only whitelisted fields are accepted; null values are ignored.
    The tenant_id is resolved from the current user's token.
    """
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
        "body_water_percentage",
        "muscle_mass_percentage",
        "bmr_kcal",
        "fat_mass_kg",
        "subcutaneous_fat_kg",
        "subcutaneous_fat_percentage",
        "visceral_fat_level",
        "visceral_fat_percentage",
        "visceral_fat_kg",
        "muscle_mass_kg",
        "bone_mass_kg",
        "protein_percentage",
        "protein_kg",
        "body_age",
        "apparent_age",
        "bmi",
        "lean_body_mass_kg",
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
    """Change the authenticated athlete's password.

    Verifies the current password before updating to the new hash.
    """
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
    frontend_origin: str | None = Query(None),
    state: str = "",
):
    """Get Google OAuth2 authorization URL."""
    from ..auth.google_auth import get_google_oauth_url

    if not _s.google_client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")
    redirect_uri = redirect_uri or _build_redirect_uri(request, "/api/v1/auth/google/callback")
    _validate_redirect_uri(redirect_uri, request)
    if frontend_origin:
        _validate_redirect_uri(frontend_origin, request)
    state = _issue_oauth_state(redirect_uri, frontend_origin=frontend_origin)
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
        resp = _build_oauth_error_url(
            request, _build_redirect_uri(request, "/api/v1/auth/google/callback"), "invalid_state"
        )
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    redirect_uri = state_data["redirect_uri"]
    frontend_origin = state_data.get("frontend_origin")
    _validate_redirect_uri(redirect_uri, request)
    _validate_frontend_origin(frontend_origin, request)

    if error:
        message = error_description or error
        resp = _build_oauth_error_url(request, redirect_uri, message, frontend_origin)
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    if not code:
        resp = _build_oauth_error_url(request, redirect_uri, "missing_code", frontend_origin)
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    cache_key = f"oauth:code:{code}"
    try:
        cached_result = await _cached(cache_key)
        if cached_result:
            resp = RedirectResponse(url=cached_result["redirect_url"])
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
            return resp

        try:
            token_data = await asyncio.to_thread(
                exchange_google_code, _s.google_client_id, _s.google_client_secret, code, redirect_uri
            )
        except Exception as exc:
            response = getattr(exc, "response", None)
            if response is not None and getattr(response, "status_code", None) == 400:
                resp = _build_oauth_error_url(request, redirect_uri, "oauth_error", frontend_origin)
                resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
                resp.headers["Pragma"] = "no-cache"
                resp.headers["Expires"] = "0"
                return resp
            error_body = response.text if response is not None else str(exc)
            error_detail = f"token_exchange_failed:{error_body[:200]}"
            resp = _build_oauth_error_url(request, redirect_uri, error_detail, frontend_origin)
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
            return resp
        access_token = token_data.get("access_token")
        if not access_token:
            resp = _build_oauth_error_url(request, redirect_uri, "no_access_token", frontend_origin)
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
            return resp

        try:
            user_info = await asyncio.to_thread(get_google_user_info, access_token)
        except Exception as exc:
            response = getattr(exc, "response", None)
            error_body = response.text if response is not None else str(exc)
            resp = _build_oauth_error_url(request, redirect_uri, f"userinfo_failed:{error_body[:200]}", frontend_origin)
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
            return resp
        google_sub = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name")

        if not google_sub:
            resp = _build_oauth_error_url(request, redirect_uri, "invalid_user_info", frontend_origin)
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
            return resp

        try:
            existing = await asyncio.to_thread(get_athlete_by_email, email) if email else None
        except Exception as exc:
            logger.exception("Google OAuth athlete lookup failed: %s", exc)
            resp = _build_oauth_error_url(request, redirect_uri, "user_lookup_failed", frontend_origin)
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
            return resp

        if not existing:
            from ..redis_client import get_redis

            lock_key = f"oauth:lock:athlete:{email or google_sub}"
            r = await get_redis()
            if r is not None:
                lock_acquired = await r.set(lock_key, "1", ex=10, nx=True)
                lock_release = lambda: None  # will be replaced below
            else:
                from ..db.database import acquire_oauth_sqlite_lock, release_oauth_sqlite_lock

                lock_acquired = acquire_oauth_sqlite_lock(lock_key, ttl_seconds=10)
                lock_release = lambda: release_oauth_sqlite_lock(lock_key)
            try:
                if lock_acquired:

                    def _create_athlete():
                        """Crea un atleta se non esiste (per email o sub), con tenant_id isolato."""
                        result = get_athlete_by_email(email) if email else None
                        if not result:
                            try:
                                athlete_id = save_athlete(
                                    {
                                        "name": name or email or google_sub,
                                        "email": email,
                                        "picture": user_info.get("picture"),
                                        "experience_level": "Beginner",
                                    }
                                )
                                if athlete_id:
                                    try:
                                        from ..db.database import update_athlete
                                        update_athlete(athlete_id, {"tenant_id": athlete_id})
                                    except Exception:
                                        logger.warning("Google OAuth update_athlete failed for athlete_id=%s", athlete_id)
                                result = get_athlete(athlete_id)
                                if result is None and athlete_id:
                                    logger.warning("Google OAuth get_athlete returned None after save for athlete_id=%s, using fallback", athlete_id)
                                    result = {"id": athlete_id}
                            except Exception:
                                logger.exception(
                                    "Athlete creation failed, checking if already created by another request"
                                )
                                result = get_athlete_by_email(email) if email else None
                                if not result:
                                    raise
                        return result

                    existing = await asyncio.to_thread(_create_athlete)
                else:
                    await asyncio.sleep(0.5)
                    existing = await asyncio.to_thread(get_athlete_by_email, email)
            except Exception as exc:
                logger.exception("Google OAuth athlete creation failed: %s", exc)
                if r is not None:
                    await r.delete(lock_key)
                else:
                    lock_release()
                resp = _build_oauth_error_url(request, redirect_uri, "user_creation_failed", frontend_origin)
                resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
                resp.headers["Pragma"] = "no-cache"
                resp.headers["Expires"] = "0"
                return resp
            finally:
                if r is not None:
                    await r.delete(lock_key)
                else:
                    lock_release()

        if not existing:
            resp = _build_oauth_error_url(request, redirect_uri, "user_creation_failed", frontend_origin)
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
            return resp

        try:
            jwt_token = create_google_session(user_info, athlete_id=existing["id"])["access_token"]
        except Exception as exc:
            logger.exception("Google OAuth session creation failed: %s", exc)
            resp = _build_oauth_error_url(request, redirect_uri, "session_creation_failed", frontend_origin)
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
            return resp

        frontend_origin = state_data.get("frontend_origin")
        redirect_target = frontend_origin or redirect_uri
        redirect_url = _build_oauth_success_url(redirect_target, jwt_token, email or "", existing["id"])
        await _cache_set(f"oauth:code:{code}", {"redirect_url": redirect_url}, ttl=300)
        return _oauth_redirect_response(redirect_url)
    except Exception as exc:
        logger.exception("Google OAuth callback failed: %s", exc)
        resp = _build_oauth_error_url(request, redirect_uri, "server_error", frontend_origin)
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp


@router.post("/auth/google/code-exchange")
@limiter.limit("10/minute")
async def google_code_exchange(
    request: Request,
    payload: dict[str, str] = Body(...),
):
    """Scambia il codice OAuth Google per token e crea una sessione JWT."""
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
    from ..redis_client import get_redis
    from ..db.database import acquire_oauth_sqlite_lock, release_oauth_sqlite_lock

    lock_key = f"oauth:lock:athlete:{email or google_sub}"
    r = await get_redis()
    if r is not None:
        lock_acquired = await r.set(lock_key, "1", ex=10, nx=True)
        lock_release = lambda: None
    else:
        lock_acquired = acquire_oauth_sqlite_lock(lock_key, ttl_seconds=10)
        lock_release = lambda: release_oauth_sqlite_lock(lock_key)

    try:
        if lock_acquired:

            def _create_athlete():
                result = get_athlete_by_email(email) if email else None
                if not result:
                    try:
                        athlete_id = save_athlete(
                            {
                                "name": user_info.get("name") or email or google_sub,
                                "email": email,
                                "picture": user_info.get("picture"),
                                "experience_level": "Beginner",
                            }
                        )
                        if athlete_id:
                            try:
                                from ..db.database import update_athlete
                                update_athlete(athlete_id, {"tenant_id": athlete_id})
                            except Exception:
                                logger.warning("Google OAuth update_athlete failed for athlete_id=%s", athlete_id)
                        result = get_athlete(athlete_id)
                        if result is None and athlete_id:
                            logger.warning("Google OAuth get_athlete returned None after save for athlete_id=%s, using fallback", athlete_id)
                            result = {"id": athlete_id}
                    except Exception:
                        logger.exception(
                            "Athlete creation failed in code-exchange, checking if already created"
                        )
                        result = get_athlete_by_email(email) if email else None
                        if not result:
                            raise
                return result

            existing = await asyncio.to_thread(_create_athlete)
        else:
            await asyncio.sleep(0.5)
            existing = await asyncio.to_thread(get_athlete_by_email, email)
    finally:
        if r is not None:
            await r.delete(lock_key)
        else:
            lock_release()

    if not existing:
        raise HTTPException(status_code=500, detail="user_creation_failed")
    jwt_token = create_google_session(user_info, athlete_id=existing["id"])["access_token"]
    return {"access_token": jwt_token, "email": email or "", "user_id": str(existing["id"])}


@router.post("/rides")
async def create_ride(ride_data: RideCreate, current_user: dict = Depends(get_current_user)):
    """Create a new ride and assign it to the authenticated athlete.

    Validates and cleans GPS points server-side via ``process_route``,
    computes avg_speed and calories if missing (with heart-rate-based
    estimation when HR is available), publishes a RideCreated event,
    and invalidates the dashboard cache.
    """
    from ..db.database import save_ride

    ride_dict = ride_data.model_dump()
    ride_dict["athlete_id"] = _current_athlete_id(current_user)
    ride_dict["tenant_id"] = _ensure_int_user_id(current_user)
    points = ride_dict.get("gps_points", [])
    if points:
        gps_points: list[GPSPoint] = []
        for p in points:
            try:
                ts = p.get("timestamp")
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                gps_points.append(
                    GPSPoint(
                        lat=p["lat"],
                        lon=p["lon"],
                        timestamp=ts,
                        altitude=p.get("altitude"),
                        speed=p.get("speed"),
                        heart_rate=p.get("heart_rate"),
                        cadence=p.get("cadence"),
                        power=p.get("power"),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        if gps_points:
            cleaned, stats = process_route(gps_points)
            ride_dict["gps_points"] = [
                {
                    "lat": p.lat,
                    "lon": p.lon,
                    "altitude": p.altitude,
                    "timestamp": p.timestamp.isoformat() if p.timestamp else None,
                    "speed": p.speed,
                    "heart_rate": p.heart_rate,
                    "cadence": p.cadence,
                    "power": p.power,
                }
                for p in cleaned
            ]
            ride_dict["distance_km"] = ride_dict.get("distance_km") or round(
                stats.total_distance_m / 1000, 2
            )
            ride_dict["duration_minutes"] = ride_dict.get("duration_minutes") or round(
                stats.total_duration_s / 60, 2
            )
            ride_dict["avg_speed_kmh"] = ride_dict.get("avg_speed_kmh") or round(
                stats.avg_speed_km_h, 2
            )
            ride_dict["elevation_gain_m"] = ride_dict.get("elevation_gain_m") or round(
                stats.total_elevation_gain_m, 1
            )
    if (
        not ride_dict.get("avg_speed_kmh")
        and ride_dict.get("distance_km")
        and ride_dict.get("duration_minutes")
        and ride_dict["duration_minutes"] > 0
    ):
        ride_dict["avg_speed_kmh"] = ride_dict["distance_km"] / (ride_dict["duration_minutes"] / 60)
    if not ride_dict.get("calories"):
        ride = Ride(**{k: v for k, v in ride_dict.items() if k not in ("gps_points", "tenant_id")})
        if ride_dict.get("heart_rate_avg") and ride.distance_km and ride.duration_minutes:
            method = "hr"
        elif ride_dict.get("avg_speed_kmh"):
            method = "physics"
        else:
            method = "met"
        ride_dict["calories"] = estimate_calories(ride, method=method)
    ride_id = save_ride(ride_dict)
    from ..events import RideCreated, publish

    await publish(
        RideCreated.type,
        {
            "ride_id": int(ride_id),
            "athlete_id": _current_athlete_id(current_user),
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
    """List rides for the authenticated athlete with pagination.

    Missing calories are estimated on-the-fly using the physics or MET
    method depending on available speed data.
    """
    from ..analytics.calories import ensure_calories
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    all_rides = get_rides_by_athlete(_current_athlete_id(current_user), tenant_id)
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
    """Return the total number of rides for the authenticated athlete."""
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    return {"count": len(get_rides_by_athlete(_current_athlete_id(current_user), tenant_id))}


@router.get("/rides/{ride_id}")
async def get_ride(ride_id: int, current_user: dict = Depends(get_current_user)):
    """Get a single ride by ID with computed fatigue and calories metrics.

    Access control ensures the athlete can only retrieve their own rides
    (admins can access any ride).
    """
    from ..db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    r = Ride(**ride)
    ride["fatigue_score"] = round(calculate_fatigue_score(r), 1)
    ride["recovery_hours"] = round(estimate_recovery_hours(ride["fatigue_score"]), 1)
    ride["calories_per_km"] = round(calories_per_km(r), 0) if r.distance_km else 0
    return ride


@router.get("/rides/{ride_id}/gpx")
async def export_ride_gpx(
    ride_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Export a ride as a GPX 1.1 XML document.

    Includes heart rate, cadence, and power extensions when available.
    """
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
            q = {k: v for k, v in p.items() if k != "elevation"}
            q["altitude"] = p.get("elevation")
            normalized.append(q)
        else:
            normalized.append(p)
    points = [GPSPoint(**p) for p in normalized]

    def _ele_str(p: GPSPoint) -> str:
        if p.altitude is not None:
            return f"\n        <ele>{p.altitude}</ele>"
        return ""

    def _extensions_str(p: GPSPoint) -> str:
        parts: list[str] = []
        if p.heart_rate is not None:
            parts.append(f"<gpxtpx:hr>{p.heart_rate}</gpxtpx:hr>")
        if p.cadence is not None:
            parts.append(f"<gpxtpx:cad>{p.cadence}</gpxtpx:cad>")
        if p.power is not None:
            parts.append(f"<gpxtpx:power>{p.power}</gpxtpx:power>")
        if not parts:
            return ""
        return f"\n        <gpxtpx:TrackPointExtension>\n          {''.join(parts)}\n        </gpxtpx:TrackPointExtension>"

    def _time_str(p: GPSPoint) -> str:
        if p.timestamp is not None:
            return p.timestamp.isoformat().replace("+00:00", "Z")
        return datetime.now(UTC).isoformat()

    trkpts = []
    for p in points:
        trkpts.append(
            f"      <trkpt lat=\"{p.lat}\" lon=\"{p.lon}\">{_ele_str(p)}"
            f"\n        <time>{_time_str(p)}</time>"
            f"{_extensions_str(p)}\n      </trkpt>"
        )

    gpx_body = "\n".join(trkpts)

    gpx = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gpx version="1.1" creator="BikeMaster-Backend" xmlns="http://www.topografix.com/GPX/1/1"\n'
        '      xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">\n'
        "  <trk>\n"
        f"    <name>{ride.get('title') or 'BikeMaster ride'}</name>\n"
        "    <trkseg>\n"
        f"{gpx_body}\n"
        "    </trkseg>\n"
        "  </trk>\n"
        "</gpx>\n"
    )

    return StreamingResponse(
        iter([gpx]),
        media_type="application/gpx+xml",
        headers={"Content-Disposition": f'attachment; filename="ride_{ride_id}.gpx"'},
    )


@router.get("/rides/{ride_id}/map")
async def generate_ride_map(
    ride_id: int,
    provider: str = Query("folium", description="Map provider: folium or aethermap"),
    current_user: dict = Depends(get_current_user),
):
    """Generate an interactive map HTML/JSON for a ride's GPS track.

    Supports the built-in Folium renderer and the AetherMap provider.
    GPS points are normalized (elevation -> altitude) before rendering.
    """
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
            q = {k: v for k, v in p.items() if k != "elevation"}
            q["altitude"] = p.get("elevation")
            normalized.append(q)
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


@router.get("/aethermap/terrain")
async def get_aethermap_terrain(
    min_lat: float = Query(..., description="Minimum latitude"),
    max_lat: float = Query(..., description="Maximum latitude"),
    min_lon: float = Query(..., description="Minimum longitude"),
    max_lon: float = Query(..., description="Maximum longitude"),
    resolution: int = Query(64, description="Grid resolution (NxN)", ge=8, le=256),
    source: str = Query("auto", description="Terrain source: auto, dem, procedural, copernicus, lidar, osm"),
):
    """Return a terrain heightfield tile for the given bounding box.

    Heights are in meters above sea level. The response includes the tile bounds,
    source, and a flat array of ``resolution x resolution`` float32 values.
    """
    from ..maps.terrain import get_tile

    if not (-90 <= min_lat <= max_lat <= 90):
        raise HTTPException(status_code=400, detail="Invalid latitude range")
    min_lon = ((min_lon + 180) % 360) - 180
    max_lon = ((max_lon + 180) % 360) - 180
    if max_lon < min_lon:
        min_lon, max_lon = max_lon, min_lon
    if max_lon - min_lon > 360:
        raise HTTPException(status_code=400, detail="Invalid longitude range")
    if not (-180 <= min_lon <= max_lon <= 180):
        raise HTTPException(status_code=400, detail="Invalid longitude range")

    tile = get_tile(min_lat, max_lat, min_lon, max_lon, resolution, source=source)
    return {
        "min_lat": tile.min_lat,
        "max_lat": tile.max_lat,
        "min_lon": tile.min_lon,
        "max_lon": tile.max_lon,
        "resolution": tile.resolution,
        "source": tile.source,
        "heights": tile.heights.flatten().tolist(),
    }


@router.get("/aethermap/world")
@limiter.limit("30/minute")
async def get_aethermap_world(request: Request):
    """Return the full AetherMap world data for the WebGL renderer.

    Returns terrain mesh, entities, relations, and camera settings
    in the format expected by ``webgl_stub.html``.
    """


    from aethermap.render.webgl_exporter import (
        _build_full_heightfield,
        _entity_to_gl,
        _terrain_mesh_from_hf,
    )
    from aethermap.twin.objects import make_albero, make_montagna, make_strada
    from aethermap.twin.world import DigitalTwin, Environment

    twin = DigitalTwin()
    pts = [
        {"lat": 45.0 + i * 0.0005, "lon": 9.0 + i * 0.0006, "ele": 120 + (i % 2) * 2}
        for i in range(6)
    ]
    twin.add(make_strada("strada-1", 45.0, 9.0, pts))
    twin.add(make_albero("albero-1", 45.005, 9.01, "quercia", 8.5))
    twin.add(make_montagna("montagna-1", 45.015, 9.03, 1800.0, ["nord", "sud", "est"]))

    env = Environment(temp_c=15.0, solar_elev_deg=30.0, ora="12:00")
    twin.step(env)

    n_terrain = 64
    hf = _build_full_heightfield(n_terrain, 0.0, 0.04).flatten()
    terrain = _terrain_mesh_from_hf(hf, n_terrain)

    entities = []
    for obj in twin.store.objects.values():
        entities.append(_entity_to_gl(obj))

    relations = []
    for obj in twin.store.objects.values():
        for rel in obj.relazioni:
            relations.append({
                "from": obj.id,
                "to": rel.target_id,
                "tipo": rel.tipo,
                "peso": rel.peso,
            })

    return {
        "version": "aethermap-webgl-1.0",
        "terrain": terrain,
        "entities": entities,
        "relations": relations,
        "camera": {"yaw": 0.6, "pitch": 0.35},
        "earth_r": 6371000.0,
    }


def _build_procedural_heightfield(n: int, base: float = 0.0, scale: float = 0.04) -> np.ndarray:
    from aethermap.render.webgl_exporter import _build_heightfield
    return _build_heightfield(n, base, scale)


def _face_bbox(face: int) -> tuple[float, float, float, float]:
    face_bbox = {
        0: (0.0, 90.0, -180.0, -90.0),
        1: (0.0, 90.0, -90.0, 0.0),
        2: (0.0, 90.0, 0.0, 90.0),
        3: (0.0, 90.0, 90.0, 180.0),
        4: (-90.0, 0.0, -180.0, -90.0),
        5: (90.0, 180.0, -180.0, 180.0),
    }
    return face_bbox.get(face, (0.0, 90.0, -180.0, 180.0))


@router.get("/aethermap/terrain-tile")
@limiter.limit("60/minute")
async def get_aethermap_terrain_tile(
    request: Request,
    face: int = Query(0, ge=0, le=5, description="Cube face index (0-5)"),
    resolution: int = Query(64, ge=8, le=256, description="Grid resolution"),
    dem: str | None = Query(None, description="Use real DEM if available (copernicus|lidar|osm)"),
):
    """Return a cube-sphere terrain mesh for a single face.

    Used by the WebGL renderer for LOD terrain streaming.
    """
    cache_key = f"aethermap:tile:{face}:{resolution}:{dem or 'procedural'}"
    cached_data = await _cached(cache_key, ttl=3600)
    if cached_data is not None:
        return cached_data

    from aethermap.render.webgl_exporter import _build_heightfield, _face_direction

    n = resolution
    hf = _build_procedural_heightfield(n)
    source = "procedural"

    if dem:
        try:
            from aethermap.data.dem_loader import get_dem_loader
            loader = get_dem_loader()
            if loader is not None:
                bbox = _face_bbox(face)
                real_hf = loader.load(bbox, resolution)
                if real_hf is not None and np.mean(np.abs(real_hf)) > 1e-6:
                    hf = real_hf
                    source = f"dem:{dem}"
        except Exception as exc:
            logger.debug("DEM load failed, falling back to procedural: %s", exc)

    face_hf = hf

    # Convert heightfield to meters for frontend data contract.
    # Backend internal representation is normalized [0, height_scale] or [0, 1] from DEM.
    # Frontend expects meters and applies terrainH * TERRAIN_SCALE internally.
    _MAX_ELEVATION_M = 4000.0
    if source == "procedural":
        proc_max = float(_build_procedural_heightfield(n).max())
        if proc_max > 1e-6:
            face_hf = hf * (_MAX_ELEVATION_M / proc_max)
    elif source.startswith("dem:"):
        dem_max = float(hf.max())
        if dem_max > 1e-6:
            face_hf = hf * (_MAX_ELEVATION_M / dem_max)

    positions: list[list[float]] = []
    normals: list[list[float]] = []
    indices: list[int] = []
    grid_size = n + 2

    base_idx = 0
    for i in range(grid_size):
        for j in range(grid_size):
            src_i = max(0, min(i - 1, n - 1))
            src_j = max(0, min(j - 1, n - 1))
            u = (src_i / (n - 1)) * 2.0 - 1.0
            v = (src_j / (n - 1)) * 2.0 - 1.0
            d = _face_direction(face, u, v)
            h = float(face_hf[src_i, src_j])
            is_skirt = i == 0 or i == grid_size - 1 or j == 0 or j == grid_size - 1
            if is_skirt:
                h = min(h, 0.0) - 0.0001
            px = float(d[0] * (1.0 + h))
            py = float(d[1] * (1.0 + h))
            pz = float(d[2] * (1.0 + h))
            positions.append([px, py, pz])
            normals.append([float(d[0]), float(d[1]), float(d[2])])

    for i in range(grid_size - 1):
        for j in range(grid_size - 1):
            a = base_idx + i * grid_size + j
            b = base_idx + (i + 1) * grid_size + j
            c = base_idx + (i + 1) * grid_size + (j + 1)
            d2 = base_idx + i * grid_size + (j + 1)
            indices.extend([a, b, d2])
            indices.extend([b, c, d2])

    payload = {
        "positions": positions,
        "normals": normals,
        "indices": indices,
        "grid_size": grid_size,
        "face": face,
        "resolution": resolution,
        "source": source,
    }
    await _cache_set(cache_key, payload, ttl=3600)
    return payload


@router.get("/aethermap/geo/roads")
async def get_aethermap_geo_roads(
    place: str = Query(..., description="Place name (e.g. 'Pavia, Italy')"),
    network_type: str = Query("drive", description="OSM network type"),
    simplify: bool = Query(True, description="Simplify geometries"),
):
    """Return OSM road network as GeoJSON for a place name."""
    try:
        from aethermap.geo.osm_loader import load_roads
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Geo dependencies not installed") from exc
    try:
        data = load_roads(place, network_type=network_type, simplify=simplify)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return data


@router.get("/aethermap/geo/cities")
async def get_aethermap_geo_cities(
    north: float = Query(..., description="North latitude"),
    south: float = Query(..., description="South latitude"),
    east: float = Query(..., description="East longitude"),
    west: float = Query(..., description="West longitude"),
):
    """Return city/place POIs as GeoJSON within a bounding box."""
    try:
        from aethermap.geo.osm_loader import load_cities
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Geo dependencies not installed") from exc
    try:
        data = load_cities((north, south, east, west))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return data


@router.get("/aethermap/geo/peaks")
async def get_aethermap_geo_peaks(
    north: float = Query(..., description="North latitude"),
    south: float = Query(..., description="South latitude"),
    east: float = Query(..., description="East longitude"),
    west: float = Query(..., description="West longitude"),
    min_ele: float = Query(0.0, description="Minimum elevation in meters"),
):
    """Return mountain peaks as GeoJSON within a bounding box."""
    try:
        from aethermap.geo.osm_loader import load_peaks
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Geo dependencies not installed") from exc
    try:
        data = load_peaks((north, south, east, west), min_ele=min_ele)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return data


@router.get("/aethermap/geo/natural-earth")
async def get_aethermap_geo_natural_earth(
    resolution: str = Query("110m", description="Data resolution (10m, 50m, 110m)"),
    min_pop: int = Query(50000, description="Minimum city population"),
):
    """Return Natural Earth coastline, border, and city data as GeoJSON."""
    try:
        from aethermap.geo.natural_earth import (
            load_coastlines,
            load_country_borders,
            load_cities,
            to_entities,
        )
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Geo dependencies not installed") from exc
    try:
        coastlines = load_coastlines(resolution=resolution)
        borders = load_country_borders(resolution=resolution)
        try:
            cities = load_cities(resolution=resolution, min_pop=min_pop)
        except Exception as exc:
            logger.warning("[aethermap] load_cities failed: %s — returning without cities", exc)
            cities = {"type": "FeatureCollection", "features": []}
        ne_data = to_entities(
            coastlines=coastlines,
            borders=borders,
            cities=cities,
        )
        if not ne_data or not isinstance(ne_data, dict):
            raise HTTPException(status_code=502, detail="empty natural earth data")
        features = []
        for ent in ne_data.get("entities", []):
            if ent.get("kind") == "line":
                pts = ent.get("points", [])
                coords = [[float(p.get("lon", 0)), float(p.get("lat", 0))] for p in pts if isinstance(p, dict)]
                props = {"tipo": ent.get("tipo"), **ent.get("props", {})}
                if "color" in ent:
                    props["color"] = ent["color"]
                features.append({
                    "type": "Feature",
                    "properties": props,
                    "geometry": {"type": "LineString", "coordinates": coords},
                })
            else:
                pos = ent.get("position", [0, 0])
                lat = float(pos[0]) if len(pos) > 0 else 0.0
                lon = float(pos[1]) if len(pos) > 1 else 0.0
                props = {"tipo": ent.get("tipo"), **ent.get("props", {})}
                if "color" in ent:
                    props["color"] = ent["color"]
                features.append({
                    "type": "Feature",
                    "properties": props,
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                })
        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "source": "natural_earth",
                "resolution": resolution,
                "coastline_count": int(ne_data.get("coastline_count", 0)),
                "border_count": int(ne_data.get("border_count", 0)),
                "city_count": int(ne_data.get("city_count", 0)),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


_twin_instance: DigitalTwin | None = None


def _get_twin() -> DigitalTwin:
    global _twin_instance
    if _twin_instance is None:
        from aethermap.twin import DigitalTwin
        _twin_instance = DigitalTwin(persistent=True)
    return _twin_instance


@router.get("/aethermap/twin/snapshot")
async def get_aethermap_twin_snapshot(current_user: dict = Depends(get_current_user)):
    """Return the current Digital Twin snapshot (live object states)."""
    try:
        twin = _get_twin()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Digital Twin not available: {exc}",
        ) from exc
    return {"objects": twin.snapshot(), "count": len(twin.store.objects)}


@router.get("/aethermap/twin/step")
async def post_aethermap_twin_step(
    temp_c: float = Query(15.0, description="Temperature in Celsius"),
    solar_elev_deg: float = Query(45.0, description="Solar elevation angle"),
    ora: str = Query("12:00", description="Time of day (HH:MM)"),
    current_user: dict = Depends(get_current_user),
):
    """Advance the Digital Twin simulation by one step."""
    from aethermap.twin import Environment
    try:
        twin = _get_twin()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Digital Twin not available: {exc}",
        ) from exc
    env = Environment(temp_c=temp_c, solar_elev_deg=solar_elev_deg, ora=ora)
    result = twin.step(env)
    return {"objects": twin.snapshot(), **result}


@router.get("/aethermap/sync")
@limiter.limit("10/minute")
async def get_aethermap_sync(request: Request, current_user: dict = Depends(get_current_user)):
    """Export the current Digital Twin state for offline sync."""
    try:
        from aethermap.data.sync import TwinSyncEngine
        from aethermap.twin.world import DigitalTwin

        twin = DigitalTwin()
        engine = TwinSyncEngine(twin)
        return engine.export()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Sync export failed: {exc}") from exc


@router.post("/aethermap/sync")
@limiter.limit("10/minute")
async def post_aethermap_sync(
    request: Request,
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    """Import a Digital Twin state snapshot for offline sync."""
    try:
        from aethermap.data.sync import TwinSyncEngine
        from aethermap.twin.world import DigitalTwin

        twin = DigitalTwin()
        engine = TwinSyncEngine(twin)
        engine.import_sync(payload)
        return {"imported": len(twin.store.objects)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Sync import failed: {exc}") from exc


@router.get("/rides/{ride_id}/terrain")
@limiter.limit("20/minute")
async def get_ride_terrain_enrichment(
    request: Request,
    ride_id: int,
    temp_c: float = Query(15.0, description="Temperature in Celsius"),
    solar_elev_deg: float = Query(45.0, description="Solar elevation angle"),
    ora: str = Query("12:00", description="Time of day"),
    enabled: bool = Query(
        False,
        description="Enable terrain enrichment (requires BIKEMASTER_TERRAIN_ENRICHMENT=true)",
    ),
    current_user: dict = Depends(get_current_user),
):
    """Enrich ride GPS points with terrain data from AetherMap.

    Returns GPS points with slope_pct, surface_type, shade,
    traffic_level, and terrain_confidence fields.
    Requires BIKEMASTER_TERRAIN_ENRICHMENT=true env var.
    """
    if enabled and not _s.terrain_enrichment_enabled:
        raise HTTPException(
            status_code=403,
            detail="Terrain enrichment is disabled. Set BIKEMASTER_TERRAIN_ENRICHMENT=true to enable.",
        )

    from ..db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points for this ride")

    cache_key = f"aethermap:terrain:{ride_id}:{enabled}:{temp_c}:{solar_elev_deg}:{ora}"
    cached_data = await _cached(cache_key, ttl=600)
    if cached_data is not None:
        return cached_data

    from ..models.models import GPSPoint
    from ..monitoring import aethermap_terrain_enrichment_duration_seconds, aethermap_terrain_enrichment_total

    points = [GPSPoint(**p) for p in gps_points]
    t0 = time.perf_counter()
    try:
        enricher = TerrainEnricher(
            temp_c=temp_c,
            solar_elev_deg=solar_elev_deg,
            ora=ora,
            enabled=enabled,
        )
        enriched = enricher.enrich_ride(points)
        result = {
            "ride_id": ride_id,
            "enriched": [p.to_dict() for p in enriched],
            "terrain_features": enricher.snapshot(),
            "h3_summary": enricher.h3_summary(),
        }
        duration = time.perf_counter() - t0
        if aethermap_terrain_enrichment_total is not None:
            aethermap_terrain_enrichment_total.labels(status="success").inc()
        if aethermap_terrain_enrichment_duration_seconds is not None:
            aethermap_terrain_enrichment_duration_seconds.observe(duration)
        await _cache_set(cache_key, result, ttl=600)
        return result
    except Exception as exc:
        if aethermap_terrain_enrichment_total is not None:
            aethermap_terrain_enrichment_total.labels(status="error").inc()
        if aethermap_ml_errors_total is not None:
            aethermap_ml_errors_total.labels(error_type=type(exc).__name__).inc()
        raise


@router.post("/rides/analyze")
async def analyze_rides(request: Request, payload: RideAnalysisRequest, current_user: dict = Depends(get_current_user)):
    """Run full analytics summary over a list of ride payloads."""
    from ..analytics.analytics import calculate_summary
    from ..models.models import Ride

    return await run_in_threadpool(calculate_summary, [Ride(**r.model_dump()) for r in payload.rides])


@router.post("/rides/{ride_id}/analyze")
async def analyze_single_ride(ride_id: int, ride_data: RideCreate, current_user: dict = Depends(get_current_user)):
    """Run analytics on a single ride with optional overrides."""
    from ..analytics.analytics import analyze_ride
    from ..models.models import Ride

    return await run_in_threadpool(analyze_ride, Ride(id=ride_id, **ride_data.model_dump()))


@router.delete("/rides/{ride_id}")
async def delete_ride(ride_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a ride. Only the owner (or admin) can delete."""
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
    """Detect and return significant segments from ride GPS points.

    Builds a Folium map of the detected segments and returns its URL.
    """
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
            q = {k: v for k, v in p.items() if k != "elevation"}
            q["altitude"] = p.get("elevation")
            normalized.append(q)
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
    from bike_analyzer.core.validation import ValidatedGPSPoint, ValidatedRide

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
    """Import a GPX file as a new ride.

    Parses the GPX, validates GPS points, estimates missing metrics,
    and stores the ride. Runs CPU-bound parsing in a thread pool.
    """
    from ..db.database import save_ride
    from ..ingestion.gps_parser import parse_gpx_file, points_to_ride

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")
    user_id = _user_id(current_user)
    tenant_id = current_user["id"]
    filename = file.filename

    def _work() -> dict:
        """Esegue il flusso sincrono di importazione GPX: parsing, conversione, validazione e salvataggio."""
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


@router.post("/import/tcx")
async def import_tcx(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Import a TCX file as a new ride.

    Parses the TCX, validates GPS points, estimates missing metrics,
    and stores the ride. Runs CPU-bound parsing in a thread pool.
    """
    from ..db.database import save_ride
    from ..ingestion.gps_parser import parse_tcx_file, points_to_ride

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")
    user_id = _user_id(current_user)
    tenant_id = current_user["id"]
    filename = file.filename

    def _work() -> dict:
        """Esegue il flusso sincrono di importazione TCX."""
        t0 = time.perf_counter()
        points_data = parse_tcx_file(content.decode())
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
            "tcx_import_timing parse_ms=%.1f process_ms=%.1f db_ms=%.1f points=%d",
            (t1 - t0) * 1000,
            (t2 - t1) * 1000,
            (t3 - t2) * 1000,
            len(points_data),
        )
        return ride_data

    ride_data = await asyncio.to_thread(_work)
    if "error" not in ride_data:
        from ..monitoring import record_gps_import

        record_gps_import("tcx", "upload")
    return ride_data


@router.post("/import/fit")
async def import_fit(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Import a FIT file as a new ride.

    Writes the upload to a temp file, parses it with the FIT library,
    validates the result, and stores the ride.
    """
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
        """Esegue il flusso sincrono di importazione FIT da file temporaneo, con pulizia."""
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

            try:
                os.unlink(temp_path)
            except OSError:
                logger.debug("Failed to remove temp FIT file %s", temp_path)
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
    """Detailed health check including database statistics.

    Returns ride/athlete counts and database file size.
    """
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


@router.get("/health/comprehensive")
async def health_comprehensive(request: Request):
    """Comprehensive health check with system metrics.

    Returns database, redis, task queue status plus memory, disk and uptime.
    """
    from ..monitoring import comprehensive_health_check

    base = await comprehensive_health_check()
    payload = base.to_dict()

    try:
        payload["disk"] = {
            "db_path": _s.db_path,
            "db_exists": Path(_s.db_path).exists(),
        }
        if Path(_s.db_path).exists():
            payload["disk"]["db_size_bytes"] = Path(_s.db_path).stat().st_size
    except Exception as exc:  # noqa: BLE001
        payload["system_metrics_error"] = str(exc)

    try:
        payload["uptime"] = {
            "start_time": getattr(request.app.state, "start_time", None),
            "uptime_seconds": round(time.time() - getattr(request.app.state, "start_time", time.time()), 2),
        }
    except Exception as exc:  # noqa: BLE001
        payload["uptime_error"] = str(exc)

    try:
        mem = {"available": False}
        try:
            import psutil

            proc = psutil.Process()
            mem = {
                "available": True,
                "rss_bytes": proc.memory_info().rss,
                "rss_mb": round(proc.memory_info().rss / (1024 * 1024), 2),
                "vms_bytes": proc.memory_info().vms,
                "vms_mb": round(proc.memory_info().vms / (1024 * 1024), 2),
            }
        except ImportError:
            mem["note"] = "psutil not installed"
        payload["memory"] = mem
    except Exception as exc:  # noqa: BLE001
        payload["memory_error"] = str(exc)

    return payload


@router.get("/coach/history")
async def coach_chat_history(athlete_id: int = Query(...), current_user: dict = Depends(get_current_user)):
    """Retrieve AI coach chat history for an athlete."""
    from ..db.database import get_chat_history

    _ensure_athlete_access(athlete_id, current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    history = get_chat_history(athlete_id, tenant_id=tenant_id)
    return {"athlete_id": athlete_id, "history": history}


@router.post("/import/multiple")
async def import_multiple(files: list[UploadFile] = File(...), current_user: dict = Depends(get_current_user)):
    """Batch import multiple GPX/FIT files in a single request.

    Each file is processed in a separate thread; results are aggregated
    into imported/failed lists. Total upload limited to 100MB.
    """
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
        """Elabora un singolo file GPX/FIT in thread separato e salva la corsa."""
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
    """Export all rides for the authenticated athlete as JSON.

    The file is written to a temp file and streamed back with a
    BackgroundTask that deletes it after delivery.
    """
    from fastapi.responses import FileResponse

    from ..analytics.analytics import export_rides_json
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(_current_athlete_id(current_user), tenant_id)]
    with tempfile.NamedTemporaryFile(prefix=f"rides_export_{current_user['id']}_", suffix=".json", delete=False) as tmp:
        path = tmp.name
    await asyncio.to_thread(export_rides_json, rides, path)
    return FileResponse(
        path,
        media_type="application/json",
        filename="rides.json",
        background=BackgroundTask(os.remove, path),
    )


@router.get("/rides/export/csv")
async def export_csv(current_user: dict = Depends(get_current_user)):
    """Export all rides for the authenticated athlete as CSV.

    The file is written to a temp file and streamed back with a
    BackgroundTask that deletes it after delivery.
    """
    from fastapi.responses import FileResponse

    from ..analytics.analytics import export_rides_csv
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(_current_athlete_id(current_user), tenant_id)]
    with tempfile.NamedTemporaryFile(prefix=f"rides_export_{current_user['id']}_", suffix=".csv", delete=False) as tmp:
        path = tmp.name
    await asyncio.to_thread(export_rides_csv, rides, path)
    return FileResponse(
        path,
        media_type="text/csv",
        filename="rides.csv",
        background=BackgroundTask(os.remove, path),
    )


@router.get("/rides/{ride_id}/report")
async def get_ride_report(ride_id: int, current_user: dict = Depends(get_current_user)):
    """Generate a text performance report for a single ride."""
    from ..analytics.analytics import generate_text_report
    from ..db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    report = await asyncio.to_thread(generate_text_report, Ride(**ride))
    return {"report": report}


@router.get("/charts/speed/{ride_id}")
async def speed_chart(ride_id: int, current_user: dict = Depends(get_current_user)):
    """Generate a speed profile chart PNG for a ride."""
    from ..analytics.analytics import create_speed_chart
    from ..db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points")
    normalized = []
    for p in gps_points:
        if "altitude" not in p and "elevation" in p:
            q = {k: v for k, v in p.items() if k != "elevation"}
            q["altitude"] = p.get("elevation")
            normalized.append(q)
        else:
            normalized.append(p)
    points = [GPSPoint(**p) for p in normalized]
    from ..processing.processing import build_segments

    segments = build_segments(points)
    png = await asyncio.to_thread(create_speed_chart, segments)
    from fastapi.responses import Response

    return Response(content=png, media_type="image/png", headers={"Content-Disposition": "attachment; filename=speed.png"})


@router.get("/charts/duration")
async def duration_chart(current_user: dict = Depends(get_current_user)):
    """Generate a ride duration distribution chart PNG."""
    from ..analytics.analytics import create_duration_chart
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(_current_athlete_id(current_user), tenant_id)]
    png = await asyncio.to_thread(create_duration_chart, rides)
    from fastapi.responses import Response

    return Response(content=png, media_type="image/png", headers={"Content-Disposition": "attachment; filename=duration.png"})


@router.get("/charts/distance/{ride_id}")
async def distance_chart(ride_id: int, current_user: dict = Depends(get_current_user)):
    """Generate a distance profile chart PNG for a ride."""
    from ..analytics.analytics import create_distance_chart
    from ..db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points")
    normalized = []
    for p in gps_points:
        if "altitude" not in p and "elevation" in p:
            q = {k: v for k, v in p.items() if k != "elevation"}
            q["altitude"] = p.get("elevation")
            normalized.append(q)
        else:
            normalized.append(p)
    points = [GPSPoint(**p) for p in normalized]
    from ..processing.processing import build_segments

    segments = build_segments(points)
    png = await asyncio.to_thread(create_distance_chart, segments)
    from fastapi.responses import Response

    return Response(content=png, media_type="image/png", headers={"Content-Disposition": "attachment; filename=distance.png"})


@router.get("/charts/elevation/{ride_id}")
async def elevation_chart(ride_id: int, current_user: dict = Depends(get_current_user)):
    """Generate an elevation profile chart PNG for a ride."""
    from ..analytics.analytics import create_elevation_chart
    from ..db.database import get_ride as _get_ride

    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    _ensure_ride_access(ride, current_user)
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points")
    normalized = []
    for p in gps_points:
        if "altitude" not in p and "elevation" in p:
            q = {k: v for k, v in p.items() if k != "elevation"}
            q["altitude"] = p.get("elevation")
            normalized.append(q)
        else:
            normalized.append(p)
    points = [GPSPoint(**p) for p in normalized]
    from ..processing.processing import build_segments

    segments = build_segments(points)
    png = await asyncio.to_thread(create_elevation_chart, segments)
    from fastapi.responses import Response

    return Response(content=png, media_type="image/png", headers={"Content-Disposition": "attachment; filename=elevation.png"})


@router.post("/athletes", response_model=dict)
async def create_athlete(athlete_data: AthleteCreate, current_user: dict = Depends(get_current_user)):
    """Create or upsert the authenticated user's athlete profile.

    If a profile already exists for the athlete_id, it is updated;
    otherwise a new record is created.
    """
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
            raise HTTPException(status_code=409, detail="Athlete name already in use")

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
    """Return the current user's athlete profile."""
    from ..db.database import get_athlete as _get_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete = _get_athlete(current_user["id"], tenant_id)
    if not athlete:
        return {"athletes": []}
    return {"athletes": [_public_athlete(athlete)]}


@router.get("/athletes/me")
async def get_my_athlete_profile(current_user: dict = Depends(get_current_user)):
    """Return the authenticated athlete's own profile with completeness flag."""
    from ..db.database import get_athlete as _get_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    try:
        athlete = _get_athlete(current_user["id"], tenant_id)
    except Exception:
        logger.exception(
            "get_athlete raised while fetching own profile (user_id=%s)",
            current_user.get("id"),
        )
        raise HTTPException(
            status_code=500,
            detail="Errore nel recupero del profilo atleta",
        )
    if not athlete:
        return {"athlete": None, "profile_complete": False}
    profile_complete = (
        athlete.get("age") is not None
        and athlete.get("weight_kg") is not None
        and (athlete.get("experience_level") or "").strip() != ""
    )
    try:
        safe_athlete = _public_athlete(athlete)
    except Exception:
        logger.exception("Failed to serialize athlete profile")
        safe_athlete = _athlete_profile_data(athlete)
    return {"athlete": safe_athlete, "profile_complete": profile_complete}


@router.get("/athletes/me/metric-log")
async def get_my_metric_log(
    metric_type: str = Query(..., description="weight_kg|height_cm|fat_percentage|ftp_watts|mood|sleep_hours"),
    days: int = Query(365, ge=1, le=3650),
    current_user: dict = Depends(get_current_user),
):
    """Return the authenticated athlete's metric history for charting.

    Returns the time series (oldest-first) of ``metric_type`` samples logged
    on every manual update, so the frontend can plot weight / fat% / FTP /
    mood / sleep trends over time.
    """
    from ..db.database import get_athlete as _get_athlete
    from ..db.database import get_athlete_metric_log

    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete = _get_athlete(current_user["id"], tenant_id)
    if not athlete:
        return {"metric_type": metric_type, "series": []}
    series = get_athlete_metric_log(athlete["id"], metric_type, tenant_id=tenant_id, days=days)
    return {"metric_type": metric_type, "series": series}


@router.get("/athletes/me/history")
async def get_my_athlete_history(
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
):
    """Return the authenticated athlete's profile change history.

    Each entry is a full snapshot of the profile state at the moment it was
    overwritten, ordered from newest to oldest.
    """
    from ..db.database import get_athlete as _get_athlete
    from ..db.database import get_athlete_history

    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete = _get_athlete(current_user["id"], tenant_id)
    if not athlete:
        return {"history": []}
    history = get_athlete_history(athlete["id"], tenant_id=tenant_id, limit=limit)
    return {"history": history}


@router.put("/athletes/me")
async def upsert_my_athlete_profile(
    profile_data: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update or create the authenticated athlete's own profile.

    Guarantees a backing athlete record always exists (auto-created with a
    Beginner default if missing) so the frontend onboarding flow can never
    leave the user stranded without a profile.
    """
    from ..db.database import (
        get_athlete as _get_athlete,
    )
    from ..db.database import (
        save_athlete as _save_athlete,
    )
    from ..db.database import (
        update_athlete as _update_athlete,
    )

    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete = _get_athlete(current_user["id"], tenant_id)
    if not athlete:
        username = current_user.get("username") or current_user.get("email") or str(current_user["id"])
        created_id = _save_athlete(
            {
                "name": username,
                "email": current_user.get("email"),
                "experience_level": profile_data.experience_level or "Beginner",
                "tenant_id": tenant_id,
            },
            athlete_id=current_user["id"],
        )
        athlete = _get_athlete(current_user["id"], tenant_id)
        if not athlete:
            raise HTTPException(status_code=500, detail="Failed to create athlete profile")
    updates = {k: v for k, v in profile_data.model_dump().items() if v is not None}
    if updates:
        _update_athlete(athlete["id"], updates)
        from ..db.database import log_athlete_metric

        tracked = {
            "weight_kg": ("kg", "Peso"),
            "height_cm": ("cm", "Altezza"),
            "fat_percentage": ("%", "% grassa"),
            "ftp_watts": ("W", "FTP"),
            "mood": ("/10", "Umore"),
            "sleep_hours": ("h", "Sono"),
            "body_water_percentage": ("%", "Acqua corporea"),
            "muscle_mass_percentage": ("%", "Massa muscolare %"),
            "bmr_kcal": ("kcal", "Metabolismo basale"),
            "fat_mass_kg": ("kg", "Massa grassa"),
            "subcutaneous_fat_kg": ("kg", "Grasso sottocutaneo"),
            "subcutaneous_fat_percentage": ("%", "Grasso sottocutaneo %"),
            "visceral_fat_level": ("lvl", "Grasso viscerale"),
            "visceral_fat_percentage": ("%", "Grasso viscerale %"),
            "visceral_fat_kg": ("kg", "Grasso viscerale kg"),
            "muscle_mass_kg": ("kg", "Massa muscolare"),
            "bone_mass_kg": ("kg", "Massa ossea"),
            "protein_percentage": ("%", "Proteine %"),
            "protein_kg": ("kg", "Proteine kg"),
            "body_age": ("anni", "Eta corporea"),
            "apparent_age": ("anni", "Eta apparente"),
        }
        for field, (unit, _label) in tracked.items():
            if field in updates and updates[field] is not None:
                old = athlete.get(field)
                new_value = float(updates[field])
                if old is None or float(old) != new_value:
                    try:
                        log_athlete_metric(
                            athlete["id"],
                            field,
                            new_value,
                            tenant_id=tenant_id,
                            unit=unit,
                            source="manual",
                        )
                    except Exception:
                        logger.exception(
                            "log_athlete_metric failed after PUT /athletes/me for athlete_id=%s field=%s",
                            athlete["id"],
                            field,
                        )
    athlete = _get_athlete(current_user["id"], tenant_id)
    profile_complete = (
        athlete.get("age") is not None
        and athlete.get("weight_kg") is not None
        and (athlete.get("experience_level") or "").strip() != ""
    )
    return {"athlete": _public_athlete(athlete), "profile_complete": profile_complete}


@router.post("/athletes/me/measurements")
async def log_my_measurement(
    measurement: MeasurementCreate,
    current_user: dict = Depends(get_current_user),
):
    """Log a new body-composition measurement for the current athlete.

    Updates the athlete profile with the supplied fields and records each
    changed metric to ``athlete_metric_log`` with the provided date.
    """
    from ..db.database import (
        get_athlete as _get_athlete,
        update_athlete as _update_athlete,
        log_athlete_metric as _log_athlete_metric,
    )

    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete = _get_athlete(current_user["id"], tenant_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete profile not found")

    updates = {k: v for k, v in measurement.model_dump().items() if v is not None}
    if "recorded_at" in updates:
        recorded_at = updates.pop("recorded_at")
        try:
            recorded_dt = datetime.fromisoformat(recorded_at)
            recorded_at = recorded_dt.replace(tzinfo=UTC).isoformat()
        except ValueError:
            recorded_at = datetime.now(UTC).isoformat()
    else:
        recorded_at = datetime.now(UTC).isoformat()

    if updates:
        _update_athlete(athlete["id"], updates)
        tracked = {
            "weight_kg": ("kg", "Peso"),
            "fat_percentage": ("%", "% grassa"),
            "body_water_percentage": ("%", "Acqua corporea"),
            "muscle_mass_percentage": ("%", "Massa muscolare %"),
            "bmr_kcal": ("kcal", "Metabolismo basale"),
            "fat_mass_kg": ("kg", "Massa grassa"),
            "subcutaneous_fat_percentage": ("%", "Grasso sottocutaneo %"),
            "visceral_fat_percentage": ("%", "Grasso viscerale %"),
            "muscle_mass_kg": ("kg", "Massa muscolare"),
            "bone_mass_kg": ("kg", "Massa ossea"),
            "protein_percentage": ("%", "Proteine %"),
            "ftp_watts": ("W", "FTP"),
        }
        for field, (unit, _label) in tracked.items():
            if field in updates and updates[field] is not None:
                old = athlete.get(field)
                new_value = float(updates[field])
                if old is None or float(old) != new_value:
                    try:
                        _log_athlete_metric(
                            athlete["id"],
                            field,
                            new_value,
                            tenant_id=tenant_id,
                            unit=unit,
                            source="manual",
                            recorded_at=recorded_at,
                        )
                    except Exception:
                        logger.exception(
                            "log_athlete_metric failed for athlete_id=%s field=%s",
                            athlete["id"],
                            field,
                        )

    athlete = _get_athlete(current_user["id"], tenant_id)
    profile_complete = (
        athlete.get("age") is not None
        and athlete.get("weight_kg") is not None
        and (athlete.get("experience_level") or "").strip() != ""
    )
    return {"athlete": _public_athlete(athlete), "profile_complete": profile_complete}


@admin_router.get("/athletes")
async def list_all_athletes(current_user: dict = Depends(get_admin_user)):
    """Return all athlete profiles. Admin only."""
    from ..db.database import get_all_athletes as _get_all

    athletes = _get_all()
    return {"athletes": athletes}


# ------------------------------------------------------------------
# Multi-athlete management routes
# ------------------------------------------------------------------


@router.get("/athletes/mine")
async def list_my_athletes(current_user: dict = Depends(get_current_user)):
    """List all athlete profiles belonging to the current user."""
    from ..db.database import get_athletes_by_user as _get_athletes_by_user

    user_id = int(current_user["id"])
    athletes = _get_athletes_by_user(user_id)
    return {"athletes": [_public_athlete(a) for a in athletes]}


@router.post("/athletes/mine")
async def create_my_athlete(athlete_data: AthleteCreate, current_user: dict = Depends(get_current_user)):
    """Create a new additional athlete profile for the current user."""
    from ..db.database import get_athletes_by_user as _get_athletes_by_user
    from ..db.database import save_athlete as _save_athlete

    user_id = int(current_user["id"])
    count = len(_get_athletes_by_user(user_id))
    if count >= 10:
        raise HTTPException(status_code=403, detail="Maximum 10 athletes per user")

    data = athlete_data.model_dump()
    athlete_id = _save_athlete(data, user_id=user_id)
    return {"athlete_id": athlete_id, "msg": "Athlete created"}


@router.delete("/athletes/mine/{athlete_id}")
async def delete_my_athlete(athlete_id: int, current_user: dict = Depends(get_current_user)):
    """Delete an additional athlete profile. Cannot delete the primary athlete (id == user_id)."""
    from ..db.database import delete_athlete as _delete_athlete

    user_id = int(current_user["id"])
    if athlete_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete primary athlete")
    ok = _delete_athlete(athlete_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Athlete not found or access denied")
    return {"status": "deleted", "athlete_id": athlete_id}


@router.get("/athletes/{athlete_id}")
async def get_athlete_endpoint(athlete_id: int, current_user: dict = Depends(get_current_user)):
    """Get an athlete's public profile. Users can only view their own."""
    from ..db.database import get_athlete as _get_athlete

    _ensure_athlete_access(athlete_id, current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    athlete = _get_athlete(athlete_id, tenant_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    return _public_athlete(athlete)


@router.post("/athletes/{athlete_id}/metrics")
async def add_metric(athlete_id: int, metric_data: MetricCreate, current_user: dict = Depends(get_current_user)):
    """Add a health metric record for an athlete."""
    _ensure_athlete_access(athlete_id, current_user)
    from ..db.database import save_metric

    tenant_id = current_user.get("tenant_id", athlete_id)
    metric_id = save_metric({"athlete_id": athlete_id, "tenant_id": tenant_id, **metric_data.model_dump()})
    return {"id": int(metric_id), "athlete_id": athlete_id, **metric_data.model_dump()}


@router.post("/athletes/{athlete_id}/health-metrics")
async def add_health_metrics(athlete_id: int, metrics: list[dict], current_user: dict = Depends(get_current_user)):
    """Add health metric records from connectors (BLE, Health Connect) for an athlete."""
    _ensure_athlete_access(athlete_id, current_user)
    from ..db.database import log_athlete_metric

    tenant_id = current_user.get("tenant_id", athlete_id)
    saved = []
    for m in metrics:
        metric_id = log_athlete_metric(
            athlete_id=athlete_id,
            tenant_id=tenant_id,
            metric_type=m.get("metric_type"),
            value=m.get("value"),
            unit=m.get("unit"),
            note=m.get("source"),
            source=m.get("source", "health_connect"),
            recorded_at=m.get("recorded_at"),
        )
        saved.append({"id": int(metric_id), **m})
    return {"saved": saved}


@router.put("/athletes/{athlete_id}")
async def update_athlete(
    athlete_id: int,
    athlete_data: AthleteUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update an athlete's profile fields.

    Validates name uniqueness, applies the update, and publishes an
    AthleteUpdated event.
    """
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
            raise HTTPException(status_code=409, detail="Athlete name already in use")
    old_athlete = _get(athlete_id)
    _update(athlete_id, update_data)
    from ..events import AthleteUpdated, publish

    await publish(
        AthleteUpdated.type,
        {"athlete_id": athlete_id, "updated_fields": update_data, "created": False},
    )
    tenant_id = current_user.get("tenant_id", current_user["id"])
    if old_athlete:
        from ..db.database import log_athlete_metric

        tracked = {
            "weight_kg": ("kg", "Peso"),
            "height_cm": ("cm", "Altezza"),
            "fat_percentage": ("%", "% grassa"),
            "ftp_watts": ("W", "FTP"),
            "mood": ("/10", "Umore"),
            "sleep_hours": ("h", "Sono"),
            "body_water_percentage": ("%", "Acqua corporea"),
            "muscle_mass_percentage": ("%", "Massa muscolare %"),
            "bmr_kcal": ("kcal", "Metabolismo basale"),
            "fat_mass_kg": ("kg", "Massa grassa"),
            "subcutaneous_fat_kg": ("kg", "Grasso sottocutaneo"),
            "subcutaneous_fat_percentage": ("%", "Grasso sottocutaneo %"),
            "visceral_fat_level": ("lvl", "Grasso viscerale"),
            "visceral_fat_percentage": ("%", "Grasso viscerale %"),
            "visceral_fat_kg": ("kg", "Grasso viscerale kg"),
            "muscle_mass_kg": ("kg", "Massa muscolare"),
            "bone_mass_kg": ("kg", "Massa ossea"),
            "protein_percentage": ("%", "Proteine %"),
            "protein_kg": ("kg", "Proteine kg"),
            "body_age": ("anni", "Eta corporea"),
            "apparent_age": ("anni", "Eta apparente"),
            "bmi": ("", "BMI"),
            "lean_body_mass_kg": ("kg", "Massa magra"),
        }
        for field, (unit, _label) in tracked.items():
            if field in update_data and update_data[field] is not None:
                old = old_athlete.get(field)
                new_value = float(update_data[field])
                if old is None or float(old) != new_value:
                    log_athlete_metric(
                        athlete_id,
                        field,
                        new_value,
                        tenant_id=tenant_id,
                        unit=unit,
                        source="manual",
                    )
    return _public_athlete(_get(athlete_id))


@router.get("/client/athletes")
async def client_list_athletes(current_user: dict = Depends(get_current_user)):
    """List athletes associated with the current client. Client only."""
    if not current_user.get("is_client"):
        raise HTTPException(status_code=403, detail="Accesso client richiesto")
    from ..db.database import get_all_athletes as _get_all_athletes

    tenant_id = current_user.get("tenant_id", current_user["id"])
    athletes = _get_all_athletes(tenant_id=tenant_id)
    log_action(current_user["id"], "client_list_athletes", "client")
    return {"athletes": athletes}


@router.post("/client/athletes/{athlete_id}/assign")
async def client_assign_athlete(athlete_id: int, current_user: dict = Depends(get_current_user)):
    """Assign an athlete to the current client. Client only."""
    if not current_user.get("is_client"):
        raise HTTPException(status_code=403, detail="Accesso client richiesto")
    from ..db.database import get_athlete as _get_athlete
    from ..db.database import update_athlete as _update_athlete

    athlete = _get_athlete(athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete non trovato")
    tenant_id = current_user.get("tenant_id", current_user["id"])
    _update_athlete(athlete_id, {"tenant_id": tenant_id})
    log_action(current_user["id"], "assign_athlete", "client")
    return {"status": "assigned", "athlete_id": athlete_id, "tenant_id": tenant_id}


@router.get("/metabolism/profile", response_model=MetabolicProfileResponse)
async def get_my_metabolic_profile(current_user: dict = Depends(get_current_user)):
    """Return the authenticated athlete's metabolic profile."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    from ..db.database import get_athlete as _get_athlete
    from ..db.database import get_metabolic_profile as _get_profile

    athlete = _get_athlete(athlete_id, tenant_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    profile = _get_profile(athlete_id, tenant_id)
    if not profile:
        return MetabolicProfileResponse(athlete_id=athlete_id).model_dump()
    return MetabolicProfileResponse(**profile).model_dump()


@router.put("/metabolism/profile")
async def upsert_my_metabolic_profile(
    profile_data: MetabolicProfileCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create or update the authenticated athlete's metabolic profile."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    from ..db.database import get_athlete as _get_athlete
    from ..db.database import get_metabolic_profile as _get_profile
    from ..db.database import save_metabolic_profile as _save_profile

    athlete = _get_athlete(athlete_id, tenant_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    payload = profile_data.model_dump(exclude_none=True)
    _save_profile(payload, athlete_id, tenant_id)
    profile = _get_profile(athlete_id, tenant_id)
    result = profile or {"athlete_id": athlete_id}
    return result


@router.get("/metabolism/food-log")
async def get_my_food_logs(
    date: str = Query(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    current_user: dict = Depends(get_current_user),
):
    """Return today's or specified date's food logs for the authenticated athlete."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    from ..db.database import get_food_logs_by_athlete_date as _get_logs

    return _get_logs(athlete_id, date, tenant_id=tenant_id)


@router.post("/metabolism/food-log", status_code=201)
async def create_food_log(
    log_data: FoodLogCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new food log entry."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    from ..db.database import get_athlete as _get_athlete
    from ..db.database import get_food_log as _get_log
    from ..db.database import save_food_log as _save_log

    athlete = _get_athlete(athlete_id, tenant_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    payload = log_data.model_dump(exclude_none=True)
    payload["athlete_id"] = athlete_id
    payload["tenant_id"] = tenant_id
    log_id = _save_log(payload, tenant_id)
    row = _get_log(log_id)
    return row or {}


@router.put("/metabolism/food-log/{log_id}")
async def update_food_log_entry(
    log_id: int,
    log_data: FoodLogUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update an existing food log entry."""
    athlete_id = _current_athlete_id(current_user)
    from ..db.database import get_food_log as _get_log
    from ..db.database import update_food_log as _update_log

    row = _get_log(log_id)
    if not row or row.get("athlete_id") != athlete_id:
        raise HTTPException(status_code=404, detail="Food log not found")
    payload = log_data.model_dump(exclude_none=True)
    _update_log(log_id, payload)
    row = _get_log(log_id)
    return row or {}


@router.delete("/metabolism/food-log/{log_id}", status_code=204)
async def delete_food_log_entry(
    log_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Delete a food log entry."""
    athlete_id = _current_athlete_id(current_user)
    from ..db.database import delete_food_log as _delete_log
    from ..db.database import get_food_log as _get_log

    row = _get_log(log_id)
    if not row or row.get("athlete_id") != athlete_id:
        raise HTTPException(status_code=404, detail="Food log not found")
    _delete_log(log_id)
    return None


@router.get("/metabolism/daily-summary")
async def get_my_daily_summary(
    date: str = Query(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    current_user: dict = Depends(get_current_user),
):
    """Return the metabolim daily summary for the authenticated athlete."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    from ..analytics.metabolism import recalculate_daily_summary as _recalc

    summary = _recalc(athlete_id, date, tenant_id)
    return summary


@router.get("/metabolism/range-summary")
async def get_my_range_summary(
    start_date: str = Query(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    end_date: str = Query(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    current_user: dict = Depends(get_current_user),
):
    """Return metabolim daily summaries for a date range."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    from ..analytics.metabolism import recalculate_range as _recalc_range

    summaries = _recalc_range(athlete_id, start_date, end_date, tenant_id)
    return summaries


@router.post("/metabolism/recalculate")
async def recalculate_my_daily_summary(
    date: str = Query(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    current_user: dict = Depends(get_current_user),
):
    """Force recalculate the metabolim daily summary for a specific date."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    from ..analytics.metabolism import recalculate_daily_summary as _recalc

    summary = _recalc(athlete_id, date, tenant_id)
    return summary


@router.post("/metabolism/reference-values")
async def import_metabolic_reference_values(
    payload: MetabolicReferenceImportRequest,
    current_user: dict = Depends(get_current_user),
):
    """Import (or replace) known average reference values for age/sex/weight brackets."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    from ..db.database import upsert_metabolic_reference_value as _upsert_ref

    imported = 0
    for v in payload.values:
        _upsert_ref(v.model_dump(), tenant_id)
        imported += 1
    return {"imported": imported, "tenant_id": tenant_id}


@router.get("/metabolism/reference-values")
async def list_metabolic_reference_values(
    current_user: dict = Depends(get_current_user),
):
    """List the imported reference values for the authenticated tenant."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    from ..db.database import get_all_metabolic_reference_values as _list_ref

    return _list_ref(tenant_id)


@router.get("/metabolism/reference")
async def get_my_metabolic_reference(
    current_user: dict = Depends(get_current_user),
):
    """Return the resolved reference mean (imported or built-in) for the athlete's bracket."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    from ..analytics.metabolism import resolve_reference_value as _resolve
    from ..db.database import get_athlete as _get_athlete
    from ..db.database import get_metabolic_profile as _get_profile

    athlete = _get_athlete(athlete_id, tenant_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    profile = _get_profile(athlete_id, tenant_id)
    return _resolve(athlete, profile, tenant_id)


@router.post("/metabolism/calibrate")
async def calibrate_my_metabolic_weights(
    payload: MetabolicCalibrationRequest,
    current_user: dict = Depends(get_current_user),
):
    """Ingest sensor-derived values and update per-athlete model weights + confidence."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    from ..analytics.metabolism import calibrate_athlete as _calibrate

    result = _calibrate(
        athlete_id,
        payload.sensor_bmr_kcal,
        payload.sensor_tdee_kcal,
        date=payload.date,
        tenant_id=tenant_id,
    )
    return MetabolicCalibrationResponse(
        athlete_id=result["athlete_id"],
        reference=result["reference"],
        sensor=result["sensor"],
        weights=MetabolicWeightsResponse(athlete_id=athlete_id, **result["weights"]),
    ).model_dump()


@router.get("/metabolism/weights")
async def get_my_metabolic_weights(
    current_user: dict = Depends(get_current_user),
):
    """Return the per-athlete adaptive weights and sensor confidence."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    from ..analytics.metabolism import get_athlete_weights as _get_weights

    weights = _get_weights(athlete_id, tenant_id)
    return MetabolicWeightsResponse(athlete_id=athlete_id, **weights.to_dict()).model_dump()


@router.post("/metabolism/recalculate-calibrated")
async def recalculate_my_daily_summary_calibrated(
    date: str = Query(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    current_user: dict = Depends(get_current_user),
):
    """Recalculate the daily summary using reference mean + adaptive weights."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    from ..analytics.metabolism import recalculate_daily_summary_calibrated as _recalc_c

    return _recalc_c(athlete_id, date, tenant_id)


# ── Nutrition database ──────────────────────────────────────────────────────────

@router.get("/metabolism/nutrition/search")
async def search_nutrition_food(
    q: str = Query("", max_length=100),
    category: str | None = Query(None, max_length=50),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """Search food items in the nutrition database."""
    from ..db.database import search_nutrition_food_items as _search

    return _search(q.strip(), category=category, limit=limit)


@router.get("/metabolism/nutrition/categories")
async def list_nutrition_categories(
    current_user: dict = Depends(get_current_user),
):
    """Return distinct food categories available in the database."""
    from ..db.database import list_nutrition_categories as _cats

    return _cats()


@router.get("/metabolism/nutrition/{item_id}")
async def get_nutrition_food_item(
    item_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Return a single food item by ID."""
    from ..db.database import get_nutrition_food_item as _get_item

    item = _get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Food item not found")
    return item


@router.post("/metabolism/nutrition", status_code=201)
async def create_nutrition_food_item(
    item_data: NutritionFoodItemCreate,
    current_user: dict = Depends(get_current_user),
):
    """Add a new food item to the user's personal database."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    from ..db.database import get_nutrition_food_item as _get_item
    from ..db.database import save_nutrition_food_item as _save_item

    item_id = _save_item(item_data.model_dump(), tenant_id)
    item = _get_item(item_id)
    return item or {}


@router.put("/metabolism/nutrition/{item_id}")
async def update_nutrition_food_item(
    item_id: int,
    item_data: NutritionFoodItemUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update a user-added food item (built-in items cannot be modified)."""
    from ..db.database import get_nutrition_food_item as _get_item
    from ..db.database import update_nutrition_food_item as _update_item

    existing = _get_item(item_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Food item not found")
    if existing.get("is_builtin"):
        raise HTTPException(status_code=403, detail="Cannot modify built-in items")
    ok = _update_item(item_id, item_data.model_dump(exclude_none=True))
    if not ok:
        raise HTTPException(status_code=500, detail="Update failed")
    item = _get_item(item_id)
    return item or {}


@router.delete("/metabolism/nutrition/{item_id}", status_code=204)
async def delete_nutrition_food_item(
    item_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Delete a user-added food item (built-in items cannot be deleted)."""
    from ..db.database import delete_nutrition_food_item as _del_item
    from ..db.database import get_nutrition_food_item as _get_item

    existing = _get_item(item_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Food item not found")
    if existing.get("is_builtin"):
        raise HTTPException(status_code=403, detail="Cannot delete built-in items")
    _del_item(item_id)
    return None


@router.get("/import/google-fit/auth")
async def google_fit_auth(
    request: Request,
    client_id: str | None = Query(None),
    redirect_uri: str | None = Query(None),
    state: str = Query(""),
    current_user: dict = Depends(get_current_user),
):
    """[Deprecated] Start Google Fit OAuth flow.

    Use Google Health instead. This route is kept for backward compatibility.
    """
    logger.warning("Deprecated Google Fit OAuth route accessed; use Google Health instead")
    from ..ingestion.google_fit import get_authorization_url

    user_creds = _get_user_oauth_creds(int(current_user["id"]), "google_fit")
    google_client_id = client_id or (user_creds or {}).get("client_id") or _s.google_fit_client_id
    if not google_client_id:
        raise HTTPException(status_code=503, detail="Google Fit OAuth not configured")
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
    current_user: dict = Depends(get_current_user),
):
    """Start Google Health OAuth2 PKCE flow.

    Generates a code verifier/challenge, stores the verifier in cache,
    and returns the authorization URL.
    """
    from ..ingestion.google_health import _compute_code_challenge, _generate_code_verifier, get_authorization_url

    user_creds = _get_user_oauth_creds(int(current_user["id"]), "google_health")
    google_client_id = (user_creds or {}).get("client_id") or _s.google_health_client_id
    if not google_client_id:
        raise HTTPException(status_code=500, detail="Google Health OAuth not configured")
    redirect_uri = redirect_uri or _build_redirect_uri(request, "/api/v1/import/google-health/callback")
    _validate_redirect_uri(redirect_uri, request)
    code_verifier = _generate_code_verifier()
    code_challenge = _compute_code_challenge(code_verifier)
    pkce_id = secrets.token_urlsafe(8)
    pkce_key = f"oauth:pkce:google-health:{pkce_id}"
    await _cache_set(pkce_key, {"code_verifier": code_verifier, "redirect_uri": redirect_uri, "user_id": int(current_user["id"])}, ttl=600)
    state = _issue_oauth_state(redirect_uri, pkce_id=pkce_id)
    auth_url = get_authorization_url(
        google_client_id,
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
    """Handle Google Health OAuth2 callback.

    Verifies the state token, exchanges the code for an access token,
    and returns the token via postMessage to the opener window.
    """
    from ..ingestion.google_health import exchange_code_for_token

    if not _s.google_health_client_id or not _s.google_health_client_secret:
        raise HTTPException(status_code=500, detail="Google Health OAuth not configured")
    state_data = _verify_oauth_state(state)
    if not state_data:
        return _google_health_message_html(
            {
                "type": "google-health-error",
                "error": "invalid_state",
                "error_description": "Google Health: invalid or expired state",
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
    cached_pkce = None
    if pkce_id:
        pkce_key = f"oauth:pkce:google-health:{pkce_id}"
        cached_pkce = await _cached(pkce_key)
        if cached_pkce:
            code_verifier = cached_pkce.get("code_verifier", "")
    user_id = None
    if isinstance(cached_pkce, dict):
        user_id = cached_pkce.get("user_id")
    user_creds = None
    if user_id is not None:
        user_creds = _get_user_oauth_creds(user_id, "google_health")
    google_client_id = (user_creds or {}).get("client_id") or _s.google_health_client_id
    google_client_secret = (user_creds or {}).get("client_secret") or _s.google_health_client_secret
    if not google_client_id or not google_client_secret:
        raise HTTPException(status_code=500, detail="Google Health OAuth not configured")
    try:
        token_data = exchange_code_for_token(
            google_client_id,
            google_client_secret,
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
                        "error_description": "Invalid or expired Google Health OAuth code. Re-authorize.",
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
    """Import rides from Google Health Connect.

    Stores the provided tokens, fetches activities, converts them to
    rides, and persists them. Returns the list of imported rides.
    """
    from ..db.database import save_ride
    from ..ingestion.google_health import google_health_to_rides
    from ..ingestion.google_oauth_store import get_valid_google_token, store_google_token

    athlete_id = _current_athlete_id(current_user)

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
    """[Deprecated] Exchange a Google Fit authorization code for tokens.

    Use Google Health instead.
    """
    logger.warning("Deprecated Google Fit token exchange route accessed; use Google Health instead")
    from ..ingestion.google_fit import exchange_code_for_token

    user_creds = _get_user_oauth_creds(int(current_user["id"]), "google_fit")
    client_id = payload.get("client_id") or (user_creds or {}).get("client_id") or _s.google_fit_client_id
    client_secret = payload.get("client_secret") or (user_creds or {}).get("client_secret") or _s.google_fit_client_secret
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
                     detail="Invalid or expired Google OAuth code. Try re-authorizing.",
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
                "error_description": "Google Fit: invalid or expired state",
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
        return _oauth_html_response(cached_result["html"])

    try:
        token_data = exchange_code_for_token(_s.google_fit_client_id, _s.google_fit_client_secret, code, redirect_uri)
    except requests.exceptions.HTTPError as exc:
        response = getattr(exc, "response", None)
        if response is not None and response.status_code == 400:
            cached_retry = await _cached(cache_key)
            if cached_retry:
                return _oauth_html_response(cached_retry["html"])
            return _google_fit_message_html(
                {
                    "type": "google-fit-error",
                    "error": "oauth_error",
                    "error_description": "OAuth code already used or invalid",
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
    payload_str = json.dumps(_sanitize_html_message(payload))
    response = _oauth_callback_response(payload_str)
    await _cache_set(cache_key, {"html": response.body.decode()}, ttl=300)
    return response


@router.post("/import/google-fit")
async def import_google_fit(payload: GoogleFitImportPayload, current_user: dict = Depends(get_current_user)):
    """[Deprecated] Import rides from Google Fit.

    Google Fit API has been deprecated by Google; use Google Health instead.
    """
    logger.warning("Deprecated Google Fit import route accessed; use Google Health instead")
    from ..db.database import save_ride
    from ..ingestion.google_fit import fetch_cycling_activities, google_fit_to_ride
    from ..ingestion.google_oauth_store import get_valid_google_token, store_google_token

    athlete_id = _current_athlete_id(current_user)

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
    """Compute performance, endurance, efficiency scores and experience level."""
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
    """Compare a ride against benchmark data for the athlete's level."""
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
    """Return knowledge base statistics (topics, chunks, word counts)."""
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
    """Semantic search over the cycling knowledge base.

    Returns matching chunks, an LLM-formatted context string, and
    metadata about the search results.
    """
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
    """Return knowledge base statistics for the authenticated user."""
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
    """Hot-reload the knowledge base from disk. Admin only."""
    from ..analytics.knowledge_base import reload_kb

    return reload_kb()


@router.post("/knowledge/init-embeddings")
async def init_kb_embeddings_endpoint(current_user: dict = Depends(get_admin_user)):
    """Initialize embeddings for the knowledge base in PostgreSQL and ChromaDB."""
    from ..analytics.knowledge_base import init_chroma_db, init_kb_embeddings
    from ..db.postgres_db import get_session

    try:
        with get_session() as session:
            pg_result = init_kb_embeddings(session)
    except RuntimeError as exc:
        logger.warning("init-embeddings: PostgreSQL unavailable (%s)", exc)
        raise HTTPException(status_code=500, detail="PostgreSQL not configured") from exc

    chroma_result = init_chroma_db()

    return {"pgvector": pg_result, "chromadb": chroma_result}


@router.get("/coach/workout")
@limiter.limit("10/minute")
async def workout_recommendations(
    request: Request,
    athlete_id: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """Get AI-generated workout recommendations for an athlete."""
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
    """Generate a full AI coach report (training, recovery, historical analysis).

    The report includes training advice, recovery advice, historical
    trends, training scores, and recovery scores. Rate limited.
    """
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
    """Serve the AI Coach static HTML page."""
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
    """Get AI recovery recommendations based on fatigue and recent rides."""
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
            rides = get_rides_by_athlete(_current_athlete_id(current_user), tenant_id)
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
    """Analyze historical training trends for the athlete."""
    from ..analytics.ai_coach import analyze_historical_trends
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(_current_athlete_id(current_user), tenant_id)]
    return analyze_historical_trends(rides)


# ---------------------------------------------------------------------------
# Proactive Assistant — notifications, context evaluation, preferences
# ---------------------------------------------------------------------------


@router.get("/notifications")
async def list_notifications(
    request: Request,
    athlete_id: int = 0,
    category: str | None = Query(default=None, description="Filter by category"),
    current_user: dict = Depends(get_current_user),
):
    """Evaluate pending notifications for the athlete and return those worth sending.

    The decision pipeline runs ContextEvaluator -> SmartTiming -> NotificationRouter
    against a set of candidate signals derived from the athlete's current state,
    plan and (optional) live ride context supplied via query params.
    """
    from ..analytics.proactive import (
        NotificationCategory,
        NotificationContext,
        NotificationPreferences,
        NotificationRouter,
    )

    resolved_id = athlete_id if athlete_id else current_user["id"]
    if resolved_id:
        _ensure_athlete_access(resolved_id, current_user)

    # Candidate signals are built from the athlete's state/plan when available.
    # In normal mode this runs in the background; live signals come from the
    # tracking store on the device. Keep the endpoint stateless & safe.
    prefs = NotificationPreferences()
    router = NotificationRouter(prefs)

    intensity_zone = None
    try:
        z = int(request.query_params.get("intensity_zone", ""))
        if 0 <= z <= 5:
            intensity_zone = z
    except (TypeError, ValueError):
        pass

    plan: dict = {}
    if request.query_params.get("planned_today") == "1":
        plan["planned_today"] = True
    if request.query_params.get("goal_active") == "1":
        plan["goal_active"] = True

    athlete_state: dict = {}
    try:
        tsb = float(request.query_params.get("tsb", ""))
        athlete_state["tsb"] = tsb
    except (TypeError, ValueError):
        pass

    context = NotificationContext(
        athlete_state=athlete_state,
        plan=plan or None,
        intensity_zone=intensity_zone,
    )

    candidates = [
        (
            NotificationCategory.SAFETY.value,
            "stopped",
            {"minutes": int(request.query_params.get("stopped_min", 0)) or 10},
            {"stopped_minutes": int(request.query_params.get("stopped_min", 0)) or 10},
        ),
        (
            NotificationCategory.RECOVERY.value,
            "intense_yesterday",
            {},
            {"insufficient_recovery": (athlete_state.get("tsb", 0) < -15)},
        ),
        (
            NotificationCategory.TRAINING.value,
            "weather_changed",
            {"plan": "2 ore di fondo"},
            {"plan_changed": bool(request.query_params.get("weather_changed") == "1")},
        ),
        (
            NotificationCategory.GOAL.value,
            "granfondo_countdown",
            {"n": int(request.query_params.get("rides_left", 0)) or 3},
            {},
        ),
    ]

    notifications: list = []
    for cat, key, variables, signals in candidates:
        if category and cat != category:
            continue
        n = router.route(
            context,
            cat,
            key,
            variables,
            signals=signals,
        )
        if n is not None:
            notifications.append(n)

    batched = NotificationRouter.batch(notifications, prefs.language) if notifications else None
    out = [batched] if batched else []
    return NotificationListOut(
        notifications=[NotificationOut(**_to_notification_dict(n)) for n in out],
        meta={"candidate_count": len(candidates), "language": prefs.language},
    )


@router.post("/notifications/preferences")
async def update_notification_preferences(
    prefs: NotificationPreferences,
    athlete_id: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """Persist athlete notification preferences (Proactive Assistant).

    Preferences are stored per-user; in this build they are echoed back after
    validation. A full persistence layer can be wired to the async session
    factory or local SQLite without changing this contract.
    """
    resolved_id = athlete_id if athlete_id else current_user["id"]
    if resolved_id:
        _ensure_athlete_access(resolved_id, current_user)
    # Validate via round-trip; the dataclass normalizes channels/language.
    from ..analytics.proactive import NotificationPreferences as PrefModel

    normalized = PrefModel.from_dict(prefs.model_dump())
    return {
        "athlete_id": resolved_id,
        "preferences": normalized.__dict__,
        "message": "Notification preferences saved.",
    }


@router.post("/notifications/evaluate", response_model=NotificationScoreOut)
async def evaluate_notification(
    payload: NotificationContextIn,
    category: str = Query("training"),
    current_user: dict = Depends(get_current_user),
):
    """Valuta una notifica candidata e restituisce il punteggio di rilevanza."""
    """Evaluate a single candidate notification and return its score."""
    from ..analytics.proactive import (
        ContextEvaluator,
        NotificationContext,
        NotificationPreferences,
    )

    now = None
    if payload.now:
        try:
            now = datetime.fromisoformat(payload.now.replace("Z", "+00:00"))
        except ValueError:
            now = None
    context = NotificationContext(
        athlete_state=payload.athlete_state or {},
        plan=payload.plan,
        current_ride=payload.current_ride,
        weather=payload.weather,
        intensity_zone=payload.intensity_zone,
        now=now or datetime.now(UTC),
    )
    prefs = NotificationPreferences()
    score = ContextEvaluator.evaluate(context, category=category)
    return NotificationScoreOut(
        urgency=score.urgency,
        relevance=score.relevance,
        timeliness=score.timeliness,
        score=score.score,
        should_notify=score.should_notify and not prefs.paused,
        reasons=score.reasons,
    )


def _to_notification_dict(n) -> dict:
    """Converte un modello di notifica in dizionario serializzabile."""
    return {
        "id": n.id,
        "category": n.category,
        "channel": n.channel,
        "title": n.title,
        "message": n.message,
        "tts_text": n.tts_text,
        "score": n.score,
        "priority": n.priority,
        "language": n.language,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("/rides/{ride_id}/map/google")
async def google_static_map(
    ride_id: int,
    colored: bool = Query(False, description="Color path by speed (green=fast, yellow=medium, red=slow)"),
    current_user: dict = Depends(get_current_user),
):
    """Generate a Google Static Maps image for a ride.

    Optionally colors the path by speed (green=fast, yellow=medium,
    red=slow). Requires GOOGLE_MAPS_API_KEY to be configured.
    """
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
    return FileResponse(path, media_type="image/png", filename="map.png", background=BackgroundTask(os.remove, path))


@router.get("/rides/{ride_id}/speed-path")
async def ride_speed_path(
    ride_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Return speed-colored path segments and bounding box for a ride."""
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
    """Create and download a database backup. Admin only."""
    import hashlib
    import logging

    from fastapi.responses import FileResponse

    from ..db.database import backup_database

    path = backup_database()
    file_hash = hashlib.sha256(path.encode()).hexdigest()[:8]
    log_action(
        current_user["id"],
        "download_backup",
        "database",
        details={"file": f"bikemaster_backup_{file_hash}.db", "hash": file_hash},
    )
    logger.info(
        "Admin user=%s downloaded backup file=%s hash=%s",
        current_user["id"],
        path,
        file_hash,
    )
    return FileResponse(path, media_type="application/octet-stream", filename=f"bikemaster_backup_{file_hash}.db")


@admin_router.post("/backup/scheduled")
async def create_scheduled_backup(current_user: dict = Depends(get_admin_user)):
    """Run a scheduled backup rotation (keeps last 10 backups). Admin only."""
    from ..db.database import scheduled_backup

    result = scheduled_backup(max_backups=10)
    log_action(current_user["id"], "scheduled_backup", "database")
    return result


@admin_router.post("/indexes")
async def create_db_indexes(current_user: dict = Depends(get_admin_user)):
    """Create database performance indexes. Admin only."""
    from ..db.database import create_indices

    create_indices()
    log_action(current_user["id"], "create_indexes", "database")
    return {"status": "indexes_created"}


@admin_router.get("/stats")
async def get_system_stats(current_user: dict = Depends(get_admin_user)):
    """Return system-wide statistics (rides, athletes, DB size). Admin only."""
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
    """Delete demo rides and regenerate sample data. Admin only."""
    from ..db.database import delete_ride, get_all_rides

    rides = get_all_rides()
    for r in rides:
        if "demo" in r.get("date", ""):
            delete_ride(r["id"])
    try:
        from scripts.generate_sample_ride import generate_sample_ride
    except ImportError:
        logger.warning("reset_demo: scripts.generate_sample_ride not available; skipping regeneration")
    else:
        generate_sample_ride()
    log_action(current_user["id"], "reset_demo", "system")
    return {"status": "demo_reset", "message": "Demo data regenerated"}


@admin_router.get("/ceo")
async def ceo_analytics(current_user: dict = Depends(get_admin_user)):
    """Return executive-level analytics (growth, engagement, athlete levels). Admin only."""
    from ..db.database import get_all_athletes, get_all_rides

    rides = get_all_rides()
    athletes = get_all_athletes()
    total_rides = len(rides)
    total_athletes = len(athletes)
    total_km = sum(r.get("distance_km", 0) for r in rides)
    total_hours = sum(r.get("duration_minutes", 0) for r in rides) / 60
    total_calories = sum(r.get("calories", 0) for r in rides)
    from datetime import datetime

    now = datetime.now(UTC)
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


@admin_router.get("/users")
async def admin_list_users(current_user: dict = Depends(get_admin_user)):
    """List all users. Admin only."""
    from ..db.database import get_all_users

    users = get_all_users()
    for u in users:
        u.pop("password_hash", None)
    log_action(current_user["id"], "list_users", "users")
    return users


@admin_router.get("/users/{user_id}")
async def admin_get_user(current_user: dict = Depends(get_admin_user), user_id: int = ...):
    """Get a single user. Admin only."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    user.pop("password_hash", None)
    log_action(current_user["id"], "get_user", "users")
    return user


@admin_router.post("/users")
async def admin_create_user(user_data: UserCreate, current_user: dict = Depends(get_admin_user)):
    """Create a new user. Admin only."""
    from ..db.database import get_user_by_username
    from ..security import hash_password

    if get_user_by_username(user_data.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    new_id = save_user(
        {
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": hash_password(user_data.password),
            "is_admin": False,
            "is_client": False,
            "is_active": True,
        }
    )
    log_action(current_user["id"], "create_user", "users")
    user = get_user_by_id(new_id)
    if user:
        user.pop("password_hash", None)
    return user


@admin_router.put("/users/{user_id}")
async def admin_update_user(user_id: int, user_data: UserUpdate, current_user: dict = Depends(get_admin_user)):
    """Update a user. Admin only."""
    from ..db.database import update_user as _update_user

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    updates = user_data.model_dump(exclude_unset=True)
    if "password" in updates:
        from ..security import hash_password

        updates["password_hash"] = hash_password(updates.pop("password"))
    updated = _update_user(user_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    updated.pop("password_hash", None)
    log_action(current_user["id"], "update_user", "users")
    return updated


@admin_router.delete("/users/{user_id}")
async def admin_delete_user(current_user: dict = Depends(get_admin_user), user_id: int = ...):
    """Delete a user. Admin only."""
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Non puoi eliminare te stesso")
    from ..db.database import delete_user as _delete_user

    if not _delete_user(user_id):
        raise HTTPException(status_code=404, detail="Utente non trovato")
    log_action(current_user["id"], "delete_user", "users")
    return {"status": "deleted"}


@admin_router.post("/users/{user_id}/toggle-admin")
async def admin_toggle_admin(current_user: dict = Depends(get_admin_user), user_id: int = ...):
    """Toggle admin status for a user. Admin only."""
    from ..db.database import update_user as _update_user

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    updated = _update_user(user_id, {"is_admin": not user["is_admin"]})
    updated.pop("password_hash", None)
    log_action(current_user["id"], "toggle_admin", "users")
    return updated


@admin_router.post("/users/{user_id}/toggle-client")
async def admin_toggle_client(current_user: dict = Depends(get_admin_user), user_id: int = ...):
    """Toggle client status for a user. Admin only."""
    from ..db.database import update_user as _update_user

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    updated = _update_user(user_id, {"is_client": not user["is_client"]})
    updated.pop("password_hash", None)
    log_action(current_user["id"], "toggle_client", "users")
    return updated


@admin_router.post("/users/{user_id}/toggle-active")
async def admin_toggle_active(current_user: dict = Depends(get_admin_user), user_id: int = ...):
    """Toggle active status for a user. Admin only."""
    from ..db.database import update_user as _update_user

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    updated = _update_user(user_id, {"is_active": not user["is_active"]})
    updated.pop("password_hash", None)
    log_action(current_user["id"], "toggle_active", "users")
    return updated


@router.put("/rides/{ride_id}")
async def update_ride(ride_id: int, ride: RideUpdate, current_user: dict = Depends(get_current_user)):
    """Update a ride's mutable fields. Protected fields (id, athlete_id, created_at) are ignored."""
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


@router.post("/coach/chat")
async def coach_chat_post(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Send a message to the AI coach via POST (JSON body)."""

    body = await request.json()
    chat_req = CoachChatRequest(**body)
    athlete_id = chat_req.athlete_id or current_user["id"]
    return await _process_chat(athlete_id, chat_req.message, current_user)


async def _process_chat(athlete_id: int, message: str, current_user: dict):
    """Gestisce la chat con l'AI coach: salva messaggi, genera consigli e restituisce la storia."""
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


@router.post("/coach/chat/bm2")
async def coach_chat_bm2(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """AI Coach chat with BM2 physics engine integration.

    Combines the AI coach's training advice with BM2 simulation
    and power validation results for a comprehensive analysis.
    """
    from bike_analyzer.bm2.orchestrator import AIOrchestrator
    from bike_analyzer.core.physics import RiderBikeParams, validate_ride_power

    from ..analytics.ai_coach import generate_training_advice
    from ..db.database import get_athlete, get_chat_history, get_rides_by_athlete, save_chat_message
    from ..models.models import AthleteProfile, Ride

    body = await request.json()
    chat_req = CoachChatRequest(**body)
    athlete_id = chat_req.athlete_id or current_user["id"]
    tenant_id = current_user.get("tenant_id", athlete_id)
    _ensure_athlete_access(athlete_id, current_user)

    # Generate coach advice
    athlete_data = get_athlete(athlete_id, tenant_id)
    if athlete_data:
        athlete_data = {k: v for k, v in athlete_data.items() if k != "password_hash"}
    athlete = AthleteProfile(**_athlete_profile_data(athlete_data)) if athlete_data else AthleteProfile()
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id, tenant_id=tenant_id)]
    coach_response = generate_training_advice(athlete, rides, athlete_id)

    message = chat_req.message

    # Save chat only if athlete exists (FK constraint)
    def _save_chat(role, content):
        if athlete_data:
            with contextlib.suppress(Exception):
                save_chat_message(athlete_id, role, content[:500], tenant_id)

    _save_chat("user", message)
    response_text = coach_response
    bm2_result = None
    ride_id_match = None
    import re as _re
    ride_id_match = _re.search(r"ride\s*#?(\d+)|ride\s+(\d+)", message, _re.IGNORECASE)
    if ride_id_match:
        rid = int(ride_id_match.group(1) or ride_id_match.group(2))
        from ..db.database import get_ride as _get_ride
        from .bm2_routes import _to_gps
        ride_dict = _get_ride(rid)
        if ride_dict:
            try:
                gps = [_to_gps(p) for p in (ride_dict.get("gps_points") or [])]
                ride = Ride(**{k: v for k, v in ride_dict.items() if k in Ride.__dataclass_fields__})
                ride.gps_points = gps
                params = RiderBikeParams(
                    rider_mass_kg=float(athlete.weight_kg.value) if athlete.weight_kg else 75.0,
                    bike_mass_kg=8.0,
                    cda=0.40,
                    crr=0.005,
                    drivetrain_efficiency=0.97,
                )
                validation = validate_ride_power(ride, params)
                if validation:
                    bm2_result = {
                        "validation": validation.to_dict(),
                        "ride_id": rid,
                    }
            except Exception:
                pass

    # Also run a general BM2 ask if the question is about energy/performance
    if not bm2_result and any(kw in message.lower() for kw in ["energia", "power", "ftp", "performance", "calories", "kcal"]):
        try:
            orchestrator = AIOrchestrator()
            bm2_result = orchestrator.answer(message, {
                "athlete": {"weight": athlete.weight_kg.value if athlete.weight_kg else 75},
                "bike": {"weight": 8},
                "world": {"surface": "asphalt", "avg_slope": 4},
                "gps_points": [],
                "sensors": [],
            })
        except Exception:
            pass

    response_text = coach_response
    if bm2_result:
        response_text += "\n\n---\n**BM2 Physics Analysis:**\n"
        if "validation" in bm2_result:
            v = bm2_result["validation"]
            response_text += f"- MAE: {v['mae_w']:.1f}W | RMSE: {v['rmse_w']:.1f}W | R²: {v['r2']:.3f}\n"
        if "results" in bm2_result:
            for name, r in bm2_result["results"].items():
                response_text += f"- {name}: {r['value']:.1f} {r['unit']}\n"

    _save_chat("assistant", response_text)
    return {
        "response": response_text,
        "history": get_chat_history(athlete_id, tenant_id=tenant_id),
        "bm2_result": bm2_result,
    }


@router.get("/analytics/speed-data")
async def speed_analytics(limit: int = Query(10, ge=1, le=50), current_user: dict = Depends(get_current_user)):
    """Return recent ride speed data for charting."""
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = get_rides_by_athlete(_current_athlete_id(current_user), tenant_id)
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
    """Find nearby places for a ride using OSM or SerpApi.

    Results are cached in-memory for 10 minutes.
    """
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
    """OpenStreetMap Nominatim search for places. No API key required."""
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
    """Search for places near a ride using SerpApi (requires API key)."""
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
    """Create a calendar event for an athlete."""
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
    """List calendar events for an athlete in a given month."""
    from ..db.database import get_events_by_month

    is_admin = current_user.get("is_admin", False)
    tenant_id = current_user.get("tenant_id", athlete_id) if not is_admin else None
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
    """List calendar events for an athlete within a date range."""
    from ..db.database import get_events_by_date_range

    is_admin = current_user.get("is_admin", False)
    tenant_id = current_user.get("tenant_id", athlete_id) if not is_admin else None
    _ensure_athlete_access(athlete_id, current_user)
    events = get_events_by_date_range(athlete_id, start, end, tenant_id)
    return {"events": events}


@router.get("/calendar/events/{event_id}")
async def get_calendar_event_endpoint(event_id: int, current_user: dict = Depends(get_current_user)):
    """Get a single calendar event by ID."""
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
    """Update a calendar event. Only the owner can modify."""
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
    """Delete a calendar event. Only the owner can delete."""
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
    """Toggle the completed flag on a calendar event."""
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
    """Return ATL/CTL/TSB training load metrics for the last N days."""
    from ..analytics.training_load import calculate_atl_ctl_tsb
    from ..db.database import get_rides_by_athlete

    # Users can only see their own training load (admin can see all)
    _ensure_athlete_access(athlete_id, current_user)
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id)]
    loads = await asyncio.to_thread(calculate_atl_ctl_tsb, rides)
    recent = loads[-days:] if len(loads) > days else loads
    return {"athlete_id": athlete_id, "days": days, "training_loads": list(recent)}


@router.get("/training/status")
async def get_training_status(athlete_id: int = Query(...), current_user: dict = Depends(get_current_user)):
    """Return current fitness status with ATL/CTL/TSB-based recommendation."""
    from ..analytics.training_load import get_current_training_status
    from ..db.database import get_rides_by_athlete

    # Users can only see their own training status (admin can see all)
    _ensure_athlete_access(athlete_id, current_user)
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id)]
    status = await asyncio.to_thread(get_current_training_status, rides)
    return {"athlete_id": athlete_id, **status}


@router.get("/training/summary")
async def get_7day_summary(athlete_id: int = Query(...), current_user: dict = Depends(get_current_user)):
    """Return a 7-day fitness summary for the dashboard."""
    from ..analytics.training_load import get_7day_fitness_summary
    from ..db.database import get_rides_by_athlete

    # Users can only see their own summary (admin can see all)
    _ensure_athlete_access(athlete_id, current_user)
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id)]
    summary = await asyncio.to_thread(get_7day_fitness_summary, rides)
    return {"athlete_id": athlete_id, "summary": summary}


@router.post("/training/goals")
async def create_training_goal(goal_data: dict, current_user: dict = Depends(get_current_user)):
    """Create a training goal for an athlete (requires PostgreSQL)."""
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

    from ..analytics.training_load import get_current_training_status
    from ..db.database import get_rides_by_athlete
    from ..db.postgres_db import TrainingGoalModel, get_session
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

    from ..analytics.athlete_state.service import AthleteStateService

    athlete_state_service = AthleteStateService()
    athlete_state = await athlete_state_service.calculate_current_state(
        athlete_id=goal.athlete_id,
        rides=rides,
    )

    from datetime import datetime as dt

    from ..analytics.training.models import PlanConstraints, TrainingGoal
    from ..analytics.training.workout_generator import WorkoutGenerator

    goal_type_map = {
        "granfondo": "granfondo",
        "race": "race",
        "fitness": "maintenance",
        "fondo": "granfondo",
        "custom": "maintenance",
    }
    goal_type_str = goal_type_map.get(goal.goal_type, "maintenance")
    try:
        goal_enum = __import__("bike_analyzer.backend.analytics.training.models", fromlist=["GoalType"]).GoalType(goal_type_str)
    except Exception:
        goal_enum = __import__("bike_analyzer.backend.analytics.training.models", fromlist=["GoalType"]).GoalType.MAINTENANCE

    training_goal = TrainingGoal(
        goal_type=goal_enum,
        target_date=goal.target_date,
        target_distance_km=goal.target_distance_km,
        description=goal.description or "",
    )
    constraints = PlanConstraints(days_per_week=4, hours_per_session=1.5)

    generator = WorkoutGenerator(athlete=None, ftp=250.0)
    workouts = generator.generate_for_week(
        goal=training_goal,
        constraints=constraints,
        start_date=dt.now(),
        fitness_tss=athlete_state.weekly_tss,
        fatigue_score=athlete_state.fatigue_score,
    )

    return {
        "generated": len(workouts),
        "goal_id": goal_id,
        "athlete_state": athlete_state.to_dict(),
    }



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
    days: int = Query(7, ge=1, le=7),
):
    """Get multi-day weather forecast."""
    from datetime import UTC, datetime, timedelta

    from ..weather.weather_service import get_forecast_for_date, get_weather_score

    if not _s.weather_api_key:
        raise HTTPException(status_code=500, detail="WEATHER_API_KEY not configured in .env file")

    forecasts = []
    today = datetime.now(UTC)

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


@router.get("/weather/geocode")
async def geocode_city(
    city: str = Query(..., description="City name"),
):
    """Convert city name to coordinates."""
    from ..weather.weather_service import get_city_coordinates

    result = get_city_coordinates(city)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


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
    rides = [Ride(**r) for r in get_rides_by_athlete(_current_athlete_id(current_user), tenant_id)]
    return await asyncio.to_thread(calculate_fitness_trends, rides, metric=metric, window=window)


@router.get("/analytics/monthly")
async def get_monthly_progression(current_user: dict = Depends(get_current_user)):
    """Get monthly aggregated metrics for athlete's rides."""
    from ..analytics.analytics_trends import calculate_monthly_progression
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = get_rides_by_athlete(_current_athlete_id(current_user), tenant_id)
    return await asyncio.to_thread(calculate_monthly_progression, rides)


@router.get("/analytics/comparison")
async def get_period_comparison(
    period_days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
):
    """Compare recent vs previous period for athlete's rides."""
    from ..analytics.analytics_trends import calculate_period_comparison
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(_current_athlete_id(current_user), tenant_id)]
    return await asyncio.to_thread(calculate_period_comparison, rides, period_days=period_days)


@router.get("/analytics/zones")
async def get_zone_distributions(
    current_user: dict = Depends(get_current_user),
):
    """Aggregate power & heart-rate time-in-zone distributions.

    Builds the data behind the frontend "Training Zones" charts from
    the athlete's stored ride GPS samples. FTP and max HR are taken
    from the athlete profile when available, otherwise sensible defaults.
    """
    from ..analytics.zone_analysis import calculate_zone_distributions
    from ..db.database import get_athlete, get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    athlete = get_athlete(athlete_id, tenant_id) or {}
    ftp = athlete.get("ftp_watts")
    max_hr = athlete.get("heart_rate_avg")
    rides = get_rides_by_athlete(athlete_id, tenant_id)
    return await asyncio.to_thread(calculate_zone_distributions, rides, ftp_watts=ftp, max_hr=max_hr)


@router.get("/analytics/projection")
async def get_volume_projection(
    target_days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Project future training volume based on historical trend for athlete's rides."""
    from ..analytics.analytics_trends import calculate_training_volume_projection
    from ..db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(_current_athlete_id(current_user), tenant_id)]
    return await asyncio.to_thread(calculate_training_volume_projection, rides, target_days=target_days)


@router.get("/heatmap")
async def get_heatmap(athlete_id: int = Query(0), current_user: dict = Depends(get_current_user)):
    """Get heatmap data from all GPS points for an athlete."""
    from ..db.database import get_rides_by_athlete

    if athlete_id and current_user.get("is_admin"):
        target_id = athlete_id
        _ensure_athlete_access(athlete_id, current_user)
    else:
        target_id = current_user["id"]
    rides = [Ride(**r) for r in get_rides_by_athlete(target_id)]
    rides_dict = []
    for r in rides:
        d = r.to_dict()
        gps = getattr(r, "gps_points", None)
        if gps:
            d["gps_points"] = [
                {
                    "lat": p.lat,
                    "lon": p.lon,
                    "altitude": p.altitude,
                    "speed": p.speed,
                    "power": p.power,
                    "heart_rate": p.heart_rate,
                    "cadence": p.cadence,
                    "timestamp": p.timestamp.isoformat() if p.timestamp else None,
                }
                for p in gps
            ]
        rides_dict.append(d)
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
    results = await asyncio.to_thread(classify_rides, rides)
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
    result = await asyncio.to_thread(estimate_vip, rides, athlete_ftp=ftp)
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
    result = await asyncio.to_thread(estimate_inactivity, rides)
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
    suggestions = await asyncio.to_thread(estimate_route_preferences, athlete, rides)
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
    metrics = await asyncio.to_thread(calculate_advanced_power_metrics, points, ftp=ftp)
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


def _strava_redirect_uri_for(request: Request, redirect_uri: str | None = None) -> str:
    """Resolve the Strava OAuth redirect URI.

    If an explicit ``redirect_uri`` is provided (e.g. from the frontend
    query params) it is used directly.  Otherwise falls back to the
    configured ``STRAVA_REDIRECT_URI`` env var, and finally to computing
    the URI from the request host so it always matches what Strava expects.
    """
    if redirect_uri:
        return redirect_uri
    if _s.strava_redirect_uri:
        return _s.strava_redirect_uri
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if not host:
        raise HTTPException(status_code=500, detail="Strava redirect URI not configured and no host detected")
    host_lower = host.lower()
    if (
        host_lower.endswith(".ngrok-free.dev")
        or host_lower.endswith(".vercel.app")
        or host_lower.endswith(".onrender.com")
    ):
        proto = "https"
    return f"{proto}://{host}/api/v1/import/strava/callback"


@router.get("/import/strava/auth")
async def strava_auth(
    request: Request,
    state: str = "",
    redirect_uri: str = "",
    current_user: dict = Depends(get_current_user),
):
    """Avvia il flusso OAuth Strava restituendo l'URL di autorizzazione."""
    from ..ingestion.strava_client import get_authorization_url

    resolved_redirect_uri = _strava_redirect_uri_for(request, redirect_uri or None)
    user_creds = _get_user_oauth_creds(int(current_user["id"]), "strava")
    try:
        result = get_authorization_url(
            state=state,
            redirect_uri=resolved_redirect_uri,
            client_id=(user_creds or {}).get("client_id"),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    oauth_state = result.get("state", "")
    if oauth_state:
        await _store_oauth_state(oauth_state, int(current_user["id"]), "strava")
    logger.debug(
        "Strava auth redirect_uri=%s", resolved_redirect_uri
    )
    result["athlete_id"] = current_user["id"]
    return result


@router.get("/import/strava/callback")
async def strava_callback_page(
    request: Request,
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
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    allowed_origin = None
    if origin:
        parsed_origin = urlparse(origin)
        origin_host = (parsed_origin.scheme or "https") + "://" + parsed_origin.netloc
        allowed_origins = _s.cors_origins_list if hasattr(_s, "cors_origins_list") else []
        if origin_host in allowed_origins or parsed_origin.netloc.endswith(".vercel.app"):
            allowed_origin = origin_host

    if error:
        return _strava_message_html(
            {
                "type": "strava-error",
                "error": error,
                "error_description": error_description or "Strava OAuth failed",
            },
            status_code=400,
            allowed_origin=allowed_origin,
        )
    if not code:
        return _strava_message_html(
            {
                "type": "strava-error",
                "error": "missing_code",
                "error_description": "Strava callback received without code",
            },
            status_code=400,
            allowed_origin=allowed_origin,
        )
    if not state:
        return _strava_message_html(
            {
                "type": "strava-error",
                "error": "missing_state",
                "error_description": "Strava callback missing state parameter",
            },
            status_code=400,
            allowed_origin=allowed_origin,
        )
    return _strava_message_html({"type": "strava-success", "code": code, "state": state}, allowed_origin=allowed_origin)


@router.post("/import/strava/callback")
async def strava_callback(
    payload: StravaCallbackRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Gestisce il callback OAuth Strava: scambia il codice per token e lo memorizza."""
    from ..ingestion.strava_client import exchange_code_for_token, store_token

    code = payload.code
    code_verifier = payload.code_verifier
    oauth_state = payload.state
    if not oauth_state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")
    user_id = int(current_user["id"])
    if not await _consume_oauth_state(oauth_state, "strava", user_id):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    redirect_uri = _strava_redirect_uri_for(request)
    user_creds = _get_user_oauth_creds(int(current_user["id"]), "strava")
    logger.debug("Strava token exchange redirect_uri=%s", redirect_uri)
    try:
        token_data = await exchange_code_for_token(
            code,
            code_verifier,
            redirect_uri=redirect_uri,
            client_id=(user_creds or {}).get("client_id"),
            client_secret=(user_creds or {}).get("client_secret"),
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail="Strava token exchange failed. Please try again later.",
        ) from exc
    store_token(_current_athlete_id(current_user), token_data)
    return {
        "status": "connected",
        "athlete_id": _current_athlete_id(current_user),
        "athlete_name": token_data.get("athlete", {}).get("firstname", ""),
    }


@router.post("/import/strava/sync")
async def strava_sync(
    background: bool = True,
    current_user: dict = Depends(get_current_user),
):
    """Sync Strava activities in background or synchronous mode, handling rate limits."""
    import time

    from ..task_queue import get_task_queue

    payload = {"athlete_id": _current_athlete_id(current_user)}
    if background:
        task = await get_task_queue().enqueue("strava_sync", payload)
        return {"task_id": task.id, "status": "queued", "athlete_id": _current_athlete_id(current_user)}
    from ..db.database import save_ride
    from ..ingestion.strava_client import (
        StravaRateLimitError,
        fetch_all_activities,
        get_last_sync_ts,
        get_valid_token,
        set_last_sync_ts,
        strava_to_ride,
        strava_to_ride_with_streams,
    )

    user_creds = _get_user_oauth_creds(int(current_user["id"]), "strava")
    access_token = await get_valid_token(
        current_user["id"],
        client_id=(user_creds or {}).get("client_id"),
        client_secret=(user_creds or {}).get("client_secret"),
    )
    if not access_token:
        raise HTTPException(
            status_code=403,
            detail="Strava token expired or not connected. Please reconnect in Settings.",
            headers={"X-Auth-Error": "oauth_expired"},
        )
    last_sync = get_last_sync_ts(current_user["id"])
    sync_ts = int(time.time())
    try:
        activities = await fetch_all_activities(access_token, after=last_sync)
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Strava API error. Please try again later.") from None
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
    set_last_sync_ts(current_user["id"], sync_ts)
    return {"imported": len(imported), "total_fetched": len(activities), "rides": imported}


@router.delete("/import/strava/disconnect")
async def strava_disconnect(current_user: dict = Depends(get_current_user)):
    """Revoke the Strava OAuth token for the current user."""
    from ..ingestion.strava_client import revoke_token

    revoke_token(current_user["id"])
    return {"status": "disconnected"}


@router.delete("/import/google-fit/disconnect")
async def google_fit_disconnect(current_user: dict = Depends(get_current_user)):
    """Delete the Google Fit token (deprecated) for the current user."""
    logger.warning("Deprecated Google Fit disconnect route accessed; use Google Health instead")
    from ..ingestion.google_oauth_store import delete_google_token

    delete_google_token(int(current_user["id"]), "google_fit")
    return {"status": "disconnected"}


@router.delete("/import/google-health/disconnect")
async def google_health_disconnect(current_user: dict = Depends(get_current_user)):
    """Delete the Google Health token for the current user."""
    from ..ingestion.google_oauth_store import delete_google_token

    delete_google_token(int(current_user["id"]), "google_health")
    return {"status": "disconnected"}


# ------------------------------------------------------------------
# BLE device management
# ------------------------------------------------------------------


@router.get("/ble/devices")
async def list_ble_devices(current_user: dict = Depends(get_current_user)):
    """List all BLE devices registered for the current athlete."""
    from ..db.database import get_ble_devices

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    devices = get_ble_devices(athlete_id, tenant_id=tenant_id)
    return {"devices": [BleDeviceOut.model_validate(d).model_dump() for d in devices]}


@router.post("/ble/devices")
async def register_ble_device(current_user: dict = Depends(get_current_user), payload: BleDeviceRegister = Body(...)):
    """Register a new BLE device (or update if already known)."""
    from ..db.database import register_ble_device

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    device_id = register_ble_device(
        athlete_id=athlete_id,
        device_id=payload.device_id,
        name=payload.name,
        tenant_id=tenant_id,
        device_type=payload.device_type,
        service_uuid=payload.service_uuid,
        characteristic_uuid=payload.characteristic_uuid,
        mac_address=payload.mac_address,
    )
    return {"id": device_id, "device_id": payload.device_id, "name": payload.name}


@router.put("/ble/devices/{device_id}")
async def update_ble_device(current_user: dict = Depends(get_current_user), device_id: int = ..., payload: BleDeviceUpdate = ...):
    """Update a BLE device (name, paired status, settings)."""
    from ..db.database import get_ble_device, update_ble_device

    athlete_id = _current_athlete_id(current_user)
    existing = get_ble_device(device_id, athlete_id)
    if not existing:
        raise HTTPException(status_code=404, detail="BLE device not found")
    update_data = payload.model_dump(exclude_none=True)
    updated = update_ble_device(device_id, athlete_id, **update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="BLE device not found")
    return BleDeviceOut.model_validate(updated).model_dump()


@router.delete("/ble/devices/{device_id}")
async def delete_ble_device(current_user: dict = Depends(get_current_user), device_id: int = ...):
    """Unregister (delete) a BLE device."""
    from ..db.database import get_ble_device, unregister_ble_device

    athlete_id = _current_athlete_id(current_user)
    existing = get_ble_device(device_id, athlete_id)
    if not existing:
        raise HTTPException(status_code=404, detail="BLE device not found")
    unregister_ble_device(device_id, athlete_id)
    return {"status": "deleted", "id": device_id}


@router.post("/ble/devices/{device_id}/sync")
async def sync_ble_device(
    current_user: dict = Depends(get_current_user),
    device_id: int = ...,
    payload: BleDeviceSync | None = Body(default=None),
):
    """Trigger a sync/read from a BLE device. Frontend provides the data."""
    from ..db.database import get_ble_device, log_athlete_metric, mark_ble_device_synced

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    existing = get_ble_device(device_id, athlete_id)
    if not existing:
        raise HTTPException(status_code=404, detail="BLE device not found")
    device_type = existing.get("device_type", "generic")
    note = f"ble:{existing.get('device_id', '')}"
    has_value = payload is not None and payload.value is not None
    unit = payload.unit if payload else None
    if device_type == "weight_scale":
        metric_type = "weight_kg" if unit != "lb" else "weight_lb"
        unit = unit or "kg"
    elif device_type == "heart_rate":
        metric_type = "heart_rate_bpm"
        unit = unit or "bpm"
    elif device_type == "blood_pressure":
        metric_type = "blood_pressure_systolic"
        unit = unit or "mmHg"
    else:
        metric_type = "ble_generic"
        unit = unit or "value"
    metric_id = 0
    if has_value:
        metric_id = log_athlete_metric(
            athlete_id=athlete_id,
            metric_type=metric_type,
            value=payload.value,
            tenant_id=tenant_id,
            unit=unit,
            note=note,
            source="ble",
            recorded_at=payload.recorded_at,
        )
    mark_ble_device_synced(device_id, athlete_id)
    return {
        "status": "synced",
        "device_id": device_id,
        "type": device_type,
        "metric_id": metric_id,
    }


# ------------------------------------------------------------------
# Garmin integration routes
# ------------------------------------------------------------------


@router.get("/import/garmin/auth")
async def garmin_auth(
    request: Request,
    state: str = "",
    current_user: dict = Depends(get_current_user),
):
    """Start the Garmin OAuth flow, returning the authorization URL."""
    from ..ingestion.garmin_client import get_authorization_url

    oauth_state = state or _generate_oauth_state()
    try:
        result = get_authorization_url(state=oauth_state)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    await _store_oauth_state(oauth_state, _current_athlete_id(current_user), "garmin")
    result["athlete_id"] = _current_athlete_id(current_user)
    return result


@router.post("/import/garmin/callback")
async def garmin_callback(
    payload: GarminCallbackRequest,
    current_user: dict = Depends(get_current_user),
):
    """Handle the Garmin OAuth callback: exchange code for token and store it."""
    from ..ingestion.garmin_client import exchange_code_for_token, store_token

    code = payload.code
    redirect_uri = payload.redirect_uri
    oauth_state = getattr(payload, 'state', None)
    if not oauth_state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")
    user_id = _current_athlete_id(current_user)
    if not await _consume_oauth_state(oauth_state, "garmin", user_id):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    try:
        token_data = await exchange_code_for_token(code, redirect_uri=redirect_uri or "")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Garmin token exchange failed: {exc}") from exc
    store_token(user_id, token_data)
    return {"status": "connected", "athlete_id": user_id}


@router.post("/import/garmin/sync")
async def garmin_sync(
    background: bool = True,
    current_user: dict = Depends(get_current_user),
):
    """Sync Garmin activities, optionally in background, and save rides."""
    from ..task_queue import get_task_queue

    payload = {"athlete_id": _current_athlete_id(current_user)}
    if background:
        task = await get_task_queue().enqueue("garmin_sync", payload)
        return {"task_id": task.id, "status": "queued", "athlete_id": current_user["id"]}
    from ..db.database import save_ride
    from ..ingestion.garmin_client import fetch_activities, garmin_to_ride, get_valid_token

    access_token = await get_valid_token(_current_athlete_id(current_user))
    if not access_token:
        raise HTTPException(
            status_code=403,
            detail="Garmin token expired or not connected. Please reconnect in Settings.",
            headers={"X-Auth-Error": "oauth_expired"},
        )
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
    """Revoke the Garmin OAuth token for the current user."""
    from ..ingestion.garmin_client import revoke_token

    revoke_token(current_user["id"])
    return {"status": "disconnected"}


@router.get("/import/providers")
async def list_import_providers():
    """Return the configuration of available import providers."""
    return {
        "google_fit": bool(_s.google_fit_client_id and _s.google_fit_client_secret),
        "google_health": bool(_s.google_health_client_id and _s.google_health_client_secret),
        "wahoo": bool(_s.wahoo_client_id and _s.wahoo_client_secret),
        "strava": bool(_s.strava_client_id and _s.strava_client_secret),
        "ble": True,
        "health_connect": True,
        "hr_24h": True,
    }


# ------------------------------------------------------------------
# Wahoo integration routes
# ------------------------------------------------------------------


@router.get("/import/wahoo/auth")
async def wahoo_auth(
    request: Request,
    state: str = "",
    current_user: dict = Depends(get_current_user),
):
    """Avvia il flusso OAuth Wahoo restituendo l'URL di autorizzazione."""
    from ..ingestion.wahoo_client import get_authorization_url

    oauth_state = state or _generate_oauth_state()
    user_creds = _get_user_oauth_creds(int(current_user["id"]), "wahoo")
    try:
        result = get_authorization_url(
            state=oauth_state,
            client_id=(user_creds or {}).get("client_id"),
            redirect_uri=(user_creds or {}).get("redirect_uri"),
            scope=(user_creds or {}).get("scope"),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    await _store_oauth_state(oauth_state, int(current_user["id"]), "wahoo")
    result["athlete_id"] = current_user["id"]
    return result


@router.post("/import/wahoo/callback")
async def wahoo_callback(
    payload: WahooCallbackRequest,
    current_user: dict = Depends(get_current_user),
):
    """Gestisce il callback OAuth Wahoo: scambia il codice per token e lo memorizza."""
    from ..ingestion.wahoo_client import exchange_code_for_token, store_token

    code = payload.code
    code_verifier = payload.code_verifier
    oauth_state = payload.state
    if not oauth_state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")
    user_id = int(current_user["id"])
    if not await _consume_oauth_state(oauth_state, "wahoo", user_id):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    user_creds = _get_user_oauth_creds(user_id, "wahoo")
    try:
        token_data = exchange_code_for_token(
            code,
            code_verifier,
            client_id=(user_creds or {}).get("client_id"),
            client_secret=(user_creds or {}).get("client_secret"),
            redirect_uri=(user_creds or {}).get("redirect_uri"),
        )
    except requests.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Wahoo token exchange failed: {exc}") from exc
    store_token(user_id, token_data, code_verifier=code_verifier)
    return {
        "status": "connected",
        "athlete_id": _current_athlete_id(current_user),
        "athlete_name": "",
    }


@router.post("/import/wahoo/sync")
async def wahoo_sync(
    background: bool = True,
    current_user: dict = Depends(get_current_user),
):
    """Sync Wahoo workouts and save the corresponding rides."""
    from ..task_queue import get_task_queue

    payload = {"athlete_id": _current_athlete_id(current_user)}
    if background:
        task = await get_task_queue().enqueue("wahoo_sync", payload)
        return {"task_id": task.id, "status": "queued", "athlete_id": current_user["id"]}
    from ..db.database import save_ride
    from ..ingestion.wahoo_client import fetch_workouts, get_valid_token, wahoo_to_ride

    user_creds = _get_user_oauth_creds(int(current_user["id"]), "wahoo")
    access_token = get_valid_token(
        current_user["id"],
        client_id=(user_creds or {}).get("client_id"),
        client_secret=(user_creds or {}).get("client_secret"),
    )
    if not access_token:
        raise HTTPException(
            status_code=403,
            detail="Wahoo token expired or not connected. Please reconnect in Settings.",
            headers={"X-Auth-Error": "oauth_expired"},
        )
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
    """Revoca il token OAuth Wahoo per l'utente corrente."""
    from ..ingestion.wahoo_client import revoke_token

    revoke_token(current_user["id"])
    return {"status": "disconnected"}


# ------------------------------------------------------------------
# Android Health Connect integration routes
# ------------------------------------------------------------------


@router.post("/health-connect/connect")
async def health_connect_connect(current_user: dict = Depends(get_current_user)):
    """Connect Android Health Connect for the current athlete."""
    from ..ingestion.health_connect import connect

    result = connect(current_user["id"])
    return result


@router.post("/health-connect/disconnect")
async def health_connect_disconnect(current_user: dict = Depends(get_current_user)):
    """Disconnect Android Health Connect for the current athlete."""
    from ..ingestion.health_connect import disconnect

    disconnect(current_user["id"])
    return {"status": "disconnected"}


@router.post("/health-connect/sync")
async def health_connect_sync(
    payload: HealthConnectPayload,
    current_user: dict = Depends(get_current_user),
):
    """Sync data from Android Health Connect.

    Accepts health metrics collected from the Android Health Connect API
    (or the Tauri desktop app) and persists them via ``log_athlete_metric``.
    """
    from ..ingestion.health_connect import sync_health_data

    result = sync_health_data(
        current_user["id"],
        metrics=payload.metrics,
        tenant_id=current_user.get("tenant_id", current_user["id"]),
    )
    return result


# ------------------------------------------------------------------
# HR 24h continuous heart-rate tracking routes
# ------------------------------------------------------------------


@router.get("/hr/settings")
async def get_hr_settings_route(current_user: dict = Depends(get_current_user)):
    """Return HR 24h monitoring settings for the current athlete."""
    from ..db.database import get_hr_settings

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    settings = get_hr_settings(athlete_id, tenant_id)
    if settings is None:
        settings = {
            "enabled": True,
            "interval_seconds": 30,
            "source": "ble",
            "device_id": None,
            "max_hr": None,
            "resting_hr": None,
        }
    settings.pop("id", None)
    settings.pop("athlete_id", None)
    settings.pop("tenant_id", None)
    if "enabled" in settings:
        settings["enabled"] = bool(settings["enabled"])
    return settings


@router.put("/hr/settings")
async def upsert_hr_settings_route(
    settings_data: HrMonitoringSettings,
    current_user: dict = Depends(get_current_user),
):
    """Create or update HR 24h monitoring settings."""
    from ..db.database import upsert_hr_settings

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    settings = upsert_hr_settings(
        athlete_id,
        settings_data.model_dump(),
        tenant_id=tenant_id,
    )
    settings.pop("id", None)
    settings.pop("athlete_id", None)
    settings.pop("tenant_id", None)
    if "enabled" in settings:
        settings["enabled"] = bool(settings["enabled"])
    return settings


@router.post("/hr/samples")
async def log_hr_samples_route(
    samples: HrSamplesBulk,
    current_user: dict = Depends(get_current_user),
):
    """Persist heart-rate samples from BLE or other sources (bulk)."""
    from ..db.database import log_hr_samples

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    count = log_hr_samples(
        athlete_id,
        [s.model_dump() for s in samples.samples],
        source=samples.source or "ble",
        tenant_id=tenant_id,
    )
    return {"saved": count}


@router.get("/hr/24h")
async def get_hr_24h_route(
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user),
):
    """Return raw heart-rate samples for the last *hours* hours (oldest-first)."""
    from ..db.database import get_hr_24h_samples

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    samples = get_hr_24h_samples(athlete_id, hours=hours, tenant_id=tenant_id)
    return {"samples": samples}


@router.get("/hr/summary", response_model=Hr24hSummary | None)
async def get_hr_daily_summary_route(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Return per-day HR summary for the last *days* days (latest day)."""
    from ..db.database import get_hr_daily_summary

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    history = get_hr_daily_summary(athlete_id, days=days, tenant_id=tenant_id)
    if not history:
        return None
    return Hr24hSummary(**history[-1])


@router.get("/hr/summary/history")
async def get_hr_summary_history_route(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Return the full per-day HR history for charting trends."""
    from ..db.database import get_hr_daily_summary

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    history = get_hr_daily_summary(athlete_id, days=days, tenant_id=tenant_id)
    return {"history": history}


@router.delete("/hr/samples")
async def delete_hr_samples_route(
    older_than: str | None = Query(default=None, description="ISO timestamp; delete samples older than this"),
    current_user: dict = Depends(get_current_user),
):
    """Delete HR samples, optionally older than a given timestamp (cleanup)."""
    from ..db.database import delete_hr_samples

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    count = delete_hr_samples(athlete_id, tenant_id=tenant_id, older_than=older_than)
    return {"deleted": count}


@router.post("/hr/sensor")
async def log_sensor_data_route(
    payload: SensorSamplesBulk,
    current_user: dict = Depends(get_current_user),
):
    """Persist raw BLE sensor readings (heart-rate, GPS, accelerometer)."""
    from ..db.database import log_sensor_data

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    count = log_sensor_data(
        athlete_id,
        [s.model_dump() for s in payload.samples],
        tenant_id=tenant_id,
    )
    return {"saved": count}


@router.get("/activity/summary", response_model=ActivitySummaryResponse)
@limiter.limit("60/minute")
async def get_activity_summary_route(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Return daily activity classifications for the last *days* days."""
    from ..db.database import get_activity_summary

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    history = get_activity_summary(athlete_id, days=days, tenant_id=tenant_id)
    return {"history": [ActivityClassification(**h) for h in history]}


@router.post("/activity/classify")
@limiter.limit("60/minute")
async def classify_day_route(
    request: Request,
    for_date: str = Query(default=None, description="ISO date YYYY-MM-DD; defaults to today"),
    current_user: dict = Depends(get_current_user),
):
    """Compute (and persist) the activity classification for a single day."""
    from ..db.database import classify_day

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    if for_date is None:
        for_date = datetime.now(UTC).strftime("%Y-%m-%d")
    result = classify_day(athlete_id, for_date, tenant_id=tenant_id)
    return result


@router.get("/dashboard")
@limiter.limit("20/minute")
async def get_dashboard(request: Request, current_user: dict = Depends(get_current_user)):
    """Get consolidated dashboard analytics for authenticated athlete."""
    from ..analytics.dashboard import create_score_dashboard
    from ..analytics.training_load import get_7day_fitness_summary
    from ..db.database import get_athlete, get_rides_by_athlete

    def _compute() -> dict:
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
        return {
            "athlete": athlete_dict,
            "summary": summary,
            "scores": scores,
            "fitness": fitness,
            "trends": trends,
            "rides_count": len(rides),
        }

    athlete_id = _ensure_int_user_id(current_user)
    cache_key = f"dashboard:{athlete_id}"
    cached_result = await _cached(cache_key, ttl=120)
    if cached_result:
        return cached_result

    result = await run_in_threadpool(_compute)
    await _cache_set(cache_key, result, ttl=120)
    return result


@router.get("/athlete/state")
async def get_athlete_state(
    current_user: dict = Depends(get_current_user),
):
    """Compute and return the current athlete state."""
    from ..analytics.athlete_state.service import AthleteStateService
    from ..db.database import get_rides_by_athlete

    athlete_id = _ensure_int_user_id(current_user)
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id)]
    service = AthleteStateService()
    state = await service.calculate_current_state(
        athlete_id=athlete_id,
        rides=rides,
    )
    return state.to_dict()


@router.post("/beck/assessments", status_code=201)
async def create_beck_assessment(
    payload: BeckAssessmentCreate,
    current_user: dict = Depends(get_current_user),
):
    """Salva un nuovo assessment Beck per l'atleta autenticato."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    from ..db.database import get_athlete as _get_athlete
    from ..db.database import get_beck_assessment as _get_beck_assessment
    from ..db.database import save_beck_assessment as _save_beck

    athlete = _get_athlete(athlete_id, tenant_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    assessment_id = _save_beck(
        {
            "athlete_id": athlete_id,
            "tenant_id": tenant_id,
            "answers": [list(item) for item in payload.answers],
            "notes": payload.notes,
        },
        tenant_id=tenant_id,
    )
    row = _get_beck_assessment(assessment_id)
    return BeckAssessmentResponse(**row).model_dump()


@router.get("/beck/assessments", response_model=list[BeckAssessmentResponse])
async def list_beck_assessments(current_user: dict = Depends(get_current_user)):
    """Restituisce lo storico assessment Beck dell'atleta autenticato."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    from ..db.database import get_beck_assessments_by_athlete as _list_beck

    rows = _list_beck(athlete_id, tenant_id)
    return [BeckAssessmentResponse(**r).model_dump() for r in rows]


@router.get("/beck/assessments/latest", response_model=BeckAssessmentResponse)
async def get_latest_beck_assessment(current_user: dict = Depends(get_current_user)):
    """Restituisce l'ultimo assessment Beck completato."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    from ..db.database import get_latest_beck_assessment as _latest_beck

    row = _latest_beck(athlete_id, tenant_id)
    if not row:
        raise HTTPException(status_code=404, detail="No Beck assessments found")
    return BeckAssessmentResponse(**row).model_dump()


@router.get("/beck/history", response_model=BeckHistoryResponse)
async def get_beck_history(current_user: dict = Depends(get_current_user)):
    """Restituisce storico assessment Beck con trend."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    from ..db.database import get_beck_assessments_by_athlete as _list_beck
    from ..db.database import get_latest_beck_assessment as _latest_beck

    items = _list_beck(athlete_id, tenant_id)
    latest = _latest_beck(athlete_id, tenant_id)
    trend = [
        {"date": item.get("created_at"), "score": item.get("total_score"), "severity": item.get("severity")}
        for item in items
    ]
    return BeckHistoryResponse(
        items=[BeckAssessmentResponse(**r).model_dump() for r in items],
        latest=BeckAssessmentResponse(**latest).model_dump() if latest else None,
        trend=trend,
    ).model_dump()


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

@router.post("/auth/switch-athlete/{athlete_id}")
async def switch_athlete(athlete_id: int, current_user: dict = Depends(get_current_user)):
    """Switch the active athlete profile and return a new JWT with athlete_id claim."""
    from ..db.database import get_athlete as _get_athlete
    from ..security import create_access_token, create_refresh_token, save_refresh_token

    user_id = int(current_user["id"])
    athlete = _get_athlete(athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    if athlete.get("user_id") != user_id and athlete_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied to this athlete")

    access_token = create_access_token(
        subject=str(user_id),
        is_admin=current_user.get("is_admin", False),
        tenant_id=current_user.get("tenant_id", user_id),
        is_client=current_user.get("is_client", False),
        athlete_id=athlete_id,
    )
    refresh_token = create_refresh_token(
        subject=str(user_id),
        is_admin=current_user.get("is_admin", False),
        tenant_id=current_user.get("tenant_id", user_id),
        is_client=current_user.get("is_client", False),
    )
    await save_refresh_token(user_id, refresh_token)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_id": user_id,
        "athlete_id": athlete_id,
    }


# ------------------------------------------------------------------
# User OAuth credentials routes
# ------------------------------------------------------------------


@router.get("/connections/credentials")
async def list_my_oauth_credentials(current_user: dict = Depends(get_current_user)):
    """List OAuth credentials configured for the current user (without secrets)."""
    from ..db.database import get_all_user_oauth_credentials as _get_all

    user_id = int(current_user["id"])
    creds = _get_all(user_id)
    result = []
    for c in creds:
        result.append({
            "id": c["id"],
            "provider": c["provider"],
            "client_id": c["client_id"],
            "redirect_uri": c["redirect_uri"],
            "scope": c["scope"],
            "has_secret": bool(c["client_secret"]),
            "created_at": c["created_at"],
            "updated_at": c["updated_at"],
        })
    return {"credentials": result}


@router.post("/connections/credentials")
async def set_my_oauth_credentials(credentials: UserOAuthCredentials, current_user: dict = Depends(get_current_user)):
    """Set or update OAuth credentials for a specific provider."""
    from ..db.database import save_user_oauth_credentials as _save

    user_id = int(current_user["id"])
    data = credentials.model_dump(exclude_unset=True)
    if not data.get("client_id") and not data.get("client_secret"):
        raise HTTPException(status_code=400, detail="client_id or client_secret required")
    _save(user_id, credentials.provider, data)
    return {"status": "saved", "provider": credentials.provider}


@router.delete("/connections/credentials/{provider}")
async def delete_my_oauth_credentials(provider: str, current_user: dict = Depends(get_current_user)):
    """Delete OAuth credentials for a specific provider."""
    from ..db.database import delete_user_oauth_credentials as _delete

    user_id = int(current_user["id"])
    ok = _delete(user_id, provider)
    if not ok:
        raise HTTPException(status_code=404, detail="Credentials not found")
    return {"status": "deleted", "provider": provider}

