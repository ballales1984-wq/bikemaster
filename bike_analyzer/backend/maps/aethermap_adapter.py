"""AetherMap adapter for BikeMaster route visualization.

Exposes the same public interface as ``map_renderer.create_route_map`` so it
can be swapped in behind the existing lazy registry without touching callers.

Requires the ``aethermap`` package (optional dependency ``bikemaster[maps]``).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from ..models.models import GPSPoint, RouteStatistics

if TYPE_CHECKING:
    from aethermap.render.scene import Scene

logger = logging.getLogger(__name__)


def _speed_to_color(speed_kmh: float | None) -> str:
    if speed_kmh is None:
        return "#4488ff"
    if speed_kmh >= 35:
        return "#00cc44"
    if speed_kmh >= 25:
        return "#88cc00"
    if speed_kmh >= 15:
        return "#ddbb00"
    if speed_kmh >= 5:
        return "#ee8800"
    return "#ee3333"


def _build_scene(
    points: list[GPSPoint],
    statistics: RouteStatistics | None,
    color_by_speed: bool,
) -> Scene:
    try:
        from aethermap.render.scene import Scene
    except ImportError as exc:
        raise RuntimeError(
            "aethermap is not installed. Install it with "
            "`pip install -e ./aethermap` or enable the optional "
            "`bikemaster[maps]` extra."
        ) from exc

    scene = Scene()
    if not points:
        return scene

    for i, point in enumerate(points[:-1]):
        color = _speed_to_color(point.speed) if color_by_speed else "#FF6B00"
        scene.add(
            "segment",
            [(point.lat, point.lon), (points[i + 1].lat, points[i + 1].lon)],
            char=color,
        )

    scene.add("start", (points[0].lat, points[0].lon), char="S")
    scene.add("end", (points[-1].lat, points[-1].lon), char="E")

    if statistics:
        scene.add(
            "stats",
            (
                points[0].lat,
                points[0].lon,
                statistics.total_elevation_gain_m or 0.0,
            ),
            char="M",
        )

    return scene


def create_route_map(
    points: list[GPSPoint],
    statistics: RouteStatistics | None = None,
    output_path: str = "route_map.json",
    color_by_speed: bool = True,
) -> str:
    if not points:
        raise ValueError("No GPS points provided")

    scene = _build_scene(points, statistics, color_by_speed)
    payload = {
        "engine": "aethermap",
        "entities": scene.entities,
    }

    if statistics:
        payload["statistics"] = {
            "total_distance_m": statistics.total_distance_m,
            "total_duration_s": statistics.total_duration_s,
            "avg_speed_km_h": statistics.avg_speed_km_h,
            "max_speed_km_h": statistics.max_speed_km_h,
            "total_elevation_gain_m": statistics.total_elevation_gain_m,
        }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    logger.debug("AetherMap scene written to %s", path)
    return str(path)
