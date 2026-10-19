"""Fatigue calculator.

Estimates fatigue score (0-10) from ride characteristics using weighted
factors: duration, heart rate intensity, speed, elevation, and rider weight.
Also provides recovery hour estimates and textual recommendations.
"""

from __future__ import annotations

from bike_analyzer.core.models import Ride


def calculate_fatigue_score(ride: Ride, rider_age: int = 35) -> float:
    """Score di fatica (0-10) combinando durata, FC, velocita', dislivello e peso.

    Five weighted factors (sum of weights = 1.0):
    - Duration factor (0.30): min(hours/2, 3.0) -> caps at 3h
    - Intensity factor (0.30): from HR% of max (220 - age)
    - Speed factor (0.20): min(speed/25, 2.0)
    - Elevation factor (0.10): gain/distance ratio, capped at 1.0
    - Weight factor (0.10): weight/70kg ratio

    The weighted sum is multiplied by 3.0 and clamped to [0, 10].

    Args:
        ride: Cycling activity with duration_minutes, heart_rate_avg,
              avg_speed_kmh, elevation_gain_m, distance_km, weight_kg.
        rider_age: Age in years for max HR estimation (default 35).

    Returns:
        Fatigue score from 0.0 (fresh) to 10.0 (exhausted).
    """
    duration_h = ride.duration_hours
    hr_avg = ride.heart_rate_avg
    # Duration factor: scales linearly up to 2h, caps at 3.0 for longer rides
    DURATION_FACTOR = min(duration_h / 2.0, 3.0)
    if hr_avg:
        hr_pct = hr_avg / (220 - rider_age) if rider_age < 220 else 0.5
        # Intensity factor: 0.5 at 50% HRmax, ramps to 1.0 at 85%+, plateau beyond
        INTENSITY_FACTOR = (
            0.5 if hr_pct <= 0.5 else 0.5 + (hr_pct - 0.5) * 2.0 if hr_pct <= 0.85 else 1.0
        )
    else:
        INTENSITY_FACTOR = 1.0
    SPEED_FACTOR = min(ride.avg_speed_kmh / 25.0, 2.0)
    # Elevation factor: normalized by distance, capped at 1.0
    ELEV_FACTOR = (
        1.0 + min((ride.elevation_gain_m / ride.distance_km) / 20.0, 1.0)
        if ride.elevation_gain_m and ride.distance_km and ride.distance_km > 0
        else 1.0
    )
    WEIGHT_FACTOR = ride.weight_kg / 70.0
    return min(
        (DURATION_FACTOR * 0.3 + INTENSITY_FACTOR * 0.3 + SPEED_FACTOR * 0.2 + ELEV_FACTOR * 0.1 + WEIGHT_FACTOR * 0.1)
        * 3.0,
        10.0,
    )


def estimate_recovery_hours(fatigue_score: float) -> float:
    """Stima ore di recupero necessarie in base allo score di fatica.

    Thresholds:
    - <= 3.0: 8h
    - <= 5.0: 16h
    - <= 7.0: 24h
    - > 7.0: 48h

    Args:
        fatigue_score: Fatigue score from 0 to 10.

    Returns:
        Estimated recovery hours.
    """
    if fatigue_score <= 3.0:
        return 8.0
    if fatigue_score <= 5.0:
        return 16.0
    if fatigue_score <= 7.0:
        return 24.0
    return 48.0


def get_recovery_recommendation(fatigue_score: float) -> str:
    """Raccomandazione testuale di recupero in base al livello di fatica.

    Args:
        fatigue_score: Fatigue score from 0 to 10.

    Returns:
        Human-readable recovery recommendation string.
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
