"""GPS parsing for FIT and GPX files."""
from __future__ import annotations
from datetime import datetime

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
                if lat and lon and ts: points.append({"lat": lat, "lon": lon, "timestamp": ts, "altitude": alt, "speed": spd})
        return points
    except ImportError: raise ImportError("fitparse not installed. Run: pip install fitparse")