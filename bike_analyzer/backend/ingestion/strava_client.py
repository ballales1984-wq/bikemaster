"""Strava API integration for activity import and sync.

Provides:
- OAuth 2.0 + PKCE authorization flow
- Token exchange, refresh, and storage
- Activity fetch with pagination
- Normalization to Ride model format

Usage:
    from bike_analyzer.backend.ingestion.strava_client import (
        get_authorization_url,
        exchange_code_for_token,
        fetch_activities,
        strava_to_ride,
        get_valid_token,
        store_token,
        revoke_token,
    )
"""

from __future__ import annotations

import contextlib
import logging
import secrets
import sqlite3
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from ..http_async import request_json
from ..settings import get_settings

# Canonical Strava API v3 contract (Swagger 2.0), fetched from
# https://developers.strava.com/swagger/swagger.json and stored next to this
# module as ``strava_api_v3.swagger.json``. Use it to validate requests/responses
# or to regenerate typed clients.
STRAVA_API_V3_SCHEMA = __file__.replace(".py", ".swagger.json")

_s = get_settings()

logger = logging.getLogger(__name__)

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"  # noqa: S105
STRAVA_API_BASE_URL = "https://www.strava.com/api/v3"

OAUTH_STATE_TTL_SECONDS = 600
TOKEN_REFRESH_BUFFER_SECONDS = 300


# ---------------------------------------------------------------------------
# OAuth 2.0 + PKCE helpers
# ---------------------------------------------------------------------------


def generate_code_verifier() -> str:
    """Generates the PKCE code_verifier: high-entropy URL-safe string (64 bytes)."""
    return secrets.token_urlsafe(64)


def generate_code_challenge(verifier: str) -> str:
    """Derives the PKCE code_challenge: SHA-256 of the verifier, Base64url without padding."""
    import base64
    import hashlib

    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def build_authorization_url(
    state: str,
    code_challenge: str,
    redirect_uri: str | None = None,
    client_id: str | None = None,
) -> str:
    """Builds the Strava OAuth2 authorization URL with PKCE (S256)."""
    cid = client_id or _s.strava_client_id
    if not cid:
        raise RuntimeError("Strava client_id not configured")
    params = {
        "response_type": "code",
        "client_id": cid,
        "redirect_uri": redirect_uri or _s.strava_redirect_uri,
        "scope": _s.strava_scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "approval_prompt": "auto",
    }
    return f"{STRAVA_AUTH_URL}?{urlencode(params)}"


def get_authorization_url(
    state: str | None = None,
    redirect_uri: str | None = None,
    client_id: str | None = None,
) -> dict[str, str]:
    """Return dict with auth_url, state, and code_verifier (to be stored server-side)."""
    cid = client_id or _s.strava_client_id
    if not cid:
        raise RuntimeError("STRAVA_CLIENT_ID not configured")
    state = state or secrets.token_urlsafe(16)
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    auth_url = build_authorization_url(state, challenge, redirect_uri=redirect_uri, client_id=cid)
    return {
        "auth_url": auth_url,
        "state": state,
        "code_verifier": verifier,
    }


# ---------------------------------------------------------------------------
# Token exchange / refresh
# ---------------------------------------------------------------------------


async def exchange_code_for_token(
    code: str,
    code_verifier: str,
    redirect_uri: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> dict[str, Any]:
    """Exchanges the authorization code (plus PKCE code_verifier) for Strava tokens."""
    cid = client_id or _s.strava_client_id
    csec = client_secret or _s.strava_client_secret
    if not cid or not csec:
        raise RuntimeError("Strava client_id/client_secret not configured")
    payload = {
        "client_id": cid,
        "client_secret": csec,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri or _s.strava_redirect_uri,
        "code_verifier": code_verifier,
    }
    return await request_json("POST", STRAVA_TOKEN_URL, data=payload, timeout=15)


async def refresh_access_token(
    refresh_token: str, client_id: str | None = None, client_secret: str | None = None
) -> dict[str, Any]:
    """Renews a Strava access token using the refresh token (grant_type=refresh_token)."""
    cid = client_id or _s.strava_client_id
    csec = client_secret or _s.strava_client_secret
    if not cid or not csec:
        raise RuntimeError("Strava client_id/client_secret not configured")
    payload = {
        "client_id": cid,
        "client_secret": csec,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    return await request_json("POST", STRAVA_TOKEN_URL, data=payload, timeout=15)


# ---------------------------------------------------------------------------
# Token storage helpers (SQLite-backed)
# ---------------------------------------------------------------------------


def _get_conn():
    from ..db.database import get_db_connection

    return get_db_connection()


def _ensure_token_table() -> None:
    with _get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS strava_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id INTEGER NOT NULL,
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at INTEGER,
                scope TEXT,
                athlete_name TEXT,
                last_sync_ts INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_strava_tokens_athlete
                ON strava_tokens(athlete_id);
            """
        )
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute("ALTER TABLE strava_tokens ADD COLUMN last_sync_ts INTEGER")


def store_token(athlete_id: int, token_data: dict[str, Any]) -> None:
    from ..db.database import save_strava_token

    scope = token_data.get("scope", "")
    expires_at = token_data.get("expires_at", 0)
    if isinstance(expires_at, str):
        try:
            expires_at = int(expires_at)
        except ValueError:
            expires_at = 0
    if not expires_at and "expires_in" in token_data:
        expires_at = int(time.time()) + int(token_data["expires_in"])
    athlete_name = ""
    if token_data.get("athlete"):
        athlete_name = token_data.get("athlete", {}).get("firstname", "")
    encrypted_access = token_data.get("access_token", "")
    encrypted_refresh = token_data.get("refresh_token", "")
    try:
        from ..db.token_crypto import encrypt_token
        if encrypted_access:
            encrypted_access = encrypt_token(encrypted_access)
        if encrypted_refresh:
            encrypted_refresh = encrypt_token(encrypted_refresh)
    except Exception:
        logger.warning("Strava token encryption skipped", exc_info=True)
    save_strava_token(
        athlete_id=athlete_id,
        access_token=encrypted_access,
        refresh_token=encrypted_refresh,
        expires_at=expires_at,
        scope=scope,
        athlete_name=athlete_name,
    )


def get_last_sync_ts(athlete_id: int) -> int | None:
    from ..db.database import get_strava_token

    row = get_strava_token(athlete_id)
    if row and row.get("last_sync_ts") is not None:
        return int(row["last_sync_ts"])
    return None


def set_last_sync_ts(athlete_id: int, ts: int) -> None:
    from ..db.database import update_strava_last_sync

    update_strava_last_sync(athlete_id, ts)


def revoke_token(athlete_id: int) -> None:
    from ..db.database import revoke_strava_token

    revoke_strava_token(athlete_id)


async def get_valid_token(
    athlete_id: int, client_id: str | None = None, client_secret: str | None = None
) -> str | None:
    print(f"DEBUG get_valid_token CALLED: athlete_id={athlete_id}")
    from ..db.database import get_strava_token

    row = get_strava_token(athlete_id)
    print(f"DEBUG get_valid_token: row={row!r}")
    if not row:
        print("DEBUG get_valid_token: row is falsy, returning None")
        return None
    access_token = row.get("access_token", "")
    refresh_token = row.get("refresh_token", "")
    expires_at = row.get("expires_at")
    print(f"DEBUG get_valid_token: access_token={access_token!r}, refresh_token={refresh_token!r}, expires_at={expires_at!r}")
    try:
        from ..db.token_crypto import decrypt_token
        if access_token:
            access_token = decrypt_token(access_token)
        if refresh_token:
            refresh_token = decrypt_token(refresh_token)
    except Exception:
        logger.warning("Strava token decryption failed", exc_info=True)
    print(f"DEBUG get_valid_token: after decrypt access_token={access_token!r}, refresh_token={refresh_token!r}")
    if not access_token:
        print("DEBUG get_valid_token: access_token is falsy, returning None")
        return None
    if expires_at and expires_at - time.time() < TOKEN_REFRESH_BUFFER_SECONDS:
        print(f"DEBUG get_valid_token: token expired, refreshing...")
        try:
            new_data = await refresh_access_token(refresh_token or "", client_id=client_id, client_secret=client_secret)
            print(f"DEBUG get_valid_token: new_data={new_data!r}")
            store_token(athlete_id, new_data)
            result = new_data.get("access_token")
            print(f"DEBUG get_valid_token: result={result!r}")
            return result
        except Exception:
            logger.exception("Failed to refresh Strava token for athlete %s", athlete_id)
            return None
    print("DEBUG get_valid_token: token still valid, returning access_token")
    return access_token


# ---------------------------------------------------------------------------
# Activity fetch
# ---------------------------------------------------------------------------

_STRAVA_PER_PAGE = 30


async def fetch_activities(
    access_token: str,
    page: int = 1,
    per_page: int = _STRAVA_PER_PAGE,
    after: int | None = None,
) -> list[dict]:
    """Fetches one page of athlete activities from the Strava v3 endpoint."""
    headers = {"Authorization": f"Bearer {access_token}"}
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if after is not None:
        params["after"] = after
    return await request_json(
        "GET",
        f"{STRAVA_API_BASE_URL}/athlete/activities",
        headers=headers,
        params=params,
        timeout=20,
    )


async def fetch_all_activities(
    access_token: str,
    max_pages: int = 20,
    after: int | None = None,
) -> list[dict]:
    """Fetch all athlete activities, optionally only after a Unix timestamp."""
    all_activities: list[dict] = []
    page = 1
    while page <= max_pages:
        batch = await fetch_activities(access_token, page=page, after=after)
        if not batch:
            break
        all_activities.extend(batch)
        if len(batch) < _STRAVA_PER_PAGE:
            break
        page += 1
    return all_activities


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def decode_polyline(encoded: str) -> list[dict[str, float]]:
    """Decode a Google-encoded polyline string into a list of {lat, lon} dicts."""
    if not encoded:
        return []
    points: list[dict[str, float]] = []
    index = 0
    lat = lng = 0
    while index < len(encoded):
        for coord in ("lat", "lng"):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if (result & 1) else (result >> 1)
            if coord == "lat":
                lat += delta
            else:
                lng += delta
        points.append({"lat": lat / 1e5, "lon": lng / 1e5})
    return points


class StravaRateLimitError(Exception):
    """Raised when Strava returns HTTP 429 on a streams request."""

    pass


async def fetch_activity_streams(
    access_token: str,
    activity_id: int | str,
    keys: tuple[str, ...] = ("latlng", "altitude"),
    resolution: str = "medium",
) -> dict:
    """Fetch raw GPS streams for a single activity.

    Returns the decoded Strava streams object, or raises ``StravaRateLimitError``
    on HTTP 429 so callers can stop hammering the API (no retries, since a 429
    here means the whole import should fall back to the summary polyline).
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "keys": ",".join(keys),
        "key_by_type": "true",
        "resolution": resolution,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{STRAVA_API_BASE_URL}/activities/{activity_id}/streams",
            headers=headers,
            params=params,
        )
    if resp.status_code == 429:
        raise StravaRateLimitError()
    resp.raise_for_status()
    return resp.json()


def streams_to_points(streams: dict) -> list[dict[str, float]] | None:
    """Convert a Strava streams object into [{lat, lon, altitude?}] points."""
    if not streams:
        return None
    latlng = (streams.get("latlng") or {}).get("data")
    if not latlng:
        return None
    altitudes = (streams.get("altitude") or {}).get("data") or []
    points: list[dict[str, float]] = []
    for i, (lat, lng) in enumerate(latlng):
        pt: dict[str, float] = {"lat": float(lat), "lon": float(lng)}
        if i < len(altitudes):
            with contextlib.suppress(TypeError, ValueError):
                pt["altitude"] = float(altitudes[i])
        points.append(pt)
    return points or None


def _map_strava_sport_to_activity_type(sport: str) -> str:
    """Map a Strava sport type to a BikeMaster activity_type."""
    sport_lower = sport.lower()
    if any(keyword in sport_lower for keyword in ("bike", "ride", "velomobile")):
        return "ride"
    if sport_lower in ("run", "trailrunning", "virtualrun"):
        return "run"
    if sport_lower == "walk":
        return "walk"
    if sport_lower == "hike":
        return "hike"
    if sport_lower == "swim":
        return "other"
    if sport_lower in (
        "workout",
        "weighttraining",
        "crossfit",
        "stretching",
        "yoga",
        "elliptical",
        "stairstepper",
        "rowing",
        "virtualrow",
    ):
        return "indoor"
    return "other"


def strava_to_ride(
    activity: dict[str, Any],
    weight_kg: float = 70.0,
    gps_points: list[dict[str, float]] | None = None,
    resolution: str = "medium",
) -> dict[str, Any]:
    """Convert a single Strava activity dict into a BikeMaster Ride dict.

    GPS points are taken from ``gps_points`` when provided; otherwise the
    low-resolution ``summary_polyline`` from the activity list is decoded. The
    high-resolution Strava streams are fetched by the async
    :func:`strava_to_ride_with_streams` helper so this function stays free of
    blocking network I/O.
    """
    sport = activity.get("sport_type", activity.get("type", "Ride"))
    activity_type = _map_strava_sport_to_activity_type(sport)

    distance_m = activity.get("distance", 0)
    moving_time_s = activity.get("moving_time", 0)
    average_speed_ms = activity.get("average_speed", 0)
    avg_speed_kmh = average_speed_ms * 3.6 if average_speed_ms else 0
    date_str = activity.get("start_date_local", "")[:10]
    calories = activity.get("calories", 0) or 0
    total_elevation_gain = activity.get("total_elevation_gain", 0) or 0
    heart_rate_avg = activity.get("average_heartrate", 0) or None
    external_id = activity.get("id")
    name = activity.get("name", "")

    if gps_points is None:
        summary_polyline = (activity.get("map") or {}).get("summary_polyline")
        gps_points = decode_polyline(summary_polyline)

    ride: dict[str, Any] = {
        "date": date_str,
        "distance_km": distance_m / 1000,
        "duration_minutes": moving_time_s / 60,
        "avg_speed_kmh": avg_speed_kmh,
        "weight_kg": weight_kg,
        "calories": calories,
        "elevation_gain_m": total_elevation_gain,
        "heart_rate_avg": heart_rate_avg,
        "gps_points": gps_points,
        "external_source": "strava",
        "external_id": str(external_id) if external_id else None,
        "title": name,
        "activity_type": activity_type,
    }
    return ride


async def strava_to_ride_with_streams(
    activity: dict[str, Any],
    access_token: str,
    weight_kg: float = 70.0,
    resolution: str = "medium",
) -> dict[str, Any]:
    """Build a Strava ride dict, fetching high-resolution GPS streams.

    Falls back to the summary polyline (via :func:`strava_to_ride`) when streams
    are unavailable, but re-raises ``StravaRateLimitError`` so callers can stop
    requesting streams for the rest of the batch.
    """
    external_id = activity.get("id")
    points: list[dict[str, float]] | None = None
    if external_id is not None:
        try:
            streams = await fetch_activity_streams(access_token, external_id, resolution=resolution)
            points = streams_to_points(streams)
        except StravaRateLimitError:
            raise
        except Exception:
            logger.exception("Failed to fetch Strava streams for activity %s", external_id)
    return strava_to_ride(activity, weight_kg=weight_kg, gps_points=points, resolution=resolution)
