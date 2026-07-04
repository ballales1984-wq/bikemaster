"""OpenStreetMap Overpass API client for road and bike lane data."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_RATE_LIMIT_S = 1.0
_USER_AGENT = "BikeMaster/1.0 (cycling analytics)"
_last_request_ts: float = 0.0
_rate_lock = asyncio.Lock()


async def _wait_for_rate_limit() -> None:
    global _last_request_ts
    async with _rate_lock:
        elapsed = asyncio.get_event_loop().time() - _last_request_ts
        if elapsed < _RATE_LIMIT_S:
            await asyncio.sleep(_RATE_LIMIT_S - elapsed)


async def _overpass_query(query: str, timeout: int = 30) -> dict[str, Any] | None:
    await _wait_for_rate_limit()
    try:
        resp = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: requests.post(
                _OVERPASS_URL,
                data={"data": query},
                headers={"User-Agent": _USER_AGENT},
                timeout=timeout,
            ),
        )
        global _last_request_ts
        _last_request_ts = asyncio.get_event_loop().time()
        if resp.ok:
            return resp.json()
    except requests.RequestException:
        pass
    return None


def _validate_coords(points: list[dict[str, float]]) -> None:
    for p in points:
        lat, lon = p.get("lat"), p.get("lon")
        if lat is None or lon is None:
            raise ValueError("Missing lat/lon in GPS point")
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError(f"Invalid coordinates: lat={lat}, lon={lon}")


async def fetch_road_data(points: list[dict[str, float]], include_geometry: bool = False) -> dict[str, Any] | None:
    """Fetch road network data for a bounding box defined by GPS points."""
    if not points or len(points) < 2:
        return None
    _validate_coords(points)
    lats = [p["lat"] for p in points]
    lons = [p["lon"] for p in points]
    bbox = f"{min(lats)},{min(lons)},{max(lats)},{max(lons)}"
    geom_clause = ";._;" if include_geometry else ";"
    query = f"""
    [out:json][timeout:25];
    (
      way["highway"]({bbox});
    );
    out body{geom_clause}
    """
    return await _overpass_query(query)


async def fetch_bike_lanes(points: list[dict[str, float]], include_geometry: bool = False) -> dict[str, Any] | None:
    """Fetch dedicated bike infrastructure for a bounding box."""
    if not points or len(points) < 2:
        return None
    _validate_coords(points)
    lats = [p["lat"] for p in points]
    lons = [p["lon"] for p in points]
    bbox = f"{min(lats)},{min(lons)},{max(lats)},{max(lons)}"
    geom_clause = ";._;" if include_geometry else ";"
    query = f"""
    [out:json][timeout:25];
    (
      way["bicycle"="designated"]({bbox});
      way["highway"="cycleway"]({bbox});
      way["cycleway"~"lane|track"]({bbox});
    );
    out body{geom_clause}
    """
    return await _overpass_query(query)


async def get_road_type_summary(points: list[dict[str, float]]) -> dict[str, int]:
    """Return counts of road types in the route area."""
    data = await fetch_road_data(points)
    if not data or "elements" not in data:
        return {}
    counts: dict[str, int] = {}
    for el in data["elements"]:
        tags = el.get("tags", {})
        hw = tags.get("highway", "unknown")
        counts[hw] = counts.get(hw, 0) + 1
    return counts
