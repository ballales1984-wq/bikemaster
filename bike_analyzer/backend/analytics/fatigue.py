"""Fatigue model for cycling performance intelligence."""
from __future__ import annotations
from ..models.models import Ride

def calculate_fatigue_score(ride: Ride, rider_age: int = 35) -> float:
    dur_f = min(ride.duration_hours / 2.0, 3.0)
    int_f, spd_f, elev_f, wgt_f = 1.0, min(ride.avg_speed_kmh / 25.0, 2.0), 1.0, ride.weight_kg / 70.0
    if ride.heart_rate_avg:
        pct = ride.heart_rate_avg / (220 - rider_age)
        int_f = 0.5 if pct <= 0.5 else 0.5 + (pct - 0.5) * 2.0 if pct <= 0.85 else 1.5 + (pct - 0.85) * 3.33
    if ride.elevation_gain_m and ride.distance_km > 0: elev_f = 1.0 + min((ride.elevation_gain_m / ride.distance_km) / 20.0, 1.0)
    return min((dur_f * 0.3 + int_f * 0.3 + spd_f * 0.2 + elev_f * 0.1 + wgt_f * 0.1) * 3.0, 10.0)

def estimate_recovery_hours(fatigue_score: float) -> float:
    return 8.0 if fatigue_score <= 3.0 else 16.0 if fatigue_score <= 5.0 else 24.0 if fatigue_score <= 7.0 else 48.0

def get_recovery_recommendation(fatigue_score: float) -> str:
    if fatigue_score <= 2.0: return "Minimal fatigue - ready for another ride"
    if fatigue_score <= 4.0: return "Light fatigue - easy recovery ride or rest recommended"
    if fatigue_score <= 6.0: return "Moderate fatigue - rest day or very easy spin recommended"
    if fatigue_score <= 8.0: return "High fatigue - rest day required, focus on recovery"
    return "Extreme fatigue - multiple rest days recommended"