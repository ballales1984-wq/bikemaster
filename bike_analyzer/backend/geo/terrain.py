from __future__ import annotations

import logging
from collections.abc import Sequence

from ..maps.terrain import generate_heightfield

logger = logging.getLogger(__name__)


def _interpolate_tile(heights: list[float], resolution: int, u: float, v: float) -> float:
    x = max(0.0, min(1.0, u)) * (resolution - 1)
    y = max(0.0, min(1.0, v)) * (resolution - 1)
    x0 = int(x)
    y0 = int(y)
    x1 = min(x0 + 1, resolution - 1)
    y1 = min(y0 + 1, resolution - 1)
    fx = x - x0
    fy = y - y0
    h00 = heights[y0 * resolution + x0]
    h10 = heights[y0 * resolution + x1]
    h01 = heights[y1 * resolution + x0]
    h11 = heights[y1 * resolution + x1]
    return (h00 * (1 - fx) + h10 * fx) * (1 - fy) + (h01 * (1 - fx) + h11 * fx) * fy


def sample_elevation_profile(
    points: Sequence[tuple[float, float]],
    resolution: int = 64,
    source: str = "auto",
) -> list[float]:
    if not points:
        return []
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    min_lat = min(lats)
    max_lat = max(lats)
    min_lon = min(lons)
    max_lon = max(lons)
    if max_lat - min_lat < 1e-6 and max_lon - min_lon < 1e-6:
        center_lat = (min_lat + max_lat) / 2.0
        center_lon = (min_lon + max_lon) / 2.0
        delta = 0.01
        min_lat = center_lat - delta
        max_lat = center_lat + delta
        min_lon = center_lon - delta
        max_lon = center_lon + delta
    tile = generate_heightfield(min_lat, max_lat, min_lon, max_lon, resolution, source=source)
    heights = tile.flatten().tolist()
    out: list[float] = []
    for lat, lon in points:
        u = (lon - min_lon) / max(1e-9, max_lon - min_lon)
        v = 1.0 - (lat - min_lat) / max(1e-9, max_lat - min_lat)
        out.append(float(_interpolate_tile(heights, resolution, max(0.0, min(1.0, u)), max(0.0, min(1.0, v)))))
    return out
