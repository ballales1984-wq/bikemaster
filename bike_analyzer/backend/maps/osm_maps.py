"""OpenStreetMap-backed places and geocoding provider.

Uses the Nominatim API (public or self-hosted) for forward geocoding,
reverse geocoding, and POI search. No API key required for the public
instance (respect 1 req/s rate limit).
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests

from ..models.models import GPSPoint


from ..config import NOMINATIM_BASE_URL

_NOMINATIM_BASE = NOMINATIM_BASE_URL
_USER_AGENT = "BikeMaster/1.0 (https://github.com/your-repo)"
_RATE_LIMIT_S = 1.05

_last_request_ts: float = 0.0


def _wait_for_rate_limit() -> None:
    global _last_request_ts
    elapsed = time.time() - _last_request_ts
    if elapsed < _RATE_LIMIT_S:
        time.sleep(_RATE_LIMIT_S - elapsed)


def _nominatim_get(path: str, params: dict) -> Optional[dict]:
    _wait_for_rate_limit()
    try:
        resp = requests.get(
            f"{_NOMINATIM_BASE}{path}",
            params=params,
            headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
            timeout=20,
        )
        global _last_request_ts
        _last_request_ts = time.time()
        if resp.ok:
            return resp.json()
    except requests.RequestException:
        pass
    return None


def search_places(
    query: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    limit: int = 5,
) -> Optional[Dict[str, Any]]:
    params = {
        "q": query,
        "format": "json",
        "limit": limit,
        "addressdetails": 1,
    }
    if lat is not None and lon is not None:
        params["lat"] = lat
        params["lon"] = lon
        params["viewbox"] = f"{lon - 0.05},{lat + 0.05},{lon + 0.05},{lat - 0.05}"
        params["bounded"] = 0
    data = _nominatim_get("/search", params)
    if data is None:
        return None
    return {"results": data}


def get_local_results(
    points: List[GPSPoint],
    query: str = "cafe,bakery,restaurant",
    limit: int = 10,
) -> Optional[List[Dict[str, Any]]]:
    if not points:
        return None
    center_lat = sum(p.lat for p in points) / len(points)
    center_lon = sum(p.lon for p in points) / len(points)
    result = search_places(query, lat=center_lat, lon=center_lon, limit=limit)
    if not result:
        return None
    return result.get("results", [])


def search_nearby(
    points: List[GPSPoint],
    query: str,
    limit: int = 5,
) -> Optional[Dict[str, Any]]:
    if not points:
        return None
    center_lat = sum(p.lat for p in points) / len(points)
    center_lon = sum(p.lon for p in points) / len(points)
    return search_places(query, lat=center_lat, lon=center_lon, limit=limit)


def reverse_geocode(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1,
    }
    data = _nominatim_get("/reverse", params)
    if data and "error" not in data:
        return data
    return None
