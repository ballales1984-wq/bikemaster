from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional, Tuple

from bike_analyzer.map.gps_parser import GPSPoint
from bike_analyzer.map.map_builder import ProcessedRoute, extract_route_coordinates

try:
    import folium
except ImportError:
    folium = None  # type: ignore[assignment]


def render_folium_map(
    processed_route: ProcessedRoute,
    output_path: str = "route.html",
    show_speed_colors: bool = True,
    show_pauses: bool = True,
    center: Optional[Tuple[float, float]] = None,
) -> str:
    if folium is None:
        raise ImportError("folium is required for map rendering. Install it with: pip install folium")

    coordinates = extract_route_coordinates(processed_route.points)

    if center is None:
        mid = len(coordinates) // 2
        center = coordinates[mid]

    m = folium.Map(location=center, zoom_start=14)

    if show_speed_colors:
        _render_speed_segments(m, processed_route.segments)
    else:
        folium.PolyLine(coordinates, color="#0066FF", weight=4, opacity=0.9).add_to(m)

    if show_pauses:
        for pause in processed_route.pauses:
            pause_point = processed_route.points[0]
            for p in processed_route.points:
                if p.timestamp >= pause.start:
                    pause_point = p
                    break
            folium.CircleMarker(
                location=[pause_point.lat, pause_point.lon],
                radius=6,
                color="red",
                fill=True,
                fill_opacity=0.8,
                popup=f"Pausa: {pause.duration_s / 60:.1f} min",
            ).add_to(m)

    start_point = coordinates[0]
    end_point = coordinates[-1]
    folium.CircleMarker(
        location=start_point,
        radius=8,
        color="green",
        fill=True,
        fill_opacity=1.0,
        popup="Partenza",
    ).add_to(m)
    folium.CircleMarker(
        location=end_point,
        radius=8,
        color="red",
        fill=True,
        fill_opacity=1.0,
        popup="Arrivo",
    ).add_to(m)

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    m.save(output_path)
    return os.path.abspath(output_path)


def _speed_to_color(speed_km_h: float, max_speed: float) -> str:
    if max_speed <= 0:
        return "#0066FF"
    ratio = min(speed_km_h / max_speed, 1.0)
    r = int(0 + ratio * 220)
    g = int(100 - ratio * 50)
    b = int(255 - ratio * 200)
    return f"#{r:02X}{g:02X}{b:02X}"


def _render_speed_segments(map_obj, segments) -> None:
    if not segments:
        return
    max_speed = max(s.avg_speed_km_h for s in segments)
    for seg in segments:
        color = _speed_to_color(seg.avg_speed_km_h, max_speed)
        folium.PolyLine(
            locations=[(seg.start.lat, seg.start.lon), (seg.end.lat, seg.end.lon)],
            color=color,
            weight=5,
            opacity=0.85,
        ).add_to(map_obj)


def build_route_from_points(
    points: List[Tuple[float, float, float]],
    timestamps: Optional[List[float]] = None,
    altitudes: Optional[List[Optional[float]]] = None,
    speeds: Optional[List[Optional[float]]] = None,
) -> ProcessedRoute:
    gps_points = []
    for i, (lat, lon, ts) in enumerate(points):
        timestamp = datetime.fromtimestamp(ts) if timestamps is not None else datetime.now()
        altitude = altitudes[i] if altitudes and i < len(altitudes) else None
        speed = speeds[i] if speeds and i < len(speeds) else None
        gps_points.append(GPSPoint(lat=lat, lon=lon, timestamp=timestamp, altitude=altitude, speed=speed))

    route = GPSRoute(points=gps_points)
    from bike_analyzer.map.map_builder import build_processed_route
    return build_processed_route(route)
