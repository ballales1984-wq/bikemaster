"""Incident data fetcher with support for multiple sources.

Supported sources (configurable):
- Local JSON file (INCIDENT_DATA_PATH) -- default, no API key required
- ANAS Open Data (via configurable endpoint)
- Generic REST API (extensible)

Each fetcher returns a normalized list of incidents:
{
    "id": str,
    "lat": float,
    "lon": float,
    "date": str (YYYY-MM-DD),
    "severity": str (low|medium|high|critical),
    "description": str,
    "source": str,
    "road_type": str (optional),
}
"""

from __future__ import annotations

import json
import logging
import math
import os
from datetime import UTC, datetime
from typing import Any

_INCIDENT_DATA_PATH = os.environ.get("INCIDENT_DATA_PATH", "")
_INCIDENT_API_URL = os.environ.get("INCIDENT_API_URL", "")
_INCIDENT_API_KEY = os.environ.get("INCIDENT_API_KEY", "")

logger = logging.getLogger(__name__)


def _load_local_incidents() -> list[dict[str, Any]]:
    if not _INCIDENT_DATA_PATH or not os.path.exists(_INCIDENT_DATA_PATH):
        return []
    try:
        with open(_INCIDENT_DATA_PATH, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("incidents", data.get("features", []))
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _fetch_from_api(lat: float, lon: float, radius_km: float = 5.0, days: int = 90) -> list[dict[str, Any]]:
    if not _INCIDENT_API_URL:
        return []
    headers = {}
    if _INCIDENT_API_KEY:
        headers["Authorization"] = f"Bearer {_INCIDENT_API_KEY}"
        headers["X-API-Key"] = _INCIDENT_API_KEY
    params = {
        "lat": lat,
        "lon": lon,
        "radius_km": radius_km,
        "days": days,
    }
    try:
        import requests as req

        resp = req.get(_INCIDENT_API_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("incidents", data.get("features", []))
    except Exception:
        logger.debug("Incident fetch failed", exc_info=True)
        return []


def _normalize_incident(raw: dict[str, Any], source: str) -> dict[str, Any] | None:
    try:
        lat = float(raw.get("lat", raw.get("latitude", 0)))
        lon = float(raw.get("lon", raw.get("longitude", 0)))
        if lat == 0 and lon == 0:
            return None
        date_val = raw.get("date", raw.get("data", raw.get("timestamp", "")))
        if isinstance(date_val, datetime):
            date_val = date_val.strftime("%Y-%m-%d")
        if isinstance(date_val, str) and len(date_val) >= 10:
            date_val = date_val[:10]
        else:
            date_val = datetime.now(UTC).strftime("%Y-%m-%d")
        severity = raw.get("severity", raw.get("gravita", raw.get("gravity", "medium")))
        if severity not in ("low", "medium", "high", "critical"):
            severity = "medium"
        description = raw.get("description", raw.get("descrizione", raw.get("desc", ""))) or ""
        road_type = raw.get("road_type", raw.get("strada", raw.get("road", ""))) or ""
        return {
            "id": str(raw.get("id", raw.get("codice", f"{source}_{lat}_{lon}_{date_val}"))),
            "lat": lat,
            "lon": lon,
            "date": date_val,
            "severity": severity,
            "description": description[:200],
            "source": source,
            "road_type": road_type,
        }
    except (ValueError, TypeError):
        return None


def fetch_incidents(
    lat: float,
    lon: float,
    radius_km: float = 5.0,
    days: int = 90,
) -> list[dict[str, Any]]:
    """Fetch incidents near coordinates from all configured sources."""
    incidents: list[dict[str, Any]] = []
    local = _load_local_incidents()
    for raw in local:
        norm = _normalize_incident(raw, "local")
        if norm:
            incidents.append(norm)
    api_data = _fetch_from_api(lat, lon, radius_km, days)
    for raw in api_data:
        norm = _normalize_incident(raw, "api")
        if norm:
            incidents.append(norm)
    return incidents


def fetch_incidents_by_bbox(
    south: float,
    west: float,
    north: float,
    east: float,
    days: int = 90,
) -> list[dict[str, Any]]:
    """Fetch incidents within a bounding box."""
    center_lat = (south + north) / 2
    center_lon = (west + east) / 2
    avg_lat = (south + north) / 2
    dist_deg = 111.32
    dist_lon_deg = 111.32 * math.cos(avg_lat * 3.14159 / 180)
    radius_km = max(
        (north - south) * dist_deg / 2,
        (east - west) * dist_lon_deg / 2,
        1.0,
    )
    return fetch_incidents(center_lat, center_lon, radius_km=radius_km, days=days)


def get_incident_stats(incidents: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate statistics from a list of incidents."""
    if not incidents:
        return {"total": 0, "by_severity": {}, "by_date": {}}
    by_severity: dict[str, int] = {}
    by_date: dict[str, int] = {}
    for inc in incidents:
        sev = inc.get("severity", "medium")
        by_severity[sev] = by_severity.get(sev, 0) + 1
        dt = inc.get("date", "unknown")
        by_date[dt] = by_date.get(dt, 0) + 1
    return {
        "total": len(incidents),
        "by_severity": by_severity,
        "by_date": dict(sorted(by_date.items(), reverse=True)[:30]),
    }
