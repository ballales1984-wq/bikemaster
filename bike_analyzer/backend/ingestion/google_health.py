"""Google Health API integration for activity import."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import secrets
import urllib.parse
from datetime import UTC, datetime, timedelta
from typing import Any

from defusedxml import ElementTree as ET
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from ..settings import get_settings
from .gps_parser import points_to_ride

_s = get_settings()

GOOGLE_HEALTH_API_BASE = "https://health.googleapis.com/v4"


def _generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)


def _compute_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def get_authorization_url(
    client_id: str,
    redirect_uri: str = "http://localhost:8001/callback",
    state: str = "",
    code_challenge: str = "",
    code_challenge_method: str = "S256",
) -> str:
    params: dict[str, str] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": _s.google_health_scope,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "state": state,
        "prompt": "consent",
    }
    if code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = code_challenge_method
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    code_verifier: str = "",
) -> dict:
    import requests

    data: dict[str, str] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    if code_verifier:
        data["code_verifier"] = code_verifier
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data=data,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def _build_credentials(token_data: dict) -> Credentials:
    return Credentials(
        token=token_data.get("access_token", ""),
        refresh_token=token_data.get("refresh_token", ""),
        token_uri="https://oauth2.googleapis.com/token",  # noqa: S106
        client_id=_s.google_health_client_id,
        client_secret=_s.google_health_client_secret,
        scopes=_s.google_health_scope.split(),
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


def fetch_exercises(access_token: str, days: int = 180) -> list[dict]:
    import requests

    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    params = {
        "pageSize": 25,
        "filter": (
            'exercise.interval.start_time >= "'
            f"{start.isoformat(timespec='seconds')}"
            '" AND exercise.interval.start_time < "'
            f"{end.isoformat(timespec='seconds')}"
            '"'
        ),
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{GOOGLE_HEALTH_API_BASE}/users/me/dataTypes/exercise/dataPoints"

    exercises: list[dict] = []
    while url:
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        if resp.status_code == 403:
            raise requests.exceptions.HTTPError(f"403 Client Error: Forbidden for url: {resp.url}", response=resp)
        resp.raise_for_status()
        data = resp.json()
        exercises.extend(data.get("dataPoints", []))
        next_token = data.get("nextPageToken")
        if not next_token:
            break
        params = {"pageSize": 25, "pageToken": next_token, "filter": params["filter"]}
        url = f"{GOOGLE_HEALTH_API_BASE}/users/me/dataTypes/exercise/dataPoints"
    return exercises


def export_exercise_tcx(access_token: str, exercise_name: str) -> str:
    import requests

    url = f"{GOOGLE_HEALTH_API_BASE}/{exercise_name}:exportExerciseTcx"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        params={"alt": "media", "partialData": "true"},
        timeout=30,
    )
    resp.raise_for_status()
    if resp.headers.get("content-type", "").startswith("application/json"):
        payload = resp.json()
        return payload.get("tcxData", "")
    return resp.text


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _child_text(parent: ET.Element, path: str) -> str | None:
    for elem in parent.iter():
        if elem is parent:
            continue
        if _strip_ns(elem.tag) == path:
            return (elem.text or "").strip() or None
    return None


def _parse_tcx_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def tcx_to_points(tcx_content: str) -> list[dict[str, Any]]:
    if not tcx_content:
        return []
    root = ET.fromstring(tcx_content)
    points: list[dict[str, Any]] = []

    for trackpoint in root.iter():
        if _strip_ns(trackpoint.tag) != "Trackpoint":
            continue
        timestamp = _parse_tcx_time(_child_text(trackpoint, "Time"))
        lat_text = _child_text(trackpoint, "LatitudeDegrees")
        lon_text = _child_text(trackpoint, "LongitudeDegrees")
        try:
            lat = float(lat_text) if lat_text else None
            lon = float(lon_text) if lon_text else None
        except ValueError:
            lat, lon = None, None
        if not timestamp or lat is None or lon is None:
            continue

        point: dict[str, Any] = {
            "lat": lat,
            "lon": lon,
            "timestamp": timestamp,
            "altitude": None,
            "heart_rate": None,
            "speed": None,
        }
        ele_text = _child_text(trackpoint, "AltitudeMeters")
        hr_value = _child_text(trackpoint, "Value")
        speed_text = _child_text(trackpoint, "Speed")
        if ele_text:
            with contextlib.suppress(ValueError):
                point["altitude"] = float(ele_text)
        if hr_value:
            with contextlib.suppress(ValueError):
                point["heart_rate"] = int(float(hr_value))
        if speed_text:
            with contextlib.suppress(ValueError):
                point["speed"] = float(speed_text) * 3.6
        points.append(point)
    return points


def _summary_from_exercise(exercise: dict, title: str | None = None) -> dict[str, Any]:
    interval = exercise.get("interval", {})
    start_text = interval.get("startTime") or interval.get("civilStartTime", {}).get("date")
    end_text = interval.get("endTime")
    start = datetime.fromisoformat(start_text.replace("Z", "+00:00")) if start_text else None
    end = datetime.fromisoformat(end_text.replace("Z", "+00:00")) if end_text else None
    duration_minutes = (end - start).total_seconds() / 60 if start and end else 0
    date = start.strftime("%Y-%m-%d") if start else ""

    metrics = exercise.get("metricsSummary", {}) or {}
    distance_m = None
    calories = None
    avg_hr = None
    speed_mps = None

    for key in ("distanceMeters", "distance", "totalDistance"):
        value = metrics.get(key)
        if value not in (None, ""):
            try:
                distance_m = float(value)
                break
            except (TypeError, ValueError):
                pass
    for key in ("activeEnergy", "calories", "totalCalories", "caloriesKcal"):
        value = metrics.get(key)
        if value not in (None, ""):
            try:
                calories = float(value)
                break
            except (TypeError, ValueError):
                pass
    for key in ("averageHeartRate", "avgHeartRate", "heartRateAverage"):
        value = metrics.get(key)
        if value not in (None, ""):
            try:
                avg_hr = float(value)
                break
            except (TypeError, ValueError):
                pass
    for key in ("averageSpeed", "avgSpeed", "speed"):
        value = metrics.get(key)
        if value not in (None, ""):
            try:
                speed_mps = float(value)
                break
            except (TypeError, ValueError):
                pass

    distance_km = distance_m / 1000 if distance_m is not None else 0
    avg_speed_kmh = (
        speed_mps * 3.6
        if speed_mps is not None
        else (distance_km / (duration_minutes / 60) if duration_minutes > 0 else 0)
    )

    return {
        "title": title or exercise.get("displayName") or "Uscita Google Health",
        "date": date,
        "distance_km": round(distance_km, 3),
        "duration_minutes": round(duration_minutes, 2),
        "avg_speed_kmh": round(avg_speed_kmh, 2),
        "calories": round(calories, 1) if calories is not None else 0,
        "heart_rate_avg": round(avg_hr, 1) if avg_hr is not None else None,
        "external_source": "google_health",
        "external_id": exercise.get("name"),
    }


def google_health_to_rides(access_token: str, athlete_id: int, days: int = 180) -> list[dict[str, Any]]:
    rides: list[dict[str, Any]] = []
    for exercise in fetch_exercises(access_token, days=days):
        exercise_name = exercise.get("name")
        ride_data: dict[str, Any] | None = None
        if exercise_name:
            try:
                tcx = export_exercise_tcx(access_token, exercise_name)
                points = tcx_to_points(tcx)
                if points:
                    ride_data = points_to_ride(points, exercise.get("displayName") or "Uscita Google Health")
                    heart_rates = [p["heart_rate"] for p in points if p.get("heart_rate") is not None]
                    if heart_rates:
                        ride_data["heart_rate_avg"] = round(sum(heart_rates) / len(heart_rates), 1)
                    ride_data["external_source"] = "google_health"
                    ride_data["external_id"] = exercise_name
            except Exception:
                ride_data = None
        if ride_data is None:
            ride_data = _summary_from_exercise(exercise)
        ride_data["athlete_id"] = athlete_id
        rides.append(ride_data)
    return rides


def google_health_to_ride(exercises: list[dict]) -> list[dict]:
    return [_summary_from_exercise(exercise) for exercise in exercises]
