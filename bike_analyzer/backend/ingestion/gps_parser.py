"""GPS parsing for FIT and GPX files."""

from __future__ import annotations

from datetime import datetime


def parse_gpx_file(content: str) -> list[dict]:
    import re
    import xml.etree.ElementTree as ET

    content = re.sub(r"<!DOCTYPE[^>]*?>", "", content, flags=re.IGNORECASE | re.DOTALL)
    root = ET.fromstring(content)
    points, ns = [], {"d": "http://www.topografix.com/GPX/1/1"}
    for trkpt in root.findall(".//d:trkpt", ns):
        lat_raw, lon_raw = trkpt.get("lat"), trkpt.get("lon")
        try:
            lat, lon = float(lat_raw), float(lon_raw)
        except (TypeError, ValueError):
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        ele, time_elem = trkpt.find("d:ele", ns), trkpt.find("d:time", ns)
        altitude = float(ele.text) if ele is not None and ele.text is not None else None
        timestamp = None
        if time_elem is not None and time_elem.text:
            try:
                timestamp = datetime.fromisoformat(time_elem.text.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass
        if timestamp:
            points.append({"lat": lat, "lon": lon, "timestamp": timestamp, "altitude": altitude})
    return points


def parse_fit_file(file_path: str) -> list[dict]:
    try:
        from fitparse import FitFile

        points = []
        for record in FitFile(file_path).get_messages("record"):
            d = record.get_values()
            lat_raw, lon_raw = d.get("position_lat"), d.get("position_long")
            if lat_raw is None or lon_raw is None:
                continue
            try:
                lat, lon = float(lat_raw) * (180 / 2**31), float(lon_raw) * (180 / 2**31)
            except (TypeError, ValueError):
                continue
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            ts = d.get("timestamp")
            alt = d.get("enhanced_altitude") or d.get("altitude")
            spd = d.get("speed") * 3.6 if d.get("speed") is not None else None
            if ts:
                points.append({"lat": lat, "lon": lon, "timestamp": ts, "altitude": alt, "speed": spd})
        return points
    except ImportError:
        raise ImportError("fitparse not installed") from None


def points_to_ride(points: list[dict], name: str | None = None, weight_kg: float = 70.0) -> dict:
    if not points:
        return {"error": "No GPS points provided"}
    valid_points = [p for p in points if p.get("lat") is not None and p.get("lon") is not None and p.get("timestamp") is not None]
    if not valid_points:
        return {"error": "No valid GPS points provided"}
    from ..models.models import haversine_distance_m

    total_distance = (
        sum(
            haversine_distance_m(valid_points[i - 1]["lat"], valid_points[i - 1]["lon"], p["lat"], p["lon"])
            for i, p in enumerate(valid_points)
            if i > 0
        )
        if len(valid_points) > 1
        else 0
    )
    duration_s = (valid_points[-1]["timestamp"] - valid_points[0]["timestamp"]).total_seconds() if len(valid_points) > 1 else 0
    avg_speed = (total_distance / duration_s * 3.6) if duration_s > 0 else 0
    return {
        "date": valid_points[0]["timestamp"].strftime("%Y-%m-%d") if valid_points else "",
        "distance_km": total_distance / 1000,
        "duration_minutes": duration_s / 60,
        "avg_speed_kmh": avg_speed,
        "weight_kg": weight_kg,
        "gps_points": [
            {
                "lat": p["lat"],
                "lon": p["lon"],
                "timestamp": p["timestamp"].isoformat(),
                "altitude": p.get("altitude"),
                "speed": p.get("speed"),
            }
            for p in valid_points
        ],
    }
