"""AetherMap adapter for BikeMaster route visualization.

Uses the shared AetherMap data layer (``WorldStore`` + GeoJSON) so the
serialization contract is identical to the standalone ``aethermap`` package
and to any future 3D Tiles exporter.

Output format: GeoJSON FeatureCollection with optional ``metadata`` section
containing ride statistics. The frontend ``useAetherMap`` composable reads
both the FeatureCollection features (as ``entities``) and the ``metadata``
section (as ``statistics``).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..models.models import GPSPoint, RouteStatistics

try:
    from aethermap import Geometria, Oggetto, Posizione, WorldStore
except ImportError as exc:
    raise RuntimeError("AetherMap package is required for the aethermap adapter") from exc

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


def _gps_point_to_obj(point: GPSPoint, idx: int, color: str) -> Oggetto:
    alt = point.altitude or 0.0
    pos = Posizione.from_latlon(point.lat, point.lon, alt)
    geom = Geometria(
        tipo="punto",
        dati={
            "tipo": "punto",
            "lat": point.lat,
            "lon": point.lon,
            "alt": alt,
            "ele": alt,
            "color": color,
            "idx": idx,
        },
    )
    return Oggetto(
        id=f"gps_{idx:06d}",
        tipo="segment",
        posizione=pos,
        geometria=geom,
        proprieta={"color": color, "idx": idx},
    )


def _gps_line_to_obj(points: list[GPSPoint], color: str) -> Oggetto:
    pts = [
        {"lat": p.lat, "lon": p.lon, "ele": p.altitude or 0.0}
        for p in points
    ]
    first = points[0]
    pos = Posizione.from_latlon(
        first.lat, first.lon, first.altitude or 0.0
    )
    geom = Geometria(tipo="linea", dati={"tipo": "linea", "punti": pts})
    return Oggetto(
        id="gps_segment",
        tipo="segment",
        posizione=pos,
        geometria=geom,
        proprieta={"color": color},
    )


def _build_world(
    points: list[GPSPoint],
    statistics: RouteStatistics | None,
    color_by_speed: bool,
) -> WorldStore:
    store = WorldStore()
    if not points:
        return store

    for i, point in enumerate(points):
        color = _speed_to_color(point.speed) if color_by_speed else "#FF6B00"
        store.add(_gps_point_to_obj(point, i, color))

    start = points[0]
    end = points[-1]
    start_pos = Posizione.from_latlon(start.lat, start.lon, start.altitude or 0.0)
    end_pos = Posizione.from_latlon(end.lat, end.lon, end.altitude or 0.0)
    store.add(Oggetto(
        id="marker_start",
        tipo="start",
        posizione=start_pos,
        geometria=Geometria(tipo="punto"),
        proprieta={"char": "S"},
    ))
    store.add(Oggetto(
        id="marker_end",
        tipo="end",
        posizione=end_pos,
        geometria=Geometria(tipo="punto"),
        proprieta={"char": "E"},
    ))

    if statistics and statistics.total_elevation_gain_m:
        mid = points[len(points) // 2]
        mid_pos = Posizione.from_latlon(mid.lat, mid.lon, statistics.total_elevation_gain_m or 0.0)
        store.add(Oggetto(
            id="marker_stats",
            tipo="stats",
            posizione=mid_pos,
            geometria=Geometria(tipo="punto"),
            proprieta={"char": "M"},
        ))

    return store


def _statistics_metadata(statistics: RouteStatistics | None) -> dict[str, Any]:
    md: dict[str, Any] = {"engine": "aethermap"}
    if statistics:
        md["statistics"] = {
            "total_distance_m": statistics.total_distance_m,
            "total_duration_s": statistics.total_duration_s,
            "avg_speed_km_h": statistics.avg_speed_km_h,
            "max_speed_km_h": statistics.max_speed_km_h,
            "total_elevation_gain_m": statistics.total_elevation_gain_m,
        }
    return md


def create_route_map(
    points: list[GPSPoint],
    statistics: RouteStatistics | None = None,
    output_path: str = "route_map.json",
    color_by_speed: bool = True,
) -> str:
    if not points:
        raise ValueError("No GPS points provided")

    world = _build_world(points, statistics, color_by_speed)
    metadata = _statistics_metadata(statistics)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    world.save_geojson(path, metadata=metadata)
    logger.debug("AetherMap GeoJSON written to %s", path)
    return str(path)
