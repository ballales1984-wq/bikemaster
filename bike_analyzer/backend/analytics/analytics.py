"""Analytics engine for ride analysis."""
from __future__ import annotations
from typing import List
from ..models.models import Ride
from .calories import estimate_calories
from .fatigue import calculate_fatigue_score, estimate_recovery_hours, get_recovery_recommendation

def calculate_summary(rides: List[Ride]) -> dict:
    if not rides: return {"total_rides": 0, "total_km": 0.0, "total_calories": 0.0, "avg_speed": 0.0, "avg_fatigue": 0.0}
    return {"total_rides": len(rides), "total_km": round(sum(r.distance_km for r in rides), 1), "total_calories": round(sum(r.calories for r in rides), 0), "avg_speed": round(sum(r.avg_speed_kmh for r in rides) / len(rides), 1), "avg_fatigue": round(sum(calculate_fatigue_score(r) for r in rides) / len(rides), 1)}

def analyze_ride(ride: Ride) -> dict:
    fatigue = calculate_fatigue_score(ride)
    return {"ride_id": ride.id, "date": ride.date, "distance_km": ride.distance_km, "duration_minutes": ride.duration_minutes, "avg_speed_kmh": ride.avg_speed_kmh, "calories": ride.calories, "fatigue_score": round(fatigue, 1), "recovery_hours": estimate_recovery_hours(fatigue), "recovery_recommendation": get_recovery_recommendation(fatigue)}