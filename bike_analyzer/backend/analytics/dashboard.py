"""Dashboard for performance scores."""
from __future__ import annotations

from typing import Any, Dict, List

from ..models.models import AthleteProfile, Ride
from .performance import (
    calculate_efficiency_score,
    calculate_endurance_score,
    calculate_performance_score,
    calculate_recovery_score,
    classify_athlete,
)


def create_score_dashboard(rides: List[Ride], athlete: AthleteProfile) -> Dict[str, Any]:
    if not rides:
        return {"performance": 0, "endurance": 0, "recovery": 0, "efficiency": 0, "level": "Beginner", "total_rides": 0, "total_km": 0}
    scores = {"performance": round(sum(calculate_performance_score(r) for r in rides) / len(rides), 1), "endurance": calculate_endurance_score(rides), "recovery": round(sum(calculate_recovery_score(r) for r in rides) / len(rides), 1), "efficiency": round(sum(calculate_efficiency_score(r) for r in rides) / len(rides), 1), "level": classify_athlete(rides), "total_rides": len(rides), "total_km": round(sum(r.distance_km for r in rides), 1)}
    return scores

def get_score_breakdown(ride: Ride) -> Dict[str, float]:
    return {"performance": calculate_performance_score(ride), "recovery": calculate_recovery_score(ride), "efficiency": calculate_efficiency_score(ride)}
