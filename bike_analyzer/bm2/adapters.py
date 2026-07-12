"""Adapter che collega il flusso prodotto (Ride / AthleteProfile) al motore bm2.

Il prodotto modella i dati con ``bike_analyzer.core.models`` (``Ride`` con
``gps_points: list[GPSPoint]`` e ``AthleteProfile``), mentre ``bm2`` usa il suo
dominio proprio (``AnalysisContext`` costruito via ``from_raw``). Questo modulo
è l'unico punto in cui le due rappresentazioni si incontrano, così il resto di
``bm2`` resta ignorante del prodotto.
"""

from __future__ import annotations

from typing import Optional

from ..core.models import AthleteProfile, GPSPoint, Ride
from .models import AnalysisContext
from .transformer import TransformerEngine


def _iso(ts) -> Optional[str]:
    if ts is None:
        return None
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    return str(ts)


def _gps_to_raw(p: GPSPoint) -> dict:
    return {
        "lat": p.lat,
        "lon": p.lon,
        "altitude": p.altitude,
        "timestamp": _iso(p.timestamp),
        "speed": p.speed,
        "power": p.power,
        "heart_rate": p.heart_rate,
        "cadence": p.cadence,
    }


def ride_to_bm2_raw(
    ride: Ride,
    athlete: Optional[AthleteProfile] = None,
    bike_weight_kg: float = 8.0,
    cda: float = 0.40,
    crr: float = 0.005,
    drivetrain_efficiency: float = 0.97,
    wind_speed_ms: Optional[float] = None,
    temperature_c: Optional[float] = None,
    surface: str = "asphalt",
) -> dict:
    """Mappa una ``Ride`` prodotto (+ ``AthleteProfile``) nel dict ``raw`` di bm2.

    La pendenza media del ``WorldObject`` è derivata da
    ``elevation_gain_m / distance_km`` quando entrambi disponibili.
    """
    if not ride.gps_points:
        raise ValueError("Ride senza gps_points: impossibile costruire il contesto bm2")

    weight = (athlete.weight_kg if athlete and athlete.weight_kg else ride.weight_kg) or 70.0
    athlete_raw: dict = {"weight": weight, "source": "manual"}
    if athlete is not None:
        athlete_raw["age"] = athlete.age
        athlete_raw["experience_level"] = athlete.experience_level
        if athlete.ftp_watts is not None:
            athlete_raw["ftp"] = athlete.ftp_watts
            athlete_raw["ftp_source"] = "estimate"
        if athlete.height_cm:
            athlete_raw["height"] = athlete.height_cm / 100.0
            athlete_raw["height_unit"] = "m"

    bike_raw = {
        "weight": bike_weight_kg,
        "weight_unit": "kg",
        "cda": cda,
        "crr": crr,
        "drivetrain_efficiency": drivetrain_efficiency,
        "source": "manual",
    }

    world_raw: dict = {"surface": surface}
    if ride.elevation_gain_m and ride.distance_km and ride.distance_km > 0:
        avg_slope = (ride.elevation_gain_m / (ride.distance_km * 1000.0)) * 100.0
        world_raw["avg_slope"] = avg_slope
        world_raw["avg_slope_unit"] = "%"
        world_raw["source"] = "gps"
    if wind_speed_ms is not None:
        world_raw["wind_speed"] = wind_speed_ms
    if temperature_c is not None:
        world_raw["temperature"] = temperature_c

    return {
        "athlete": athlete_raw,
        "bike": bike_raw,
        "world": world_raw,
        "gps_points": [_gps_to_raw(p) for p in ride.gps_points],
    }


def ride_to_analysis_context(
    ride: Ride,
    athlete: Optional[AthleteProfile] = None,
    transformer: Optional[TransformerEngine] = None,
    **kwargs,
) -> AnalysisContext:
    """Costruisce direttamente un ``AnalysisContext`` bm2 da una ``Ride`` prodotto."""
    t = transformer or TransformerEngine()
    raw = ride_to_bm2_raw(ride, athlete, **kwargs)
    return AnalysisContext.from_raw(raw, t)
