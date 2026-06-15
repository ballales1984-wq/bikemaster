"""Fatigue calculator."""

from __future__ import annotations

from ....core.models import Ride


def calculate_fatigue_score(ride: Ride, rider_age: int = 35) -> float:
    duration_h = ride.duration_hours
    hr_avg = ride.heart_rate_avg
    DURATION_FACTOR = min(duration_h / 2.0, 3.0)
    if hr_avg:
        hr_pct = hr_avg / (220 - rider_age) if rider_age < 220 else 0.5
        INTENSITY_FACTOR = (
            0.5
            if hr_pct <= 0.5
            else 0.5 + (hr_pct - 0.5) * 2.0
            if hr_pct <= 0.85
            else 1.5 + (hr_pct - 0.85) * 3.33
        )
    else:
        INTENSITY_FACTOR = 1.0
    SPEED_FACTOR = min(ride.avg_speed_kmh / 25.0, 2.0)
    ELEV_FACTOR = (
        1.0 + min((ride.elevation_gain_m / ride.distance_km) / 20.0, 1.0)
        if ride.elevation_gain_m and ride.distance_km and ride.distance_km > 0
        else 1.0
    )
    WEIGHT_FACTOR = ride.weight_kg / 70.0
    return min(
        (
            DURATION_FACTOR * 0.3
            + INTENSITY_FACTOR * 0.3
            + SPEED_FACTOR * 0.2
            + ELEV_FACTOR * 0.1
            + WEIGHT_FACTOR * 0.1
        )
        * 3.0,
        10.0,
    )


def estimate_recovery_hours(fatigue_score: float) -> float:
    if fatigue_score <= 3.0:
        return 8.0
    if fatigue_score <= 5.0:
        return 16.0
    if fatigue_score <= 7.0:
        return 24.0
    return 48.0


def get_recovery_recommendation(fatigue_score: float) -> str:
    if fatigue_score <= 2.0:
        return "Minimal fatigue"
    if fatigue_score <= 4.0:
        return "Light fatigue - easy spin or rest recommended"
    if fatigue_score <= 6.0:
        return "Moderate fatigue - rest day recommended"
    if fatigue_score <= 8.0:
        return "High fatigue - rest required"
    return "Extreme fatigue - multiple rest days recommended"
