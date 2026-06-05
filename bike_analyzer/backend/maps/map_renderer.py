"""Map rendering with Folium for route visualization."""

from __future__ import annotations
from typing import Optional, List
import folium
from ..models.models import GPSPoint, RouteStatistics


def create_route_map(
    points: List[GPSPoint],
    statistics: Optional[RouteStatistics] = None,
    output_path: str = "route_map.html",
    color_by_speed: bool = True,
) -> str:
    if not points:
        raise ValueError("No GPS points provided")

    route_map = folium.Map(
        location=[sum(p.lat for p in points) / len(points), sum(p.lon for p in points) / len(points)],
        zoom_start=13,
    )

    if statistics is None:
        min_spd = 0.0
        max_spd = 25.0
    else:
        speeds_with_values = [p.speed for p in points if p.speed is not None]
        if speeds_with_values:
            min_spd = min(speeds_with_values)
            max_spd = max(speeds_with_values)
        else:
            min_spd = 0.0
            max_spd = 25.0

    for i, point in enumerate(points[:-1]):
        if color_by_speed:
            color = _speed_to_color(point.speed or 15, min_spd, max_spd)
        else:
            color = "#FF6B00"
        folium.PolyLine(
            locations=[(point.lat, point.lon), (points[i + 1].lat, points[i + 1].lon)],
            color=color,
            weight=5,
            opacity=0.8,
        ).add_to(route_map)

    if statistics:
        folium.Marker(
            location=[points[0].lat, points[0].lon],
            popup="Start",
            icon=folium.Icon(color="green", icon="play"),
        ).add_to(route_map)
        folium.Marker(
            location=[points[-1].lat, points[-1].lon],
            popup="End",
            icon=folium.Icon(color="red", icon="stop"),
        ).add_to(route_map)
        stats_html = (
            "<div><h4>Route Statistics</h4>"
            f"<p>Distance: {statistics.total_distance_m / 1000:.2f} km</p>"
            f"<p>Avg Speed: {statistics.avg_speed_km_h:.1f} km/h</p>"
            f"<p>Max Speed: {statistics.max_speed_km_h:.1f} km/h</p>"
            f"<p>Elevation Gain: {statistics.total_elevation_gain_m:.0f} m</p>"
            "</div>"
        )
        route_map.get_root().html.add_child(folium.Element(stats_html))

    route_map.save(output_path)
    return output_path


def _speed_to_color(speed: float, min_speed: float, max_speed: float) -> str:
    if max_speed == min_speed:
        return "#FFFF00"
    ratio = (speed - min_speed) / (max_speed - min_speed)
    if ratio < 0.5:
        r = int(255 * ratio * 2)
        g = 255
    else:
        r = 255
        g = int(255 * (1 - (ratio - 0.5) * 2))
    return f"#{r:02x}{g:02x}00"
