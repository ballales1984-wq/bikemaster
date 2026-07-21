"""AetherMap adapter for BikeMaster route visualization.

Produces a GeoJSON-like scene consumed by the frontend ``AetherMapViewer``
(WebGL2 cube-sphere globe). Coordinates are geographic ``[lat, lon]`` in
degrees; the ``stats`` entity carries ``[lat, lon, elevation_m]``. This keeps
the payload consistent with the consumer, which projects lat/lon onto the
unit sphere.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..models.models import GPSPoint, RouteStatistics

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


class _Scene:
    def __init__(self) -> None:
        self.entities: list[dict] = []

    def add(self, tipo: str, pts: list[list[float]], char: str) -> None:
        self.entities.append({"tipo": tipo, "pts": pts, "char": char})


def _build_scene(
    points: list[GPSPoint],
    statistics: RouteStatistics | None,
    color_by_speed: bool,
) -> _Scene:
    scene = _Scene()
    if not points:
        return scene

    for i, point in enumerate(points[:-1]):
        color = _speed_to_color(point.speed) if color_by_speed else "#FF6B00"
        seg_pts = [
            [points[i].lat, points[i].lon, points[i].altitude or 0.0],
            [points[i + 1].lat, points[i + 1].lon, points[i + 1].altitude or 0.0],
        ]
        scene.add("segment", seg_pts, color)

    start_alt = points[0].altitude or 0.0
    end_alt = points[-1].altitude or 0.0
    scene.add("start", [[points[0].lat, points[0].lon, start_alt]], "S")
    scene.add("end", [[points[-1].lat, points[-1].lon, end_alt]], "E")

    if statistics:
        scene.add(
            "stats",
            [[points[0].lat, points[0].lon, statistics.total_elevation_gain_m or 0.0]],
            "M",
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
    payload: dict[str, Any] = {
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
