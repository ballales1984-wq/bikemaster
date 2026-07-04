"""SerpApi-backed Google Maps data provider (no Google Cloud billing required)."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from ..config import SERPAPI_API_KEY, SERPAPI_BASE_URL, SERPAPI_ENGINE
from ..models.models import GPSPoint

logger = logging.getLogger(__name__)
_SERPAPI_RATE_LIMIT_S = 1.0
_serpapi_last_request_ts: float = 0.0


def _wait_for_rate_limit() -> None:
    global _serpapi_last_request_ts
    elapsed = time.time() - _serpapi_last_request_ts
    if elapsed < _SERPAPI_RATE_LIMIT_S:
        time.sleep(_SERPAPI_RATE_LIMIT_S - elapsed)


def search_places(query: str, lat: float | None = None, lon: float | None = None) -> dict[str, Any] | None:
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
        _wait_for_rate_limit()
        resp = requests.get(SERPAPI_BASE_URL, params=params, timeout=20)
        global _serpapi_last_request_ts
        _serpapi_last_request_ts = time.time()
        if resp.status_code == 429:
            logger.warning("SerpApi rate limit hit for query: %s", query)
            return None
        if resp.status_code == 403:
            logger.error("SerpApi 403 — invalid or exhausted API key")
            return None
        if resp.ok:
            return resp.json()
    except requests.RequestException as exc:
        logger.warning("SerpApi request failed: %s", exc)
    return None


def get_local_results(points: list[GPSPoint], query: str = "cafe,bakery,restaurant") -> list[dict[str, Any]] | None:
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
