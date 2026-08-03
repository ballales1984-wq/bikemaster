from __future__ import annotations

import logging
from typing import Any

from ..traffic.overpass_client import fetch_road_data, fetch_bike_lanes

logger = logging.getLogger(__name__)

_SURFACE_PRIORITY = {
    "asphalt": 0,
    "paved": 0,
    "concrete": 0,
    "cobblestone": 1,
    "sett": 1,
    "gravel": 2,
    "fine_gravel": 2,
    "pebblestone": 2,
    "compacted": 2,
    "dirt": 3,
    "earth": 3,
    "ground": 3,
    "grass": 3,
    "unpaved": 3,
    "sand": 4,
    "mud": 4,
}

_HIGHWAY_CYCLING = {
    "cycleway",
    "path",
    "footway",
    "pedestrian",
    "track",
    "living_street",
    "residential",
    "service",
}


def _surface_from_tags(tags: dict[str, str]) -> str | None:
    surface = (tags.get("surface") or "").lower()
    if surface:
        return surface
    bicycle = (tags.get("bicycle") or "").lower()
    if bicycle in {"designated", "yes", "lane", "track"}:
        return "asphalt"
    return None


def _highway_from_tags(tags: dict[str, str]) -> str | None:
    return (tags.get("highway") or "").lower() or None


async def enrich_osm(points: list[dict[str, float]]) -> dict[str, Any] | None:
    if len(points) < 2:
        return None
    road_data = await fetch_road_data(points, include_geometry=False)
    bike_data = await fetch_bike_lanes(points, include_geometry=False)
    elements: list[dict[str, Any]] = []
    if road_data and isinstance(road_data, dict):
        elements.extend(road_data.get("elements", []))
    if bike_data and isinstance(bike_data, dict):
        elements.extend(bike_data.get("elements", []))
    if not elements:
        return None
    counts: dict[str, int] = {}
    surfaces: dict[str, int] = {}
    highways: set[str] = set()
    for el in elements:
        tags = el.get("tags") or {}
        hw = _highway_from_tags(tags)
        if hw:
            highways.add(hw)
            counts[hw] = counts.get(hw, 0) + 1
        s = _surface_from_tags(tags)
        if s:
            surfaces[s] = surfaces.get(s, 0) + 1
    dominant_surface = _dominant(surfaces)
    return {
        "elements": elements,
        "highway_counts": counts,
        "surface_counts": surfaces,
        "dominant_surface": dominant_surface,
        "highways": sorted(highways),
    }


def _dominant(counter: dict[str, int]) -> str | None:
    if not counter:
        return None
    return max(counter, key=lambda k: counter[k])


def roughness_for(surface: str | None) -> float:
    if not surface:
        return 1.0
    key = surface.lower()
    return float(_SURFACE_PRIORITY.get(key, 3))
