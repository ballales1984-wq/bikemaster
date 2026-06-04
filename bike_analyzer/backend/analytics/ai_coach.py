"""AI Coach - workout and recovery recommendations."""
from __future__ import annotations
from typing import List, Optional
from ..models.models import Ride, AthleteProfile
from .fatigue import estimate_recovery_hours, get_recovery_recommendation
from .benchmark import compare_with_benchmark
from .performance import calculate_performance_score, calculate_efficiency_score

def generate_workout_recommendations(rides: List[Ride], athlete: Optional[AthleteProfile] = None) -> List[str]:
    if not rides: return ["Start with 2-3 easy rides per week to build base fitness"]
    avg_speed = sum(r.avg_speed_kmh for r in rides) / len(rides)
    avg_fatigue = sum(r.calories for r in rides[:10]) / len(rides[:10]) / 50 if rides else 0
    recs = []
    if avg_speed < 20: recs.append("Focus on Zone 2 rides (easy pace) to build aerobic base")
    elif avg_speed < 25: recs.append("Add one interval session per week")
    else: recs.append("Maintain current intensity, mix endurance and race-specific workouts")
    if avg_fatigue > 700: recs.append("Consider adding more recovery days")
    recs.append("Include 1 long ride weekly (1.5-2x your average distance)")
    return recs

def generate_recovery_recommendations(ride: Optional[Ride] = None, fatigue_score: float = 5.0) -> List[str]:
    recs = [get_recovery_recommendation(fatigue_score)]
    hours = estimate_recovery_hours(fatigue_score)
    if hours >= 48: recs.append("Take 1-2 full rest days, then easy 20km spin")
    elif hours >= 24: recs.append("Do a recovery ride under 25km/h")
    return recs

def analyze_historical_trends(rides: List[Ride]) -> dict:
    if len(rides) < 3: return {"trend": "insufficient_data"}
    sorted_rides = sorted(rides, key=lambda r: r.date)[-4:]
    speeds = [r.avg_speed_kmh for r in sorted_rides]
    if len(speeds) >= 2 and speeds[-1] > speeds[0] * 1.1: return {"trend": "improving_speed", "change_pct": (speeds[-1] - speeds[0]) / speeds[0] * 100}
    if len(speeds) >= 2 and speeds[-1] < speeds[0] * 0.9: return {"trend": "declining_speed", "change_pct": (speeds[-1] - speeds[0]) / speeds[0] * 100}
    return {"trend": "stable", "avg_speed": sum(speeds) / len(speeds)}