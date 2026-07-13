"""OpenStreetMap-backed places and geocoding provider.

Uses the Nominatim API (public or self-hosted) for forward geocoding,
reverse geocoding, and POI search. No API key required for the public
instance (respect 1 req/s rate limit).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from ..http_async import request_json
from ..models.models import GPSPoint
from ..settings import get_settings

_s = get_settings()

_NOMINATIM_BASE = _s.nominatim_base_url
_USER_AGENT = "BikeMaster/1.0 (https://github.com/your-repo)"
_RATE_LIMIT_S = 1.05

_last_request_ts: float = 0.0


async def _wait_for_rate_limit() -> None:
    global _last_request_ts
    elapsed = time.time() - _last_request_ts
    if elapsed < _RATE_LIMIT_S:
        await asyncio.sleep(_RATE_LIMIT_S - elapsed)


async def _nominatim_get(path: str, params: dict) -> dict | None:
    await _wait_for_rate_limit()
    try:
        data = await request_json(
            "GET",
            f"{_NOMINATIM_BASE}{path}",
            params=params,
            headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
            timeout=20,
        )
        global _last_request_ts
        _last_request_ts = time.time()
        return data
    except Exception:  # noqa: BLE001
        return None


async def search_places(
    query: str,
    lat: float | None = None,
    lon: float | None = None,
    limit: int = 5,
) -> dict[str, Any] | None:
    params = {
        "q": query,
        "format": "json",
        "limit": limit,
        "addressdetails": 1,
    }
    if lat is not None and lon is not None:
        params["viewbox"] = f"{lon - 0.05},{lat + 0.05},{lon + 0.05},{lat - 0.05}"
        params["bounded"] = 0
    data = await _nominatim_get("/search", params)
    if data is None:
        return None
    return {"results": data}


async def get_local_results(
    points: list[GPSPoint],
    query: str = "cafe,bakery,restaurant",
    limit: int = 10,
) -> list[dict[str, Any]] | None:
    if not points:
        return None
    center_lat = sum(p.lat for p in points) / len(points)
    center_lon = sum(p.lon for p in points) / len(points)
    result = await search_places(query, lat=center_lat, lon=center_lon, limit=limit)
    if not result:
        return None
    return result.get("results", [])


async def search_nearby(
    points: list[GPSPoint],
    query: str,
    limit: int = 5,
) -> dict[str, Any] | None:
    if not points:
        return None
    center_lat = sum(p.lat for p in points) / len(points)
    center_lon = sum(p.lon for p in points) / len(points)
    return await search_places(query, lat=center_lat, lon=center_lon, limit=limit)


async def reverse_geocode(lat: float, lon: float) -> dict[str, Any] | None:
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1,
    }
    data = await _nominatim_get("/reverse", params)
    if data and "error" not in data:
        return data
    return None
