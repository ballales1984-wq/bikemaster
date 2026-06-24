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

import logging
import secrets
import time
from typing import Any

import requests

from ..config import (
    STRAVA_API_BASE_URL,
    STRAVA_AUTH_URL,
    STRAVA_CLIENT_ID,
    STRAVA_CLIENT_SECRET,
    STRAVA_REDIRECT_URI,
    STRAVA_SCOPE,
    STRAVA_TOKEN_URL,
)

logger = logging.getLogger(__name__)

OAUTH_STATE_TTL_SECONDS = 600
TOKEN_REFRESH_BUFFER_SECONDS = 300


# ---------------------------------------------------------------------------
# OAuth 2.0 + PKCE helpers
# ---------------------------------------------------------------------------

def generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)


def generate_code_challenge(verifier: str) -> str:
    import base64
    import hashlib

    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def build_authorization_url(state: str, code_challenge: str) -> str:
    params = {
        "client_id": STRAVA_CLIENT_ID,
        "redirect_uri": STRAVA_REDIRECT_URI,
        "response_type": "code",
        "scope": STRAVA_SCOPE,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "approval_prompt": "auto",
    }
    return f"{STRAVA_AUTH_URL}?{requests.compat.urlencode(params)}"


def get_authorization_url(state: str | None = None) -> dict[str, str]:
    """Return dict with auth_url, state, and code_verifier (to be stored server-side)."""
    if not STRAVA_CLIENT_ID:
        raise RuntimeError("STRAVA_CLIENT_ID not configured")
    state = state or secrets.token_urlsafe(16)
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    auth_url = build_authorization_url(state, challenge)
    return {
        "auth_url": auth_url,
        "state": state,
        "code_verifier": verifier,
    }


# ---------------------------------------------------------------------------
# Token exchange / refresh
# ---------------------------------------------------------------------------

def exchange_code_for_token(code: str, code_verifier: str) -> dict[str, Any]:
    payload = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": STRAVA_REDIRECT_URI,
        "code_verifier": code_verifier,
    }
    resp = requests.post(STRAVA_TOKEN_URL, data=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    payload = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    resp = requests.post(STRAVA_TOKEN_URL, data=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


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
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_strava_tokens_athlete
                ON strava_tokens(athlete_id);
            """
        )


def store_token(athlete_id: int, token_data: dict[str, Any]) -> None:
    _ensure_token_table()

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
        athlete_name = token_data["athlete"].get("firstname", "")
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO strava_tokens (athlete_id, access_token, refresh_token, expires_at, scope, athlete_name)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id) DO UPDATE SET
                access_token = excluded.access_token,
                refresh_token = excluded.refresh_token,
                expires_at = excluded.expires_at,
                scope = excluded.scope,
                athlete_name = excluded.athlete_name,
                updated_at = datetime('now')
            """,
            (
                athlete_id,
                token_data.get("access_token", ""),
                token_data.get("refresh_token", ""),
                expires_at,
                scope,
                athlete_name,
            ),
        )


def revoke_token(athlete_id: int) -> None:
    with _get_conn() as conn:
        conn.execute("DELETE FROM strava_tokens WHERE athlete_id = ?", (athlete_id,))


def get_valid_token(athlete_id: int) -> str | None:
    _ensure_token_table()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT access_token, refresh_token, expires_at FROM strava_tokens WHERE athlete_id = ?",
            (athlete_id,),
        ).fetchone()
    if not row:
        return None
    access_token, refresh_token, expires_at = row
    if expires_at and expires_at - time.time() < TOKEN_REFRESH_BUFFER_SECONDS:
        try:
            new_data = refresh_access_token(refresh_token)
            store_token(athlete_id, new_data)
            return new_data.get("access_token")
        except Exception:
            logger.exception("Failed to refresh Strava token for athlete %s", athlete_id)
            return None
    return access_token


# ---------------------------------------------------------------------------
# Activity fetch
# ---------------------------------------------------------------------------

_STRAVA_PER_PAGE = 30


def fetch_activities(access_token: str, page: int = 1, per_page: int = _STRAVA_PER_PAGE) -> list[dict]:
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"page": page, "per_page": per_page}
    resp = requests.get(
        f"{STRAVA_API_BASE_URL}/athlete/activities",
        headers=headers,
        params=params,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_all_activities(access_token: str, max_pages: int = 20) -> list[dict]:
    all_activities: list[dict] = []
    page = 1
    while page <= max_pages:
        batch = fetch_activities(access_token, page=page)
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

def strava_to_ride(activity: dict[str, Any], weight_kg: float = 70.0) -> dict[str, Any]:
    """Convert a single Strava activity dict into a BikeMaster Ride dict."""
    sport = activity.get("sport_type", activity.get("type", "Ride"))
    if "bike" not in sport.lower() and "ride" not in sport.lower():
        return {"error": f"Activity type '{sport}' is not a cycling activity", "skipped": True}

    distance_m = activity.get("distance", 0)
    moving_time_s = activity.get("moving_time", 0)
    average_speed_ms = activity.get("average_speed", 0)
    avg_speed_kmh = average_speed_ms * 3.6 if average_speed_ms else 0
    date_str = activity.get("start_date_local", "")[:10]
    calories = activity.get("calories", 0) or 0
    total_elevation_gain = activity.get("total_elevation_gain", 0) or 0
    avg_heart_rate = activity.get("average_heartrate", 0) or None
    external_id = activity.get("id")
    name = activity.get("name", "")

    ride: dict[str, Any] = {
        "date": date_str,
        "distance_km": distance_m / 1000,
        "duration_minutes": moving_time_s / 60,
        "avg_speed_kmh": avg_speed_kmh,
        "weight_kg": weight_kg,
        "calories": calories,
        "elevation_gain_m": total_elevation_gain,
        "heart_rate_avg": avg_heart_rate,
        "gps_points": [],
        "external_source": "strava",
        "external_id": str(external_id) if external_id else None,
        "title": name,
    }
    return ride
