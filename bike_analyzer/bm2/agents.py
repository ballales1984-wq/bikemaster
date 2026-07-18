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
    """Gestisce tracce GPS (coordinate, altitudine, timestamp).

    Converte dati GPS grezzi (dict, GPX, GeoJSON) in oggetti ``Activity``
    del Core Model, normalizzando timestamp e unita' tramite il Transformer.
    """

    def __init__(self, transformer: TransformerEngine) -> None:
        """Inizializza l'agente con il TransformerEngine per la normalizzazione.

        Args:
            transformer: Motore di trasformazione unita' e coordinate.
        """
        self.t = transformer

    def collect(self, raw_points: list[dict], title: str = "") -> Activity:
        """Converte una lista di dict GPS in un'``Activity``.

        Accetta punti con chiavi: ``lat``, ``lon``, ``altitude``, ``timestamp``
        (ISO string, Unix epoch, o datetime). I timestamp sono normalizzati a
        UTC naive.

        Args:
            raw_points: Lista di dict con dati GPS raw.
            title: Titolo opzionale per l'attivita'.

        Returns:
            Activity con i punti GeoPoint normalizzati.
        """
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
        """Costruisce un'``Activity`` dal contenuto XML di un file GPX 1.1.

        Estrae tutti i ``trkpt`` dal file GPX usando il namespace ufficiale
        ``http://www.topografix.com/GPX/1/1`` e converte altitudine e timestamp.

        Args:
            transformer: Motore di trasformazione unita'.
            text: Contenuto XML del file GPX.
            title: Titolo opzionale per l'attivita'.

        Returns:
            Activity con la traccia GPX parsata.
        """
        root = ET.fromstring(text)
        ns = {"gpx": "http://www.topografix.com/GPX/1/1"}
        raw_points: list[dict] = []
        for trkpt in root.findall(".//gpx:trkpt", ns):
            ele = trkpt.find("gpx:ele", ns)
            time = trkpt.find("gpx:time", ns)
            raw_points.append({
                "lat": trkpt.get("lat", "0.0"),
                "lon": trkpt.get("lon", "0.0"),
                "altitude": float(ele.text) if ele is not None and ele.text else 0.0,
                "timestamp": time.text if time is not None and time.text else None,
            })
        return cls(transformer).collect(raw_points, title=title)

    @classmethod
    def from_geojson(cls, transformer: TransformerEngine, data: dict[str, Any], title: str = "") -> Activity:
        """Costruisce un'``Activity`` da un FeatureCollection GeoJSON di punti.

        Considera solo le ``Feature`` con ``geometry.type == "Point"``; i
        timestamp sono letti da ``properties.timestamp`` o ``properties.time``.

        Args:
            transformer: Motore di trasformazione unita'.
            data: Dict GeoJSON con chiave ``features``.
            title: Titolo opzionale per l'attivita'.

        Returns:
            Activity con i punti GeoPoint estratti dal GeoJSON.
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
            raw_points.append({
                "lat": coords[1],
                "lon": coords[0],
                "altitude": coords[2] if len(coords) > 2 else 0.0,
                "timestamp": props.get("timestamp") or props.get("time"),
            })
        return cls(transformer).collect(raw_points, title=title)


class AthleteAgent:
    """Gestisce il corpo umano, le capacita' e lo storico dell'atleta.

    Trasforma dati raw dell'atleta in oggetti ``Athlete`` del Core Model
    tramite ``Athlete.from_raw`` e il TransformerEngine.
    """

    def __init__(self, transformer: TransformerEngine) -> None:
        """Inizializza con il TransformerEngine per la normalizzazione.

        Args:
            transformer: Motore di trasformazione unita'.
        """
        self.t = transformer

    def collect(self, raw: dict) -> Athlete:
        """Costruisce un ``Athlete`` da un dict di dati raw.

        Args:
            raw: Dizionario con dati atleta (peso, FTP, eta', ecc.).

        Returns:
            Athlete normalizzato tramite TransformerEngine.
        """
        return Athlete.from_raw(raw, self.t)


class EnvironmentAgent:
    """Gestisce meteo, terreno e condizioni ambientali.

    Trasforma dati ambientali raw in ``WorldObject`` del Core Model.
    """

    def __init__(self, transformer: TransformerEngine) -> None:
        """Inizializza con il TransformerEngine per la normalizzazione.

        Args:
            transformer: Motore di trasformazione unita'.
        """
        self.t = transformer

    def collect(self, raw: dict) -> WorldObject:
        """Costruisce un ``WorldObject`` da un dict di dati ambientali raw.

        Args:
            raw: Dizionario con superficie, pendenza, vento, temperatura, ecc.

        Returns:
            WorldObject normalizzato tramite TransformerEngine.
        """
        return WorldObject.from_raw(raw, self.t)


class SensorAgent:
    """Estrae grandezze da sensori esterni (cardio, potenza, cadenza).

    Arricchisce i punti di un'``Activity`` con dati di sensori esterni,
    abbinando i campioni per timestamp o per indice sequenziale.
    """

    def __init__(self, transformer: TransformerEngine) -> None:
        """Inizializza con il TransformerEngine.

        Args:
            transformer: Motore di trasformazione unita'.
        """
        self.t = transformer

    def enrich_points(self, activity: Activity, raw_samples: list[dict], match_by_timestamp: bool = True) -> Activity:
        """Arricchisce i punti dell'attivita' con dati di sensore.

        Se ``match_by_timestamp`` e' True, abbina ogni campione al punto GPS
        piu' vicino temporalmente usando ricerca binaria (``bisect``).
        Altrimenti associa per indice sequenziale (primo campione -> primo punto,
        ecc.).

        Args:
            activity: Activity da arricchire (modificata in-place).
            raw_samples: Lista di dict con ``speed``, ``power``,
                ``heart_rate``, ``cadence`` e ``timestamp`` opzionale.
            match_by_timestamp: Se True, abbina per timestamp anziche' per indice.

        Returns:
            La stessa Activity modificata con i valori dei sensori inseriti.
        """
        if not match_by_timestamp or not activity.points:
            # Abbinamento sequenziale: primo campione -> primo punto, ecc.
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

        # Ricerca binaria per trovare il punto GPS piu' vicino al timestamp
        # del campione del sensore.
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
        """Calcola le statistiche riepilogative dell'attivita'.

        Calcola medie per heart_rate, power, cadence e speed considerando
        solo i punti con valore non-None.

        Args:
            activity: Activity da riassumere.

        Returns:
            Dizionario con medie e conteggio campioni per ogni metrica.
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
    """Adapter per attivita' Strava verso il Core Model.

    Converte il payload JSON dell'API Strava in ``Activity`` e ``Athlete``
    del Core Model, mappando i campi specifici di Strava (``moving_time``,
    ``total_elevation_gain``, ``average_speed``, ecc.) nel formato raw
    atteso da ``from_raw``.
    """

    def __init__(self, transformer: TransformerEngine) -> None:
        """Inizializza con il TransformerEngine.

        Args:
            transformer: Motore di trasformazione unita'.
        """
        self.t = transformer

    def activity_from_raw(self, raw: dict[str, Any]) -> Activity:
        """Converte il payload di un'attivita' Strava in ``Activity``.

        Args:
            raw: Dict con chiavi Strava (``gps_points``, ``moving_time``,
                ``total_elevation_gain``, ``average_speed``, ``name``, ecc.).

        Returns:
            Activity normalizzata con dati Strava mappati.
        """
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
        """Converte i dati profilo atleta Strava in ``Athlete``.

        Args:
            raw: Dict con dati atleta da Strava.

        Returns:
            Athlete normalizzato.
        """
        return Athlete.from_raw(raw, self.t)


class GarminAgent:
    """Adapter per attivita' Garmin verso il Core Model.

    Converte il payload JSON dell'API Garmin in ``Activity`` e ``Athlete``
    del Core Model, mappando i campi specifici Garmin (``averageSpeed``,
    ``elevationGain``, ``duration``, ecc.) nel formato raw atteso da
    ``from_raw``.
    """

    def __init__(self, transformer: TransformerEngine) -> None:
        """Inizializza con il TransformerEngine.

        Args:
            transformer: Motore di trasformazione unita'.
        """
        self.t = transformer

    def activity_from_raw(self, raw: dict[str, Any]) -> Activity:
        """Converte il payload di un'attivita' Garmin in ``Activity``.

        Args:
            raw: Dict con chiavi Garmin (``gps_points``, ``duration``,
                ``elevationGain``, ``averageSpeed``, ``activityName``, ecc.).

        Returns:
            Activity normalizzata con dati Garmin mappati.
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
        return Activity.from_raw({
            "gps_points": gps_points,
            "title": raw.get("activityName", ""),
            "sport": "cycling",
            "summary": summary,
        }, self.t)

    def athlete_from_raw(self, raw: dict[str, Any]) -> Athlete:
        return Athlete.from_raw(raw, self.t)
