"""Google Maps static map generator."""
from __future__ import annotations
from typing import List, Optional
import urllib.parse
from ..models.models import GPSPoint

def create_google_static_map(points: List[GPSPoint], api_key: str, output_path: str = "google_map.png", zoom: int = 13, size: str = "800x600") -> str:
    if not points: raise ValueError("No GPS points")
    center_lat = sum(p.lat for p in points) / len(points)
    center_lon = sum(p.lon for p in points) / len(points)
    path_coords = "|".join([f"{p.lat},{p.lon}" for p in points])
    url = f"https://maps.googleapis.com/maps/api/staticmap?center={center_lat},{center_lon}&zoom={zoom}&size={size}&path=enc:{path_coords}&key={api_key}"
    import requests
    resp = requests.get(url, timeout=10)
    with open(output_path, "wb") as f: f.write(resp.content)
    return output_path

def create_google_elevation_chart(points: List[GPSPoint], api_key: str) -> Optional[List[float]]:
    if not points or not api_key.startswith("AIza") or len(api_key) < 30: return None
    latlon = "|".join([f"{p.lat},{p.lon}" for p in points])
    url = f"https://maps.googleapis.com/maps/api/elevation/json?locations={latlon}&key={api_key}"
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