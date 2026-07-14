"""SerpApi-backed Google Maps data provider (no Google Cloud billing required)."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from ..models.models import GPSPoint
from ..settings import get_settings

_s = get_settings()

logger = logging.getLogger(__name__)
_SERPAPI_RATE_LIMIT_S = 1.0
_serpapi_last_request_ts: float = 0.0


def _wait_for_rate_limit() -> None:
    global _serpapi_last_request_ts
    elapsed = time.time() - _serpapi_last_request_ts
    if elapsed < _SERPAPI_RATE_LIMIT_S:
        time.sleep(_SERPAPI_RATE_LIMIT_S - elapsed)


def get_serpapi_api_key() -> str | None:
    from ..api.user_keys import get_request_user_keys

    user_keys = get_request_user_keys()
    user_key = (user_keys.get("serpapi") or "").strip()
    if user_key:
        return user_key
    key = _s.serpapi_api_key
    return key if key else None


def search_places(query: str, lat: float | None = None, lon: float | None = None) -> dict[str, Any] | None:
    if not get_serpapi_api_key():
        return None
    params = {
        "engine": _s.serpapi_engine,
        "q": query,
        "api_key": get_serpapi_api_key(),
    }
    if lat is not None and lon is not None:
        params["ll"] = f"@{lat},{lon},15z"
        params["nearby"] = lat

    try:
        _wait_for_rate_limit()
        resp = requests.get(_s.serpapi_base_url, params=params, timeout=20)
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
