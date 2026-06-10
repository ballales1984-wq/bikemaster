"""SerpApi-backed Google Maps data provider (no Google Cloud billing required)."""

from __future__ import annotations

from typing import Any

import requests

from ..config import SERPAPI_API_KEY, SERPAPI_BASE_URL, SERPAPI_ENGINE
from ..models.models import GPSPoint


def search_places(
    query: str, lat: float | None = None, lon: float | None = None
) -> dict[str, Any] | None:
    if not SERPAPI_API_KEY:
        return None
    params = {
        "engine": SERPAPI_ENGINE,
        "q": query,
        "api_key": SERPAPI_API_KEY,
    }
    if lat is not None and lon is not None:
        params["ll"] = f"@{lat},{lon},15z"
        params["nearby"] = lat

    try:
        resp = requests.get(SERPAPI_BASE_URL, params=params, timeout=20)
        if resp.ok:
            return resp.json()
    except requests.RequestException:
        pass
    return None


def get_local_results(
    points: list[GPSPoint], query: str = "cafe,bakery,restaurant"
) -> list[dict[str, Any]] | None:
    if not points:
        return None
    center_lat = sum(p.lat for p in points) / len(points)
    center_lon = sum(p.lon for p in points) / len(points)
    data = search_places(query, center_lat, center_lon)
    if not data:
        return None
    return data.get("local_results") or data.get("places_results") or []


def search_nearby(points: list[GPSPoint], query: str) -> dict[str, Any] | None:
    if not points:
        return None
    center_lat = sum(p.lat for p in points) / len(points)
    center_lon = sum(p.lon for p in points) / len(points)
    return search_places(query, center_lat, center_lon)
