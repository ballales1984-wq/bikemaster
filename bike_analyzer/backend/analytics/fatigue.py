"""Modello di fatica post-uscita per il coach digitale.

Calcola uno score 0-10 basato su una combinazione pesata di durata,
intensita' cardio (HR%), velocita', dislivello e peso del ciclista.
Espone anche la stima delle ore di recupero e un suggerimento testuale
per la schedulazione del giorno successivo.
"""

from __future__ import annotations

from ..models.models import Ride
from .error_propagation import ErrorValue


def calculate_fatigue_score(ride: Ride, rider_age: int = 35) -> float:
    """Wrapper senza propagazione d'errore: ritorna solo il valore.

    Per analisi con confidenza, usare :func:`calculate_fatigue_score_with_error`.
    """
    result = calculate_fatigue_score_with_error(ride, rider_age)
    return round(result.value, 1)


def calculate_fatigue_score_with_error(ride: Ride, rider_age: int = 35) -> ErrorValue:
    """Calcola fatigue score 0-10 con propagazione d'errore.

    Fattori e pesi:
        - Duration (30%): normalizzato a 2h, clamp a 3x.
        - Intensity (30%): da %HRmax = HR/(220-age) con curva a 3 spezzoni
          (fino a 50% neutro, 50-85% lineare, >85% ripida).
        - Speed (20%): normalizzato a 25 km/h, clamp a 2x.
        - Elevation (10%): gradient ratio gain/km normalizzato a 20.
        - Weight (10%): kg/70.

    Score finale clamp a 10. ``coverage`` = 1 - missing_fields/4, dove i
    field opzionali sono duration/HR/speed/elevation. Piu' field mancano,
    piu' l'errore statistico cresce (fino a 2x).
    """
    duration_h = ride.duration_hours or 0
    hr_avg = ride.heart_rate_avg
    DURATION_FACTOR = min(duration_h / 2.0, 3.0)
    if hr_avg:
        hr_pct = hr_avg / (220 - rider_age) if rider_age < 220 else 0.5
        INTENSITY_FACTOR = (
            0.5 if hr_pct <= 0.5 else 0.5 + (hr_pct - 0.5) * 2.0 if hr_pct <= 0.85 else 1.5 + (hr_pct - 0.85) * 3.33
        )
    else:
        INTENSITY_FACTOR = 1.0
    speed = ride.avg_speed_kmh or 0
    SPEED_FACTOR = min(speed / 25.0, 2.0)
    ELEV_FACTOR = (
        1.0 + min((ride.elevation_gain_m / ride.distance_km) / 20.0, 1.0)
        if ride.elevation_gain_m and ride.distance_km and ride.distance_km > 0
        else 1.0
    )
    WEIGHT_FACTOR = ride.weight_kg / 70.0
    fatigue_value = min(
        (DURATION_FACTOR * 0.3 + INTENSITY_FACTOR * 0.3 + SPEED_FACTOR * 0.2 + ELEV_FACTOR * 0.1 + WEIGHT_FACTOR * 0.1)
        * 3.0,
        10.0,
    )

    missing = 0
    if not ride.duration_minutes:
        missing += 1
    if not ride.heart_rate_avg:
        missing += 1
    if not ride.avg_speed_kmh:
        missing += 1
    if not ride.elevation_gain_m:
        missing += 1
    coverage = 1.0 - missing / 4.0

    base_stat_error = 0.3
    if coverage < 1.0:
        base_stat_error *= 2.0 - coverage
    base_stat_error = min(base_stat_error, 1.0)

    return ErrorValue(
        value=round(fatigue_value, 1),
        stat_error=round(base_stat_error, 4),
        resolution_error=0.1,
        coverage=coverage,
    )


def estimate_recovery_hours(fatigue_score: float) -> float:
    """Stima le ore di recupero necessarie in base al fatigue score.

    Soglie a gradino (modello semplificato, non esponenziale):
        <= 3 -> 8h, <= 5 -> 16h, <= 7 -> 24h, altrimenti 48h.
    """
    if fatigue_score <= 3.0:
        return 8.0
    if fatigue_score <= 5.0:
        return 16.0
    if fatigue_score <= 7.0:
        return 24.0
    return 48.0


def get_recovery_recommendation(fatigue_score: float) -> str:
    """Restituisce una raccomandazione di recupero human-readable per il coach.

    Soglie graduate a partire da fatigue <= 2 (fatica minima) fino a >8
    (fatica estrema con piu' giorni di riposo consigliati).
    """
    if fatigue_score <= 2.0:
        return "Minimal fatigue"
    if fatigue_score <= 4.0:
        return "Light fatigue - easy spin or rest recommended"
    if fatigue_score <= 6.0:
        return "Moderate fatigue - rest day recommended"
    if fatigue_score <= 8.0:
        return "High fatigue - rest required"
    return "Extreme fatigue - multiple rest days recommended"


__all__ = [
    "calculate_fatigue_score",
    "calculate_fatigue_score_with_error",
    "estimate_recovery_hours",
    "get_recovery_recommendation",
]
