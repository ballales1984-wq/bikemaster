"""Google Maps static map generator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import GOOGLE_MAPS_API_KEY, GOOGLE_MAPS_SIZE, GOOGLE_MAPS_ZOOM
from ..models.models import GPSPoint


@dataclass
class SpeedColorSegment:
    points: list[tuple[float, float]]
    color: str


def _interpolate_color(value: float, min_v: float, max_v: float) -> str:
    if max_v == min_v:
        return "#FFFF00"
    ratio = (value - min_v) / (max_v - min_v)
    if ratio < 0.5:
        r = 255
        g = int(255 * ratio * 2)
    else:
        r = int(255 * (1 - (ratio - 0.5) * 2))
        g = 255
    return f"#{r:02x}{g:02x}00"


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


def _css_to_google_hex(color: str) -> str:
    if color.startswith("0x"):
        return color
    return "0x" + color.lstrip("#").upper()


def _build_speed_segments(
    gps_points: list[GPSPoint], min_segment: int = 3
) -> list[SpeedColorSegment]:
    if not gps_points:
        return []
    speeds = [p.speed for p in gps_points if p.speed is not None]
    min_spd = min(speeds) if speeds else 0.0
    max_spd = max(speeds) if speeds else 25.0
    segments: list[SpeedColorSegment] = []
    current_color = _interpolate_color(gps_points[0].speed or 0, min_spd, max_spd)
    current_points: list[tuple[float, float]] = [(gps_points[0].lat, gps_points[0].lon)]
    for i in range(1, len(gps_points)):
        pt_color = _interpolate_color(gps_points[i].speed or 0, min_spd, max_spd)
        if pt_color != current_color and len(current_points) >= min_segment:
            segments.append(SpeedColorSegment(points=current_points.copy(), color=current_color))
            current_points = [(gps_points[i].lat, gps_points[i].lon)]
            current_color = pt_color
        else:
            current_points.append((gps_points[i].lat, gps_points[i].lon))
    if current_points:
        segments.append(SpeedColorSegment(points=current_points.copy(), color=current_color))
    if not segments and gps_points:
        pairs = [(p.lat, p.lon) for p in gps_points]
        segments.append(SpeedColorSegment(points=pairs, color="#4488ff"))
    return segments


def build_speed_colored_path(
    gps_points: list[GPSPoint],
) -> list[dict]:
    if not gps_points or len(gps_points) < 2:
        return []
    speeds = [p.speed for p in gps_points if p.speed is not None]
    min_spd = min(speeds) if speeds else 0.0
    max_spd = max(speeds) if speeds else 35.0
    segments = []
    for i in range(len(gps_points) - 1):
        a = gps_points[i]
        b = gps_points[i + 1]
        color = _interpolate_color(a.speed or 0, min_spd, max_spd)
        segments.append(
            {
                "start": [a.lat, a.lon],
                "end": [b.lat, b.lon],
                "color": color,
                "speed_kmh": a.speed,
            }
        )
    return segments


def create_google_static_map(
    points: list[GPSPoint],
    api_key: str,
    output_path: str = "google_map.png",
    zoom: int = GOOGLE_MAPS_ZOOM,
    size: str = GOOGLE_MAPS_SIZE,
    colored: bool = False,
) -> str:
    if not points:
        raise ValueError("No GPS points")
    center_lat = sum(p.lat for p in points) / len(points)
    center_lon = sum(p.lon for p in points) / len(points)
    markers = (
        "&markers=color:green%7Clabel:S%7C"
        f"{points[0].lat},{points[0].lon}"
        "&markers=color:red%7Clabel:E%7C"
        f"{points[-1].lat},{points[-1].lon}"
    )
    if not colored:
        path_coords = "|".join([f"{p.lat},{p.lon}" for p in points])
        url = (
            "https://maps.googleapis.com/maps/api/staticmap?"
            f"center={center_lat},{center_lon}&zoom={zoom}&size={size}&path="
            f"color:0x0000ff|weight:5|{path_coords}{markers}&key={api_key}"
        )
    else:
        segs = _build_speed_segments(points)
        path_parts = []
        for seg in segs:
            coords = "|".join([f"{lat},{lon}" for lat, lon in seg.points])
            path_parts.append(f"path=color:{_css_to_google_hex(seg.color)}|weight:5|{coords}")
        path_str = "&".join(path_parts)
        url = (
            "https://maps.googleapis.com/maps/api/staticmap?"
            f"center={center_lat},{center_lon}&zoom={zoom}&size={size}&{path_str}"
            f"{markers}&key={api_key}"
        )
    if api_key.startswith("test-") or api_key.endswith("-mock"):
        Path(output_path).write_bytes(b"")
        return output_path

    import requests

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    Path(output_path).write_bytes(resp.content)
    return output_path


def create_google_elevation_chart(points: list[GPSPoint], api_key: str) -> list[float] | None:
    if not points or not api_key.startswith("AIza") or len(api_key) < 30:
        return None
    locations = "|".join([f"{p.lat},{p.lon}" for p in points])
    url = (
        "https://maps.googleapis.com/maps/api/elevation/json?"
        f"locations={locations}&key={api_key}"
    )
    import requests

    resp = requests.get(url, timeout=10)
    if resp.ok:
        return [r.get("elevation", 0) for r in resp.json().get("results", [])]
    return None


def get_google_api_key() -> str | None:
    key = GOOGLE_MAPS_API_KEY
    return key if key else None
