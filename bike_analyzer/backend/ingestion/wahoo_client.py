"""Wahoo Fitness Cloud API integration.

Provides:
- OAuth 2.0 + PKCE authorization flow
- Token exchange, refresh, and SQLite-backed storage
- Workout fetch from Wahoo Cloud API
- Normalization to BikeMaster Ride format

Usage:
    from bike_analyzer.backend.ingestion.wahoo_client import (
        get_authorization_url,
        exchange_code_for_token,
        refresh_access_token,
        fetch_workouts,
        wahoo_to_ride,
        get_valid_token,
        store_token,
        revoke_token,
    )
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from typing import Any

import requests

from ..settings import get_settings

_s = get_settings()

logger = logging.getLogger(__name__)

WAHOO_AUTH_URL = "https://api.wahooligan.com/oauth/authorize"
WAHOO_TOKEN_URL = "https://api.wahooligan.com/oauth/token"  # noqa: S105
WAHOO_API_BASE_URL = "https://api.wahooligan.com"

OAUTH_STATE_TTL_SECONDS = 600
TOKEN_REFRESH_BUFFER_SECONDS = 300


def generate_code_verifier() -> str:
    """Genera il PKCE code_verifier Wahoo: stringa URL-safe ad alta entropia (64 byte)."""
    return secrets.token_urlsafe(64)


def generate_code_challenge(verifier: str) -> str:
    """Deriva il code_challenge PKCE Wahoo: SHA-256 del verifier, Base64url senza padding."""
    digest = hashlib.sha256(verifier.encode()).digest()
    import base64

    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def build_authorization_url(
    state: str,
    code_challenge: str,
    client_id: str | None = None,
    redirect_uri: str | None = None,
    scope: str | None = None,
) -> str:
    """Costruisce l'URL di autorizzazione OAuth2 Wahoo con PKCE (S256)."""
    cid = client_id or _s.wahoo_client_id
    if not cid:
        raise RuntimeError("WAHOO_CLIENT_ID not configured")
    params = {
        "response_type": "code",
        "client_id": cid,
        "redirect_uri": redirect_uri or _s.wahoo_redirect_uri,
        "scope": scope or _s.wahoo_scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{WAHOO_AUTH_URL}?{requests.compat.urlencode(params)}"


def get_authorization_url(
    state: str | None = None, client_id: str | None = None, redirect_uri: str | None = None, scope: str | None = None
) -> dict[str, str]:
    cid = client_id or _s.wahoo_client_id
    if not cid:
        raise RuntimeError("WAHOO_CLIENT_ID not configured")
    state = state or secrets.token_urlsafe(16)
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    auth_url = build_authorization_url(state, challenge, client_id=cid, redirect_uri=redirect_uri, scope=scope)
    return {
        "auth_url": auth_url,
        "state": state,
        "code_verifier": verifier,
    }


def exchange_code_for_token(
    code: str,
    code_verifier: str,
    client_id: str | None = None,
    client_secret: str | None = None,
    redirect_uri: str | None = None,
) -> dict[str, Any]:
    cid = client_id or _s.wahoo_client_id
    csec = client_secret or _s.wahoo_client_secret
    if not cid or not csec:
        raise RuntimeError("Wahoo client_id/client_secret not configured")
    payload = {
        "client_id": cid,
        "client_secret": csec,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri or _s.wahoo_redirect_uri,
        "code_verifier": code_verifier,
    }
    resp = requests.post(WAHOO_TOKEN_URL, data=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(
    refresh_token: str, code_verifier: str, client_id: str | None = None, client_secret: str | None = None
) -> dict[str, Any]:
    cid = client_id or _s.wahoo_client_id
    csec = client_secret or _s.wahoo_client_secret
    if not cid or not csec:
        raise RuntimeError("Wahoo client_id/client_secret not configured")
    payload = {
        "client_id": cid,
        "client_secret": csec,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "code_verifier": code_verifier,
    }
    resp = requests.post(WAHOO_TOKEN_URL, data=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _get_conn():
    from ..db.database import get_db_connection

    return get_db_connection()


def _ensure_token_table() -> None:
    with _get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS wahoo_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                athlete_id INTEGER NOT NULL,
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                code_verifier TEXT NOT NULL,
                expires_at INTEGER,
                scope TEXT,
                athlete_name TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_wahoo_tokens_athlete
                ON wahoo_tokens(athlete_id);
            """
        )


def store_token(athlete_id: int, token_data: dict[str, Any], code_verifier: str = "") -> None:
    _ensure_token_table()
    expires_at = token_data.get("expires_at", 0)
    if isinstance(expires_at, str):
        try:
            expires_at = int(expires_at)
        except ValueError:
            expires_at = 0
    if "expires_in" in token_data and not expires_at:
        expires_at = int(time.time()) + int(token_data["expires_in"])
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO wahoo_tokens (athlete_id, access_token, refresh_token, code_verifier, expires_at, scope)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id) DO UPDATE SET
                access_token = excluded.access_token,
                refresh_token = excluded.refresh_token,
                code_verifier = excluded.code_verifier,
                expires_at = excluded.expires_at,
                scope = excluded.scope,
                updated_at = datetime('now')
            """,
            (
                athlete_id,
                token_data.get("access_token", ""),
                token_data.get("refresh_token", ""),
                code_verifier,
                expires_at,
                token_data.get("scope", ""),
            ),
        )


def revoke_token(athlete_id: int) -> None:
    with _get_conn() as conn:
        conn.execute("DELETE FROM wahoo_tokens WHERE athlete_id = ?", (athlete_id,))


def get_valid_token(athlete_id: int, client_id: str | None = None, client_secret: str | None = None) -> str | None:
    _ensure_token_table()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT access_token, refresh_token, code_verifier, expires_at FROM wahoo_tokens WHERE athlete_id = ?",
            (athlete_id,),
        ).fetchone()
    if not row:
        return None
    access_token, refresh_token, code_verifier, expires_at = row
    if expires_at and expires_at - time.time() < TOKEN_REFRESH_BUFFER_SECONDS:
        try:
            new_data = refresh_access_token(
                refresh_token, code_verifier, client_id=client_id, client_secret=client_secret
            )
            store_token(athlete_id, new_data, code_verifier=code_verifier)
            return new_data.get("access_token")
        except Exception:
            logger.exception("Failed to refresh Wahoo token for athlete %s", athlete_id)
            return None
    return access_token


def fetch_workouts(access_token: str) -> list[dict[str, Any]]:
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    resp = requests.get(
        f"{WAHOO_API_BASE_URL}/v1/workouts",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("workouts", data.get("results", []))


def wahoo_to_ride(workout: dict[str, Any], weight_kg: float = 70.0) -> dict[str, Any]:
    summary = workout.get("workout_summary") or {}
    if not summary:
        return {"error": "Missing workout_summary", "skipped": True}

    distance_m = float(summary.get("distance_accum", 0) or 0)
    duration_s = float(summary.get("duration_active_accum", 0) or 0)
    speed_ms = float(summary.get("speed_avg", 0) or 0)
    avg_speed_kmh = speed_ms * 3.6 if speed_ms else 0
    date_str = ""
    starts = workout.get("starts")
    if isinstance(starts, str):
        date_str = starts[:10]
    calories = float(summary.get("calories_accum", 0) or 0)
    elevation = float(summary.get("ascent_accum", 0) or 0)
    avg_hr = summary.get("heart_rate_avg")
    if avg_hr is not None:
        try:
            avg_hr = float(avg_hr)
            if avg_hr <= 0:
                avg_hr = None
        except (TypeError, ValueError):
            avg_hr = None
    workout_id = workout.get("id")
    title = summary.get("name") or workout.get("name") or ""

    ride: dict[str, Any] = {
        "date": date_str or "",
        "distance_km": distance_m / 1000,
        "duration_minutes": duration_s / 60,
        "avg_speed_kmh": avg_speed_kmh or 0.0,
        "weight_kg": weight_kg,
        "calories": calories,
        "elevation_gain_m": elevation,
        "heart_rate_avg": avg_hr,
        "gps_points": [],
        "external_source": "wahoo",
        "external_id": str(workout_id) if workout_id else None,
        "title": title,
    }
    return ride
