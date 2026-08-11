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

from ..audit import log_action, read_audit_logs
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
from bike_analyzer.backend.trusted_proxies import _is_trusted_proxy as is_trusted_proxy
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
    client_host = request.client.host if request.client else ""
    if is_trusted_proxy(client_host):
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme
        host = (
            request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
        )
    else:
        proto = request.url.scheme
        host = request.headers.get("host") or request.url.netloc
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


