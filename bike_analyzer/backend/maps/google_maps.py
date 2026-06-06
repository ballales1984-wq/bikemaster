"""Google Maps static map generator."""
from __future__ import annotations
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from ..models.models import GPSPoint
from ..config import GOOGLE_MAPS_ZOOM, GOOGLE_MAPS_SIZE

@dataclass
class SpeedColorSegment:
    points: List[Tuple[float, float]]
    color: str

def _speed_to_color(speed_kmh: Optional[float]) -> str:
    if speed_kmh is None: return "0x0000ff"
    if speed_kmh >= 25: return "0x00FF00"
    if speed_kmh >= 15: return "0xFFFF00"
    return "0xFF0000"

def _build_speed_segments(gps_points: List[GPSPoint], min_segment: int = 5) -> List[SpeedColorSegment]:
    if not gps_points: return []
    segments: List[SpeedColorSegment] = []
    current_color = _speed_to_color(gps_points[0].speed)
    current_points: List[Tuple[float, float]] = [(gps_points[0].lat, gps_points[0].lon)]
    for i in range(1, len(gps_points)):
        pt_color = _speed_to_color(gps_points[i].speed)
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
        segments.append(SpeedColorSegment(points=pairs, color="0x0000ff"))
    return segments

def create_google_static_map(points: List[GPSPoint], api_key: str, output_path: str = "google_map.png", zoom: int = GOOGLE_MAPS_ZOOM, size: str = GOOGLE_MAPS_SIZE, colored: bool = False) -> str:
    if not points: raise ValueError("No GPS points")
    center_lat = sum(p.lat for p in points) / len(points)
    center_lon = sum(p.lon for p in points) / len(points)
    markers = f"&markers=color:green%7Clabel:S%7C{points[0].lat},{points[0].lon}&markers=color:red%7Clabel=E%7C{points[-1].lat},{points[-1].lon}"
    if not colored:
        path_coords = "|".join([f"{p.lat},{p.lon}" for p in points])
        url = f"https://maps.googleapis.com/maps/api/staticmap?center={center_lat},{center_lon}&zoom={zoom}&size={size}&path=color:0x0000ff|weight:5|{path_coords}{markers}&key={api_key}"
    else:
        segs = _build_speed_segments(points)
        path_parts = []
        for seg in segs:
            coords = "|".join([f"{lat},{lon}" for lat, lon in seg.points])
            path_parts.append(f"path=color:{seg.color}|weight:5|{coords}")
        path_str = "&".join(path_parts)
        url = f"https://maps.googleapis.com/maps/api/staticmap?center={center_lat},{center_lon}&zoom={zoom}&size={size}&{path_str}{markers}&key={api_key}"
    import requests
    resp = requests.get(url, timeout=10)
    with open(output_path, "wb") as f: f.write(resp.content)
    return output_path

def create_google_elevation_chart(points: List[GPSPoint], api_key: str) -> Optional[List[float]]:
    if not points or not api_key.startswith("AIza") or len(api_key) < 30: return None
    locations = "|".join([f"{p.lat},{p.lon}" for p in points])
    url = f"https://maps.googleapis.com/maps/api/elevation/json?locations={locations}&key={api_key}"
    import requests
    resp = requests.get(url, timeout=10)
    if resp.ok:
        return [r.get("elevation", 0) for r in resp.json().get("results", [])]
    return None

def get_google_api_key() -> Optional[str]:
    from pathlib import Path
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        content = env_file.read_text()
        for line in content.splitlines():
            if line.startswith("GOOGLE_MAPS_API_KEY="): return line.split("=", 1)[1].strip()
    return None

