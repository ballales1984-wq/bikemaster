"""Performance Engine: Scoring system for cycling performance."""
from __future__ import annotations
from typing import List
from ..models.models import Ride, AthleteProfile

def calculate_performance_score(ride: Ride) -> float:
    speed_factor = min(ride.avg_speed_kmh / 30.0, 1.0)
    duration_factor = min(ride.duration_hours / 2.0, 1.0)
    elevation_factor = min(ride.elevation_gain_m / 500.0, 1.0) if ride.elevation_gain_m else 0
    return round((speed_factor * 0.4 + duration_factor * 0.4 + elevation_factor * 0.2) * 10.0, 1)

def calculate_endurance_score(rides: List[Ride]) -> float:
    if not rides: return 0.0
    long_rides = sum(1 for r in rides if r.duration_hours >= 2.0)
    long_ride_ratio = long_rides / len(rides)
    consistency = min(len(rides) / 20.0, 1.0)
    total_distance = sum(r.distance_km for r in rides)
    distance_factor = min(total_distance / 500.0, 1.0)
    return round((long_ride_ratio * 0.4 + consistency * 0.3 + distance_factor * 0.3) * 10.0, 1)

def calculate_recovery_score(ride: Ride) -> float:
    from .fatigue import calculate_fatigue_score
    fatigue = calculate_fatigue_score(ride)
    return round(10.0 - fatigue, 1)

def calculate_efficiency_score(ride: Ride) -> float:
    if ride.distance_km <= 0: return 0.0
    calories_per_km = ride.calories / ride.distance_km
    benchmark = 30.0
    efficiency = max(0, min(10, 10 - (calories_per_km - benchmark) / 5.0))
    return round(efficiency, 1)

def calculate_monthly_scores(rides: List[Ride]) -> dict:
    if not rides: return {"performance": 0, "endurance": 0, "recovery": 0, "efficiency": 0, "avg_fatigue": 0}
    from .fatigue import calculate_fatigue_score
    return {"performance": round(sum(calculate_performance_score(r) for r in rides) / len(rides), 1), "endurance": calculate_endurance_score(rides), "recovery": round(sum(calculate_recovery_score(r) for r in rides) / len(rides), 1), "efficiency": round(sum(calculate_efficiency_score(r) for r in rides) / len(rides), 1), "avg_fatigue": round(sum(calculate_fatigue_score(r) for r in rides) / len(rides), 1)}

def calculate_annual_scores(rides: List[Ride]) -> dict:
    if not rides: return {"performance": 0, "endurance": 0, "total_km": 0, "total_calories": 0, "avg_fatigue": 0}
    from .fatigue import calculate_fatigue_score
    from .analytics import calculate_summary
    s = calculate_summary(rides)
    return {"performance": round(sum(calculate_performance_score(r) for r in rides) / len(rides), 1), "endurance": calculate_endurance_score(rides), "total_km": s["total_km"], "total_calories": s["total_calories"], "avg_fatigue": s["avg_fatigue"]}

def classify_athlete(rides: List[Ride]) -> str:
    if not rides: return "Unclassified"
    total_km = sum(r.distance_km for r in rides)
    total_rides = len(rides)
    avg_speed = sum(r.avg_speed_kmh for r in rides) / len(rides)
    if total_km < 100 and total_rides < 10: return "Beginner"
    if total_km < 500 and total_rides < 50: return "Amateur"
    if total_km < 1500 and total_rides < 150: return "Intermediate"
    if total_km < 3000: return "Advanced"
    return "Elite"

def get_experience_level(athlete: AthleteProfile) -> str:
    return athlete.experience_level

def should_save_to_database(points: List) -> bool:
    from .processing import validate_gps_point
    return all(validate_gps_point(p) for p in points) if points else False