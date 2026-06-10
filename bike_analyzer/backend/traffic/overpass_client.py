"""OpenStreetMap Overpass API client for road and bike lane data."""

from __future__ import annotations

import time
from typing import Any

import requests

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_RATE_LIMIT_S = 1.0
_last_request_ts: float = 0.0
_USER_AGENT = "BikeMaster/1.0 (cycling analytics)"


def _wait_for_rate_limit() -> None:
    global _last_request_ts
    elapsed = time.time() - _last_request_ts
    if elapsed < _RATE_LIMIT_S:
        time.sleep(_RATE_LIMIT_S - elapsed)


def _overpass_query(query: str, timeout: int = 30) -> dict[str, Any] | None:
    _wait_for_rate_limit()
    try:
        resp = requests.post(
            _OVERPASS_URL,
            data={"data": query},
            headers={"User-Agent": _USER_AGENT},
            timeout=timeout,
        )
        global _last_request_ts
        _last_request_ts = time.time()
        if resp.ok:
            return resp.json()
    except requests.RequestException:
        pass
    return None


def _bbox_str(points: list[dict[str, float]]) -> str:
    lats = [p["lat"] for p in points]
    lons = [p["lon"] for p in points]
    south = min(lats)
    north = max(lats)
    west = min(lons)
    east = max(lons)
    return f"{south},{west},{north},{east}"


def fetch_road_data(
    points: list[dict[str, float]], include_geometry: bool = False
) -> dict[str, Any] | None:
    """Fetch road network data for a bounding box defined by GPS points."""
    if not points or len(points) < 2:
        return None
    bbox = _bbox_str(points)
    geom_clause = ";._;" if include_geometry else ";"
    query = f"""
    [out:json][timeout:25];
    (
      way["highway"]({bbox});
    );
    out body{geom_clause}
    """
    return _overpass_query(query)


def fetch_bike_lanes(
    points: list[dict[str, float]], include_geometry: bool = False
) -> dict[str, Any] | None:
    """Fetch dedicated bike infrastructure for a bounding box."""
    if not points or len(points) < 2:
        return None
    bbox = _bbox_str(points)
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
    return _overpass_query(query)


def get_road_type_summary(points: list[dict[str, float]]) -> dict[str, int]:
    """Return counts of road types in the route area."""
    data = fetch_road_data(points)
    if not data or "elements" not in data:
        return {}
    counts: dict[str, int] = {}
    for el in data["elements"]:
        tags = el.get("tags", {})
        hw = tags.get("highway", "unknown")
        counts[hw] = counts.get(hw, 0) + 1
    return counts
