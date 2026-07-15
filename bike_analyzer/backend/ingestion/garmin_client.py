"""Garmin Connect integration for activity import and sync.

Provides:
- OAuth 2.0 authorization flow
- Token exchange, refresh, and SQLite-backed storage
- Activity fetch via Garmin Fitness API
- Normalization to BikeMaster Ride format

Note: Garmin requires consumer key/secret obtained from developer portal.
The Garmin Fitness API rate-limits and requires authorization tokens with
activity:read scope.

Usage:
    from bike_analyzer.backend.ingestion.garmin_client import (
        get_authorization_url,
        exchange_code_for_token,
        fetch_activities,
        garmin_to_ride,
        get_valid_token,
        store_token,
    )
"""

from __future__ import annotations

import logging
import secrets
import time
from typing import Any
from urllib.parse import urlencode

from ..http_async import request_json
from ..settings import get_settings

_s = get_settings()

logger = logging.getLogger(__name__)

_GARMIN_AUTH_URL = "https://connect.garmin.com/oauthConfirm"
_GARMIN_TOKEN_URL = "https://connect.garmin.com/oauth2/token"  # noqa: S105
_GARMIN_API_BASE_URL = "https://apis.garmin.com/fitness/v1"

_TOKEN_TTL_SECONDS = 3600
_TOKEN_REFRESH_BUFFER_SECONDS = 300


# ---------------------------------------------------------------------------
# OAuth 2.0 (standard authorization code)
# ---------------------------------------------------------------------------


def get_authorization_url(state: str | None = None) -> dict[str, str]:
    """Return dict with auth_url and state."""
    if not _s.garmin_consumer_key:
        raise RuntimeError("GARMIN_CONSUMER_KEY not configured")
    state = state or secrets.token_urlsafe(16)
    params = {
        "response_type": "code",
        "client_id": _s.garmin_consumer_key,
        "redirect_uri": _s.garmin_redirect_uri,
        "scope": _s.garmin_scope,
        "state": state,
    }
    auth_url = f"{_GARMIN_AUTH_URL}?{urlencode(params)}"
    return {"auth_url": auth_url, "state": state}


async def exchange_code_for_token(code: str, redirect_uri: str | None = None) -> dict[str, Any]:
    """Exchange authorization code for access + refresh tokens."""
    redirect_uri = redirect_uri or _s.garmin_redirect_uri
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": _s.garmin_consumer_key,
        "client_secret": _s.garmin_consumer_secret,
        "redirect_uri": redirect_uri,
    }
    return await request_json("POST", _GARMIN_TOKEN_URL, data=payload, timeout=15)


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """Refresh an expired Garmin access token."""
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": _s.garmin_consumer_key,
        "client_secret": _s.garmin_consumer_secret,
    }
    return await request_json("POST", _GARMIN_TOKEN_URL, data=payload, timeout=15)


# ---------------------------------------------------------------------------
# Token storage (SQLite-backed, shares strava_tokens-like table shape)
# ---------------------------------------------------------------------------


def _get_conn():
    from ..db.database import get_db_connection

    return get_db_connection()


def _ensure_garmin_table() -> None:
    with _get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS garmin_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id INTEGER NOT NULL,
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at INTEGER,
                scope TEXT,
                athlete_name TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_garmin_tokens_athlete
                ON garmin_tokens(athlete_id);
            """
        )


def store_token(athlete_id: int, token_data: dict[str, Any]) -> None:
    _ensure_garmin_table()
    expires_at = token_data.get("expires_at", 0)
    if isinstance(expires_at, str):
        try:
            expires_at = int(expires_at)
        except ValueError:
            expires_at = int(time.time()) + _TOKEN_TTL_SECONDS
    if "expires_in" in token_data and not expires_at:
        expires_at = int(time.time()) + int(token_data["expires_in"])
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO garmin_tokens (athlete_id, access_token, refresh_token, expires_at, scope)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id) DO UPDATE SET
                access_token = excluded.access_token,
                refresh_token = excluded.refresh_token,
                expires_at = excluded.expires_at,
                scope = excluded.scope,
                updated_at = datetime('now')
            """,
            (
                athlete_id,
                token_data.get("access_token", ""),
                token_data.get("refresh_token", ""),
                expires_at,
                token_data.get("scope", ""),
            ),
        )


def revoke_token(athlete_id: int) -> None:
    with _get_conn() as conn:
        conn.execute("DELETE FROM garmin_tokens WHERE athlete_id = ?", (athlete_id,))


async def get_valid_token(athlete_id: int) -> str | None:
    _ensure_garmin_table()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT access_token, refresh_token, expires_at FROM garmin_tokens WHERE athlete_id = ?",
            (athlete_id,),
        ).fetchone()
    if not row:
        return None
    access_token, refresh_token, expires_at = row
    if expires_at and expires_at - time.time() < _TOKEN_REFRESH_BUFFER_SECONDS:
        try:
            new_data = await refresh_access_token(refresh_token)
            store_token(athlete_id, new_data)
            return new_data.get("access_token")
        except Exception:
            logger.exception("Failed to refresh Garmin token for athlete %s", athlete_id)
            return None
    return access_token


# ---------------------------------------------------------------------------
# Activity fetch
# ---------------------------------------------------------------------------


async def fetch_activities(access_token: str) -> list[dict[str, Any]]:
    """Fetch cycling activities from Garmin Connect."""
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    data = await request_json("GET", f"{_GARMIN_API_BASE_URL}/activities", headers=headers, timeout=20)
    if isinstance(data, list):
        return data
    return data.get("activities", [])


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def garmin_to_ride(activity: dict[str, Any], weight_kg: float = 70.0) -> dict[str, Any]:
    """Convert a Garmin activity dict into a BikeMaster Ride dict."""
    activity_type = activity.get("activityType", activity.get("type", ""))
    cycling_types = {
        "cycling",
        "road_biking",
        "mountain_biking",
        "gravel_cycling",
        "virtual_cycling",
        "indoor_cycling",
    }
    if isinstance(activity_type, dict):
        activity_type = activity_type.get("typeKey", "")
    type_key = (activity_type or "").lower()
    if type_key not in cycling_types and "bike" not in type_key:
        return {"error": f"Activity type '{activity_type}' is not cycling", "skipped": True}

    duration_s = activity.get("duration", 0) or 0
    distance_m = activity.get("distance", 0) or 0
    avg_speed = activity.get("averageSpeed", 0) or 0
    avg_speed_kmh = avg_speed * 3.6 if avg_speed else 0
    date_str = activity.get("startTimeLocal", activity.get("startTimeGMT", ""))
    if isinstance(date_str, str):
        date_str = date_str[:10]
    calories = activity.get("calories", 0) or 0
    elevation = activity.get("elevationGain", 0) or 0
    avg_hr = activity.get("averageHR", activity.get("averageHeartRate", 0)) or None
    activity_id = activity.get("activityId")
    activity_name = activity.get("activityName", "")

    ride: dict[str, Any] = {
        "date": date_str or "",
        "distance_km": distance_m / 1000,
        "duration_minutes": duration_s / 60,
        "avg_speed_kmh": avg_speed_kmh,
        "weight_kg": weight_kg,
        "calories": calories,
        "elevation_gain_m": elevation,
        "heart_rate_avg": avg_hr,
        "gps_points": [],
        "external_source": "garmin",
        "external_id": str(activity_id) if activity_id else None,
        "title": activity_name,
    }
    return ride
