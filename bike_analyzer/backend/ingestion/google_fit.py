"""Google Fit integration for activity import."""

from __future__ import annotations

import urllib.parse
from datetime import UTC, datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from ..settings import get_settings

_s = get_settings()


def get_authorization_url(client_id: str, redirect_uri: str = "http://localhost:8000/callback", state: str = "") -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": _s.google_fit_scope,
        "access_type": "offline",
        "state": state,
        "prompt": "consent",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    import requests

    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def _build_credentials(token_data: dict) -> Credentials:
    return Credentials(
        token=token_data.get("access_token", ""),
        refresh_token=token_data.get("refresh_token", ""),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=_s.google_fit_client_id,
        client_secret=_s.google_fit_client_secret,
        scopes=_s.google_fit_scope.split(),
    )


def validate_and_refresh_token(token_data: dict) -> dict:
    creds = _build_credentials(token_data)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token or token_data.get("refresh_token", ""),
        "expires_at": int(creds.expiry.timestamp()) if creds.expiry else 0,
        "scope": " ".join(creds.scopes or []),
    }


def _ms_to_iso(ms_str: str | int | None) -> str:
    if not ms_str:
        return ""
    try:
        ms = int(ms_str)
    except (TypeError, ValueError):
        return str(ms_str)
    return datetime.fromtimestamp(ms / 1000, tz=UTC).isoformat()


def fetch_cycling_activities(access_token: str) -> list[dict]:
    """Fetch cycling sessions from Google Fit REST API v1.

    Uses the Sessions endpoint, which returns activity sessions with
    startTimeMillis/endTimeMillis timestamps and activity type codes.
    """
    import requests

    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "startTime": "2020-01-01T00:00:00Z",
        "endTime": "2099-12-31T23:59:59Z",
    }
    resp = requests.get(
        "https://www.googleapis.com/fitness/v1/users/me/sessions",
        headers=headers,
        params=params,
        timeout=10,
    )
    resp.raise_for_status()
    activities: list[dict] = []
    for session in resp.json().get("session", []):
        activity_type = session.get("activity", 0)
        if activity_type == 1:
            activities.append(
                {
                    "id": session.get("id", ""),
                    "startTimeMillis": session.get("startTimeMillis", ""),
                    "endTimeMillis": session.get("endTimeMillis", ""),
                    "name": session.get("name", ""),
                }
            )
    return activities


def google_fit_to_ride(activities: list[dict]) -> list[dict]:
    """Convert Google Fit sessions to BikeMaster ride dicts.

    Supports both the Sessions API format (startTimeMillis/endTimeMillis,
    activity int code) and the legacy dataset:aggregate format for tests.
    """
    rides = []
    for act in activities:
        ms_start = act.get("startTimeMillis") or act.get("startTime", "")
        ms_end = act.get("endTimeMillis") or act.get("endTime", "")

        start_iso = _ms_to_iso(ms_start)
        end_iso = _ms_to_iso(ms_end)

        is_cycling = (
            act.get("activity") == 1
            or "cycling" in str(act.get("dataType", "")).lower()
            or "cycling" in str(act.get("name", "")).lower()
        )

        if not is_cycling:
            continue

        duration_min = 0.0
        if start_iso and end_iso:
            try:
                t0 = datetime.fromisoformat(start_iso[:19])
                t1 = datetime.fromisoformat(end_iso[:19])
                duration_min = round((t1 - t0).total_seconds() / 60, 1)
            except Exception:
                pass

        legacy_vals = act.get("value", [])
        distance_m = 0
        for v in legacy_vals:
            if isinstance(v, dict) and v.get("fpVal") and "distance" in str(v.get("name", "")).lower():
                distance_m = int(v["fpVal"])
                break

        ride = {
            "date": start_iso[:10] if start_iso else "",
            "duration_minutes": duration_min,
            "distance_km": round(distance_m / 1000, 2) if distance_m else 0,
            "avg_speed_kmh": round((distance_m / 1000) / (duration_min / 60), 1)
            if distance_m and duration_min > 0
            else 0,
            "title": act.get("name") or "Google Fit Cycling",
            "external_source": "google_fit",
            "external_id": act.get("id") or start_iso,
        }
        rides.append(ride)
    return rides
