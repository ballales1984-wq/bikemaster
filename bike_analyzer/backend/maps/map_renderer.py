"""Map rendering with Folium for route visualization."""

from __future__ import annotations

from ..models.models import GPSPoint, RouteStatistics


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


def create_route_map(
    points: list[GPSPoint],
    statistics: RouteStatistics | None = None,
    output_path: str = "route_map.html",
    color_by_speed: bool = True,
) -> str:
    if not points:
        raise ValueError("No GPS points provided")

    import folium

    route_map = folium.Map(
        location=[
            sum(p.lat for p in points) / len(points),
            sum(p.lon for p in points) / len(points),
        ],
        zoom_start=13,
    )

    for i, point in enumerate(points[:-1]):
        color = _speed_to_color(point.speed) if color_by_speed else "#FF6B00"
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
