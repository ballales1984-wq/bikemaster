"""GPS parsing for FIT and GPX files."""

from __future__ import annotations

import math
import os
from datetime import datetime


def _perpendicular_distance(point: dict, start: dict, end: dict) -> float:
    """Distanza perpendicolare di ``point`` dal segmento ``start``-``end`` (in gradi).

    Formula della distanza punto-retta |dy·x − dx·y + ...| / √(dx²+dy²). Se il
    segmento è degenere (start==end) ritorna la distanza euclidea. Usata dal
    Douglas-Peucker per scegliere il punto più "lontano" dalla linea.
    """
    dx = end["lon"] - start["lon"]
    dy = end["lat"] - start["lat"]
    if dx == 0 and dy == 0:
        return math.hypot(point["lat"] - start["lat"], point["lon"] - start["lon"])
    num = abs(dy * point["lon"] - dx * point["lat"] + end["lon"] * start["lat"] - end["lat"] * start["lon"])
    den = math.hypot(dx, dy)
    return num / den if den else 0.0


def douglas_peucker(points: list[dict], tolerance: float = 0.00005) -> list[dict]:
    """Decimazione della traccia GPS con l'algoritmo Ramer–Douglas–Peucker.

    Approccia in modo ricorsivo (qui implementato con uno stack esplicito per
    evitare la ricursion depth): mantiene sempre i capi estremi, poi per ogni
    sotto-segmento trova il punto internedio più lontano (``_perpendicular_distance``);
    se quella distanza supera ``tolerance`` il punto è "keep" e si divide il
    segmento in due. Riduce il numero di punti preservando la forma della rotta.
    """
    n = len(points)
    if n <= 2:
        return points
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        start, end = stack.pop()
        if end <= start + 1:
            continue
        max_dist = 0.0
        index = start + 1
        for i in range(start + 1, end):
            d = _perpendicular_distance(points[i], points[start], points[end])
            if d > max_dist:
                max_dist = d
                index = i
        if max_dist > tolerance:
            keep[index] = True
            stack.append((start, index))
            stack.append((index, end))
    return [points[i] for i in range(n) if keep[i]]


def parse_gpx_file(content: str) -> list[dict]:
    import re
    import xml.etree.ElementTree as ET

    content = re.sub(r"<!DOCTYPE[^>]*?>", "", content, flags=re.IGNORECASE | re.DOTALL)
    root = ET.fromstring(content)  # noqa: S314
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


def parse_tcx_file(content: str) -> list[dict]:
    """Parse a TCX (Training Center XML) file into a list of GPS points.

    TCX stores ``<Trackpoint>`` elements with ``<Position>``
    (``LatitudeDegrees`` / ``LongitudeDegrees``), optional ``<AltitudeMeters>``,
    ``<Time>``, ``<DistanceMeters>`` and ``<HeartRateBpm>``. The output
    shape matches :func:`parse_gpx_file` so it can feed ``points_to_ride``.
    """
    import re
    import xml.etree.ElementTree as ET

    content = re.sub(r"<!DOCTYPE[^>]*?>", "", content, flags=re.IGNORECASE | re.DOTALL)
    try:
        root = ET.fromstring(content)  # noqa: S314
    except ET.ParseError:
        return []
    points = []
    for trkpt in root.iter():
        if trkpt.tag.split("}")[-1] != "Trackpoint":
            continue
        lat = lon = None
        altitude = None
        time_raw = None
        for child in trkpt:
            tag = child.tag.split("}")[-1]
            if tag == "Position":
                for pos in child:
                    ptag = pos.tag.split("}")[-1]
                    if ptag == "LatitudeDegrees":
                        lat = _safe_float(pos.text)
                    elif ptag == "LongitudeDegrees":
                        lon = _safe_float(pos.text)
            elif tag == "AltitudeMeters":
                altitude = _safe_float(child.text)
            elif tag == "Time":
                time_raw = child.text
        if lat is None or lon is None:
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        timestamp = None
        if time_raw:
            try:
                timestamp = datetime.fromisoformat(time_raw.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                timestamp = None
        if timestamp:
            points.append({"lat": lat, "lon": lon, "timestamp": timestamp, "altitude": altitude})
    return points


def _safe_float(value: str | None) -> float | None:
    """Parse an optional numeric XML text, returning ``None`` on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def points_to_ride(points: list[dict], name: str | None = None, weight_kg: float = 70.0, gps_tolerance: float | None = None, max_points: int | None = None) -> dict:
    if not points:
        return {"error": "No GPS points provided"}
    valid_points = [p for p in points if p.get("lat") is not None and p.get("lon") is not None and p.get("timestamp") is not None]
    if not valid_points:
        return {"error": "No valid GPS points provided"}
    tolerance = gps_tolerance if gps_tolerance is not None else float(os.getenv("GPS_DECIMATION_TOLERANCE", "0.00005"))
    compressed = douglas_peucker(valid_points, tolerance=tolerance)
    cap = max_points if max_points is not None else int(os.getenv("GPS_MAX_POINTS", "0") or 0)
    if cap > 0 and len(compressed) > cap:
        step = len(compressed) / cap
        compressed = [compressed[int(i * step)] for i in range(cap)] + [compressed[-1]]
    from ..models.models import haversine_distance_m

    total_distance = (
        sum(
            haversine_distance_m(compressed[i - 1]["lat"], compressed[i - 1]["lon"], p["lat"], p["lon"])
            for i, p in enumerate(compressed)
            if i > 0
        )
        if len(compressed) > 1
        else 0
    )
    duration_s = (compressed[-1]["timestamp"] - compressed[0]["timestamp"]).total_seconds() if len(compressed) > 1 else 0
    avg_speed = (total_distance / duration_s * 3.6) if duration_s > 0 else 0
    return {
        "date": compressed[0]["timestamp"].strftime("%Y-%m-%d") if compressed else "",
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
            for p in compressed
        ],
    }
