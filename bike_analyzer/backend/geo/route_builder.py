from __future__ import annotations

from pathlib import Path
from typing import Any

from ..maps.aethermap_adapter import WorldStore, Geometria, Oggetto, Posizione
from ..maps.aethermap_adapter import _speed_to_color, _statistics_metadata
from ..models.models import GPSPoint, RouteStatistics
from .types import GeoEnrichedPoint


def build_aethermap_worldstore(
    points: list[GPSPoint | GeoEnrichedPoint],
    statistics: RouteStatistics | None = None,
    color_by_speed: bool = True,
    extra_layers: dict[str, Any] | None = None,
) -> tuple[WorldStore, dict[str, Any]]:
    store = WorldStore()
    if not points:
        return store, {}

    for i, point in enumerate(points):
        speed = getattr(point, "speed", None)
        color = _speed_to_color(speed) if color_by_speed else "#FF6B00"
        alt = getattr(point, "altitude", None) or getattr(point, "ele", None) or 0.0
        lat = point.lat
        lon = point.lon
        pos = Posizione.from_latlon(lat, lon, alt)
        props: dict[str, Any] = {"color": color, "idx": i}
        surface = getattr(point, "surface", None)
        if surface:
            props["surface"] = surface
        highway = getattr(point, "highway", None)
        if highway:
            props["highway"] = highway
        slope = getattr(point, "slope_percent", None)
        if slope is not None:
            props["slope_percent"] = slope
        tags = getattr(point, "tags", None)
        if tags:
            props["tags"] = tags
        geom = Geometria(
            tipo="punto",
            dati={
                "tipo": "punto",
                "lat": lat,
                "lon": lon,
                "alt": alt,
                "ele": alt,
                "color": color,
                "idx": i,
            },
        )
        store.add(Oggetto(
            id=f"gps_{i:06d}",
            tipo="segment",
            posizione=pos,
            geometria=geom,
            proprieta=props,
        ))

    start = points[0]
    end = points[-1]
    start_pos = Posizione.from_latlon(start.lat, start.lon, getattr(start, "altitude", None) or getattr(start, "ele", None) or 0.0)
    end_pos = Posizione.from_latlon(end.lat, end.lon, getattr(end, "altitude", None) or getattr(end, "ele", None) or 0.0)
    store.add(Oggetto(id="marker_start", tipo="start", posizione=start_pos,
                      geometria=Geometria(tipo="punto"), proprieta={"char": "S"}))
    store.add(Oggetto(id="marker_end", tipo="end", posizione=end_pos,
                      geometria=Geometria(tipo="punto"), proprieta={"char": "E"}))

    if statistics and statistics.total_elevation_gain_m:
        mid = points[len(points) // 2]
        mid_pos = Posizione.from_latlon(mid.lat, mid.lon, statistics.total_elevation_gain_m or 0.0)
        store.add(Oggetto(id="marker_stats", tipo="stats", posizione=mid_pos,
                          geometria=Geometria(tipo="punto"), proprieta={"char": "M"}))

    metadata = _statistics_metadata(statistics)
    if extra_layers:
        metadata.update(extra_layers)
    return store, metadata


def save_aethermap_geojson(
    store: WorldStore,
    metadata: dict[str, Any],
    output_path: str = "route_map.json",
) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    store.save_geojson(path, metadata=metadata)
    return str(path)
