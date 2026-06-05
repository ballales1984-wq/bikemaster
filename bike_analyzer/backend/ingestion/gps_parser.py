"""GPS parsing for FIT and GPX files."""
from __future__ import annotations
from datetime import datetime
from typing import Optional

def parse_gpx_file(content: str) -> list[dict]:
    import xml.etree.ElementTree as ET
    root = ET.fromstring(content)
    points, ns = [], {"d": "http://www.topografix.com/GPX/1/1"}
    for trkpt in root.findall(".//d:trkpt", ns):
        lat, lon = float(trkpt.get("lat")), float(trkpt.get("lon"))
        ele, time_elem = trkpt.find("d:ele", ns), trkpt.find("d:time", ns)
        altitude = float(ele.text) if ele is not None else None
        timestamp = datetime.fromisoformat(time_elem.text.replace("Z", "+00:00")) if time_elem is not None else None
        if timestamp: points.append({"lat": lat, "lon": lon, "timestamp": timestamp, "altitude": altitude})
    return points

def parse_fit_file(file_path: str) -> list[dict]:
    try:
        from fitparse import FitFile
        points = []
        for record in FitFile(file_path).get_messages("record"):
            d = record.get_values()
            if "position_lat" in d and "position_long" in d:
                lat, lon = d["position_lat"] * (180 / 2**31), d["position_long"] * (180 / 2**31)
                ts = d.get("timestamp")
                alt = d.get("enhanced_altitude") or d.get("altitude")
                spd = d.get("speed") * 3.6 if d.get("speed") else None
                if lat is not None and lon is not None and ts: points.append({"lat": lat, "lon": lon, "timestamp": ts, "altitude": alt, "speed": spd})
        return points
    except ImportError: raise ImportError("fitparse not installed. Run: pip install fitparse")

def points_to_ride(points: list[dict], name: Optional[str] = None, weight_kg: float = 70.0) -> dict:
    if not points: return {"error": "No GPS points provided"}
    from ..models.models import haversine_distance_m
    total_distance = sum(
        haversine_distance_m(points[i-1]["lat"], points[i-1]["lon"], p["lat"], p["lon"])
        for i, p in enumerate(points) if i > 0
    ) if len(points) > 1 else 0
    duration_s = (points[-1]["timestamp"] - points[0]["timestamp"]).total_seconds() if len(points) > 1 else 0
    avg_speed = (total_distance / duration_s * 3.6) if duration_s > 0 else 0
    return {
        "date": points[0]["timestamp"].strftime("%Y-%m-%d") if points else "",
        "distance_km": total_distance / 1000,
        "duration_minutes": duration_s / 60,
        "avg_speed_kmh": avg_speed,
        "weight_kg": weight_kg,
        "gps_points": [{"lat": p["lat"], "lon": p["lon"], "timestamp": p["timestamp"].isoformat(), "altitude": p.get("altitude"), "speed": p.get("speed")} for p in points]
    }