"""BikeMaster 2.0 - Data Agents (adapters from external sources to the domain).

Each agent encapsulates a data source (GPS, athlete, environment, sensors) and
    translates it into Core Model objects already normalized via the
    Transformer Engine. Algorithms never see "raw" data.
"""

from __future__ import annotations

import defusedxml.ElementTree as ET
from datetime import UTC, datetime
from typing import Any

from .metabolism_agent import MetabolismAgent
from .models import Activity, Athlete, WorldObject
from .transformer import GeoPoint, TransformerEngine
from .units import Quantity

__all__ = [
    "GPSAgent",
    "AthleteAgent",
    "EnvironmentAgent",
    "SensorAgent",
    "MetabolismAgent",
    "StravaAgent",
    "GarminAgent",
]


class GPSAgent:
    """Manages GPS tracks (coordinates, altitude, timestamps).

    Converts raw GPS data (dict, GPX, GeoJSON) into Core Model ``Activity``
    objects, normalizing timestamps and units via the Transformer.
    """

    def __init__(self, transformer: TransformerEngine) -> None:
        """Initializes the agent with the TransformerEngine for normalization.

        Args:
            transformer: Unit and coordinate transformation engine.
        """
        self.t = transformer

    def collect(self, raw_points: list[dict], title: str = "") -> Activity:
        """Converts a list of GPS dicts into an ``Activity``.

        Accepts points with keys: ``lat``, ``lon``, ``altitude``, ``timestamp``
        (ISO string, Unix epoch, or datetime). Timestamps are normalized to
        naive UTC.

        Args:
            raw_points: List of dicts with raw GPS data.
            title: Optional title for the activity.

        Returns:
            Activity with normalized GeoPoint points.
        """
        points: list[GeoPoint] = []
        for p in raw_points:
            ts = p.get("timestamp")
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            elif isinstance(ts, (int, float)):
                ts = datetime.fromtimestamp(ts, tz=UTC)
            alt = self.t.normalize(Quantity(p.get("altitude", 0.0), "m", source=p.get("alt_source", "gps/dem")))
            points.append(
                GeoPoint(
                    lat=float(p["lat"]),
                    lon=float(p["lon"]),
                    altitude=alt.value,
                    timestamp=ts,
                    x=0.0,
                    y=0.0,
                )
            )
        return Activity(points=points, title=title)

    @classmethod
    def from_gpx(cls, transformer: TransformerEngine, text: str, title: str = "") -> Activity:
        """Builds an ``Activity`` from the XML content of a GPX 1.1 file.

        Estrae tutti i ``trkpt`` dal file GPX usando il namespace ufficiale
        ``http://www.topografix.com/GPX/1/1`` e converte altitudine e timestamp.

        Args:
            transformer: Unit transformation engine.
            text: XML content of the GPX file.
            title: Optional title for the activity.

        Returns:
            Activity with parsed GPX track.
        """
        root = ET.fromstring(text)
        ns = {"gpx": "http://www.topografix.com/GPX/1/1"}
        raw_points: list[dict] = []
        for trkpt in root.findall(".//gpx:trkpt", ns):
            ele = trkpt.find("gpx:ele", ns)
            time = trkpt.find("gpx:time", ns)
            raw_points.append(
                {
                    "lat": trkpt.get("lat", "0.0"),
                    "lon": trkpt.get("lon", "0.0"),
                    "altitude": float(ele.text) if ele is not None and ele.text else 0.0,
                    "timestamp": time.text if time is not None and time.text else None,
                }
            )
        return cls(transformer).collect(raw_points, title=title)

    @classmethod
    def from_geojson(cls, transformer: TransformerEngine, data: dict[str, Any], title: str = "") -> Activity:
        """Builds an ``Activity`` from a GeoJSON Point FeatureCollection.

        Considera solo le ``Feature`` con ``geometry.type == "Point"``; i
        timestamp sono letti da ``properties.timestamp`` o ``properties.time``.

        Args:
            transformer: Unit transformation engine.
            data: GeoJSON dict with ``features`` key.
            title: Optional title for the activity.

        Returns:
            Activity with GeoPoint points extracted from GeoJSON.
        """
        raw_points: list[dict] = []
        for feat in data.get("features", []):
            geom = feat.get("geometry", {})
            if geom.get("type") != "Point":
                continue
            coords = geom.get("coordinates", [])
            if len(coords) < 2:
                continue
            props = feat.get("properties", {})
            raw_points.append(
                {
                    "lat": coords[1],
                    "lon": coords[0],
                    "altitude": coords[2] if len(coords) > 2 else 0.0,
                    "timestamp": props.get("timestamp") or props.get("time"),
                }
            )
        return cls(transformer).collect(raw_points, title=title)


class AthleteAgent:
    """Manages the human body, its capabilities and the athlete's history.

    Transforms raw athlete data into Core Model ``Athlete`` objects
    via ``Athlete.from_raw`` and the TransformerEngine.
    """

    def __init__(self, transformer: TransformerEngine) -> None:
        """Initializes with the TransformerEngine for normalization.

        Args:
            transformer: Unit transformation engine.
        """
        self.t = transformer

    def collect(self, raw: dict) -> Athlete:
        """Builds an ``Athlete`` from a raw data dict.

        Args:
            raw: Dictionary with athlete data (weight, FTP, age, etc.).

        Returns:
            Athlete normalized via TransformerEngine.
        """
        return Athlete.from_raw(raw, self.t)


class EnvironmentAgent:
    """Manages weather, terrain and environmental conditions.

    Transforms raw environmental data into Core Model ``WorldObject``.
    """

    def __init__(self, transformer: TransformerEngine) -> None:
        """Initializes with the TransformerEngine for normalization.

        Args:
            transformer: Unit transformation engine.
        """
        self.t = transformer

    def collect(self, raw: dict) -> WorldObject:
        """Builds a ``WorldObject`` from a raw environmental data dict.

        Args:
            raw: Dictionary with surface, slope, wind, temperature, etc.

        Returns:
            WorldObject normalized via TransformerEngine.
        """
        return WorldObject.from_raw(raw, self.t)


class SensorAgent:
    """Extracts quantities from external sensors (HR, power, cadence).

    Arricchisce i punti di un'``Activity`` con dati di sensori esterni,
    abbinando i campioni per timestamp o per indice sequenziale.
    """

    def __init__(self, transformer: TransformerEngine) -> None:
        """Inizializza con il TransformerEngine.

        Args:
            transformer: Unit transformation engine.
        """
        self.t = transformer

    def enrich_points(self, activity: Activity, raw_samples: list[dict], match_by_timestamp: bool = True) -> Activity:
        """Enriches activity points with sensor data.

        Se ``match_by_timestamp`` e' True, abbina ogni campione al punto GPS
        piu' vicino temporalmente usando ricerca binaria (``bisect``).
        Altrimenti associa per indice sequenziale (primo campione -> primo punto,
        ecc.).

        Args:
            activity: Activity to enrich (modified in-place).
            raw_samples: Lista di dict con ``speed``, ``power``,
                ``heart_rate``, ``cadence`` e ``timestamp`` opzionale.
            match_by_timestamp: If True, match by timestamp instead of index.

        Returns:
            The same Activity modified with inserted sensor values.
        """
        if not match_by_timestamp or not activity.points:
            # Abbinamento sequenziale: primo campione -> primo punto, ecc.
            for i, sample in enumerate(raw_samples):
                if i >= len(activity.points):
                    break
                pt = activity.points[i]
                activity.points[i] = GeoPoint(
                    lat=pt.lat,
                    lon=pt.lon,
                    altitude=pt.altitude,
                    timestamp=pt.timestamp,
                    x=pt.x,
                    y=pt.y,
                    speed=sample.get("speed", pt.speed),
                    power=sample.get("power", pt.power),
                    heart_rate=sample.get("heart_rate", pt.heart_rate),
                    cadence=sample.get("cadence", pt.cadence),
                )
            return activity

        # Ricerca binaria per trovare il punto GPS piu' vicino al timestamp
        # del campione del sensore.
        import bisect

        indexed_ts = [(i, p.timestamp) for i, p in enumerate(activity.points) if p.timestamp is not None]
        if not indexed_ts:
            return activity
        indices, gps_ts = zip(*indexed_ts, strict=False)
        indices = list(indices)
        gps_ts = list(gps_ts)

        for sample in raw_samples:
            st = sample.get("timestamp")
            if st is None:
                continue
            if isinstance(st, str):
                st = datetime.fromisoformat(st.replace("Z", "+00:00"))
            elif isinstance(st, (int, float)):
                st = datetime.fromtimestamp(st, tz=UTC)
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
                lat=pt.lat,
                lon=pt.lon,
                altitude=pt.altitude,
                timestamp=pt.timestamp,
                x=pt.x,
                y=pt.y,
                speed=sample.get("speed", pt.speed),
                power=sample.get("power", pt.power),
                heart_rate=sample.get("heart_rate", pt.heart_rate),
                cadence=sample.get("cadence", pt.cadence),
            )
        return activity

    def summarize(self, activity: Activity) -> dict:
        """Calculates summary statistics for the activity.

        Calcola medie per heart_rate, power, cadence e speed considerando
        solo i punti con valore non-None.

        Args:
            activity: Activity da riassumere.

        Returns:
            Dictionary with averages and sample counts for each metric.
        """
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
    """Adapter for Strava activities to the Core Model.

    Converts the Strava API JSON payload into Core Model ``Activity`` and ``Athlete``
    objects, mapping Strava-specific fields (``moving_time``,
    ``total_elevation_gain``, ``average_speed``, etc.) to the raw format
    expected by ``from_raw``.
    """

    def __init__(self, transformer: TransformerEngine) -> None:
        """Inizializza con il TransformerEngine.

        Args:
            transformer: Unit transformation engine.
        """
        self.t = transformer

    def activity_from_raw(self, raw: dict[str, Any]) -> Activity:
        """Converts a Strava activity payload into ``Activity``.

        Args:
            raw: Dict with Strava keys (``gps_points``, ``moving_time``,
                ``total_elevation_gain``, ``average_speed``, ``name``, etc.).

        Returns:
            Activity normalized with mapped Strava data.
        """
        gps_points = raw.get("gps_points") or raw.get("points") or []
        summary = {
            "distance_km": raw.get("distance", 0) / 1000 if raw.get("distance") else 0,
            "duration_minutes": raw.get("moving_time", 0) / 60 if raw.get("moving_time") else 0,
            "avg_speed_kmh": raw.get("average_speed", 0) * 3.6 if raw.get("average_speed") else 0,
            "elevation_gain_m": raw.get("total_elevation_gain", 0) or 0,
            "heart_rate_avg": raw.get("average_heartrate"),
        }
        return Activity.from_raw(
            {
                "gps_points": gps_points,
                "title": raw.get("name", ""),
                "sport": "cycling",
                "summary": summary,
            },
            self.t,
        )

    def athlete_from_raw(self, raw: dict[str, Any]) -> Athlete:
        """Converts Strava athlete profile data into ``Athlete``.

        Args:
            raw: Dict with athlete data from Strava.

        Returns:
            Normalized Athlete.
        """
        return Athlete.from_raw(raw, self.t)


class GarminAgent:
    """Adapter for Garmin activities to the Core Model.

    Converts the Garmin API JSON payload into Core Model ``Activity`` and ``Athlete``
    objects, mapping Garmin-specific fields (``averageSpeed``,
    ``elevationGain``, ``duration``, etc.) to the raw format expected by
    ``from_raw``.
    """

    def __init__(self, transformer: TransformerEngine) -> None:
        """Inizializza con il TransformerEngine.

        Args:
            transformer: Unit transformation engine.
        """
        self.t = transformer

    def activity_from_raw(self, raw: dict[str, Any]) -> Activity:
        """Converts a Garmin activity payload into ``Activity``.

        Args:
            raw: Dict with Garmin keys (``gps_points``, ``duration``,
                ``elevationGain``, ``averageSpeed``, ``activityName``, etc.).

        Returns:
            Activity normalized with mapped Garmin data.
        """
        gps_points = raw.get("gps_points") or raw.get("points") or []
        avg_speed = raw.get("averageSpeed", 0) or 0
        summary = {
            "distance_km": raw.get("distance", 0) / 1000 if raw.get("distance") else 0,
            "duration_minutes": raw.get("duration", 0) / 60 if raw.get("duration") else 0,
            "avg_speed_kmh": avg_speed * 3.6 if avg_speed else 0,
            "elevation_gain_m": raw.get("elevationGain", 0) or 0,
            "heart_rate_avg": raw.get("averageHR") or raw.get("averageHeartRate"),
        }
        return Activity.from_raw(
            {
                "gps_points": gps_points,
                "title": raw.get("activityName", ""),
                "sport": "cycling",
                "summary": summary,
            },
            self.t,
        )

    def athlete_from_raw(self, raw: dict[str, Any]) -> Athlete:
        return Athlete.from_raw(raw, self.t)
