"""BikeMaster 2.0 - Data Agents (adapter da sorgenti esterne al dominio).

Ogni agente incapsula una sorgente dati (GPS, atleta, ambiente, sensori) e
la traduce in oggetti del Core Model già normalizzati tramite il
Transformer Engine. Gli algoritmi non vedono mai dati "grezzi".
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Optional

from .models import Activity, Athlete, WorldObject
from .transformer import GeoPoint, TransformerEngine
from .units import Quantity

__all__ = [
    "GPSAgent",
    "AthleteAgent",
    "EnvironmentAgent",
    "SensorAgent",
    "StravaAgent",
    "GarminAgent",
]


class GPSAgent:
    """Gestisce tracce GPS (coordinate, altitudine, timestamp)."""

    def __init__(self, transformer: TransformerEngine) -> None:
        self.t = transformer

    def collect(self, raw_points: list[dict], title: str = "") -> Activity:
        points: list[GeoPoint] = []
        for p in raw_points:
            ts = p.get("timestamp")
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            elif isinstance(ts, (int, float)):
                ts = datetime.fromtimestamp(ts, tz=timezone.utc)
            alt = self.t.normalize(Quantity(p.get("altitude", 0.0), "m",
                                             source=p.get("alt_source", "gps/dem")))
            points.append(GeoPoint(
                lat=float(p["lat"]), lon=float(p["lon"]),
                altitude=alt.value, timestamp=ts,
                x=0.0, y=0.0,
            ))
        return Activity(points=points, title=title)

    @classmethod
    def from_gpx(cls, transformer: TransformerEngine, text: str, title: str = "") -> Activity:
        root = ET.fromstring(text)
        ns = {"gpx": "http://www.topografix.com/GPX/1/1"}
        raw_points: list[dict] = []
        for trkpt in root.findall(".//gpx:trkpt", ns):
            ele = trkpt.find("gpx:ele", ns)
            time = trkpt.find("gpx:time", ns)
            raw_points.append({
                "lat": trkpt.get("lat", "0.0"),
                "lon": trkpt.get("lon", "0.0"),
                "altitude": ele.text if ele is not None and ele.text else "0.0",
                "timestamp": time.text if time is not None and time.text else None,
            })
        return cls(transformer).collect(raw_points, title=title)

    @classmethod
    def from_geojson(cls, transformer: TransformerEngine, data: dict[str, Any], title: str = "") -> Activity:
        raw_points: list[dict] = []
        for feat in data.get("features", []):
            geom = feat.get("geometry", {})
            if geom.get("type") != "Point":
                continue
            coords = geom.get("coordinates", [])
            if len(coords) < 2:
                continue
            props = feat.get("properties", {})
            raw_points.append({
                "lat": coords[1],
                "lon": coords[0],
                "altitude": coords[2] if len(coords) > 2 else 0.0,
                "timestamp": props.get("timestamp") or props.get("time"),
            })
        return cls(transformer).collect(raw_points, title=title)


class AthleteAgent:
    """Gestisce il corpo umano, le capacità e lo storico dell'atleta."""

    def __init__(self, transformer: TransformerEngine) -> None:
        self.t = transformer

    def collect(self, raw: dict) -> Athlete:
        return Athlete.from_raw(raw, self.t)


class EnvironmentAgent:
    """Gestisce meteo, terreno e condizioni ambientali."""

    def __init__(self, transformer: TransformerEngine) -> None:
        self.t = transformer

    def collect(self, raw: dict) -> WorldObject:
        return WorldObject.from_raw(raw, self.t)


class SensorAgent:
    """Estrae grandezze da sensori esterni (cardio, potenza, cadenza)."""

    def __init__(self, transformer: TransformerEngine) -> None:
        self.t = transformer

    def enrich_points(self, activity: Activity, raw_samples: list[dict], match_by_timestamp: bool = True) -> Activity:
        if not match_by_timestamp or not activity.points:
            for i, sample in enumerate(raw_samples):
                if i >= len(activity.points):
                    break
                pt = activity.points[i]
                activity.points[i] = GeoPoint(
                    lat=pt.lat, lon=pt.lon, altitude=pt.altitude,
                    timestamp=pt.timestamp, x=pt.x, y=pt.y,
                    speed=sample.get("speed", pt.speed),
                    power=sample.get("power", pt.power),
                    heart_rate=sample.get("heart_rate", pt.heart_rate),
                    cadence=sample.get("cadence", pt.cadence),
                )
            return activity

        import bisect

        indexed_ts = [(i, p.timestamp) for i, p in enumerate(activity.points) if p.timestamp is not None]
        if not indexed_ts:
            return activity
        indices, gps_ts = zip(*indexed_ts)
        indices = list(indices)
        gps_ts = list(gps_ts)

        for sample in raw_samples:
            st = sample.get("timestamp")
            if st is None:
                continue
            if isinstance(st, str):
                st = datetime.fromisoformat(st.replace("Z", "+00:00"))
            elif isinstance(st, (int, float)):
                st = datetime.fromtimestamp(st, tz=timezone.utc)
            idx = bisect.bisect_left(gps_ts, st)
            candidates = []
            if idx < len(gps_ts):
                candidates.append(((gps_ts[idx] - st).total_seconds(), indices[idx]))
            if idx > 0:
                candidates.append(((st - gps_ts[idx - 1]).total_seconds(), indices[idx - 1]))
            if not candidates:
                continue
            _, best_idx = min(candidates, key=lambda x: x[0])
            pt = activity.points[best_idx]
            activity.points[best_idx] = GeoPoint(
                lat=pt.lat, lon=pt.lon, altitude=pt.altitude,
                timestamp=pt.timestamp, x=pt.x, y=pt.y,
                speed=sample.get("speed", pt.speed),
                power=sample.get("power", pt.power),
                heart_rate=sample.get("heart_rate", pt.heart_rate),
                cadence=sample.get("cadence", pt.cadence),
            )
        return activity

    def summarize(self, activity: Activity) -> dict:
        hrs = [p.heart_rate for p in activity.points if p.heart_rate is not None]
        pwrs = [p.power for p in activity.points if p.power is not None]
        cads = [p.cadence for p in activity.points if p.cadence is not None]
        speeds = [p.speed for p in activity.points if p.speed is not None]
        return {
            "heart_rate_avg_bpm": (sum(hrs) / len(hrs)) if hrs else None,
            "heart_rate_max_bpm": max(hrs) if hrs else None,
            "power_avg_w": (sum(pwrs) / len(pwrs)) if pwrs else None,
            "cadence_avg_rpm": (sum(cads) / len(cads)) if cads else None,
            "speed_avg_ms": (sum(speeds) / len(speeds)) if speeds else None,
            "samples_count": len(activity.points),
        }


class StravaAgent:
    """Adapter per attività Strava verso il Core Model."""

    def __init__(self, transformer: TransformerEngine) -> None:
        self.t = transformer

    def activity_from_raw(self, raw: dict[str, Any]) -> Activity:
        gps_points = raw.get("gps_points") or raw.get("points") or []
        summary = {
            "distance_km": raw.get("distance", 0) / 1000 if raw.get("distance") else 0,
            "duration_minutes": raw.get("moving_time", 0) / 60 if raw.get("moving_time") else 0,
            "avg_speed_kmh": raw.get("average_speed", 0) * 3.6 if raw.get("average_speed") else 0,
            "elevation_gain_m": raw.get("total_elevation_gain", 0) or 0,
            "heart_rate_avg": raw.get("average_heartrate"),
        }
        return Activity.from_raw({
            "gps_points": gps_points,
            "title": raw.get("name", ""),
            "sport": "cycling",
            "summary": summary,
        }, self.t)

    def athlete_from_raw(self, raw: dict[str, Any]) -> Athlete:
        return Athlete.from_raw(raw, self.t)


class GarminAgent:
    """Adapter per attività Garmin verso il Core Model."""

    def __init__(self, transformer: TransformerEngine) -> None:
        self.t = transformer

    def activity_from_raw(self, raw: dict[str, Any]) -> Activity:
        gps_points = raw.get("gps_points") or raw.get("points") or []
        avg_speed = raw.get("averageSpeed", 0) or 0
        summary = {
            "distance_km": raw.get("distance", 0) / 1000 if raw.get("distance") else 0,
            "duration_minutes": raw.get("duration", 0) / 60 if raw.get("duration") else 0,
            "avg_speed_kmh": avg_speed * 3.6 if avg_speed else 0,
            "elevation_gain_m": raw.get("elevationGain", 0) or 0,
            "heart_rate_avg": raw.get("averageHR") or raw.get("averageHeartRate"),
        }
        return Activity.from_raw({
            "gps_points": gps_points,
            "title": raw.get("activityName", ""),
            "sport": "cycling",
            "summary": summary,
        }, self.t)

    def athlete_from_raw(self, raw: dict[str, Any]) -> Athlete:
        return Athlete.from_raw(raw, self.t)
