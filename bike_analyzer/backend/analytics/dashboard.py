"""Dashboard di sintesi degli score atleta (performance, endurance, recovery, efficiency).

Aggrega i singoli score provenienti da :mod:`analytics.performance` in una
vista unica consumabile dalla home della SPA.
"""

from __future__ import annotations

from typing import Any

from ..models.models import AthleteProfile, Ride
from .performance import (
    calculate_efficiency_score,
    calculate_endurance_score,
    calculate_performance_score,
    calculate_recovery_score,
    classify_athlete,
)


def create_score_dashboard(rides: list[Ride], athlete: AthleteProfile) -> dict[str, Any]:
    """Compone il dizionario di score riassuntivo per la dashboard home.

    Calcola la media aritmetica per performance/recovery/efficiency sulle
    ride fornite, mentre ``endurance_score`` lavora sull'intera lista e
    ritorna un singolo valore. ``classify_athlete`` produce il livello
    (Beginner/Amateur/Intermediate/Advanced/Elite) dalle ride.

    Ritorna una struttura "vuota" con tutti 0 se la lista ride e' vuota.
    """
    if not rides:
        return {
            "performance": 0,
            "endurance": 0,
            "recovery": 0,
            "efficiency": 0,
            "level": "Beginner",
            "total_rides": 0,
            "total_km": 0,
        }
    scores = {
        "performance": round(sum(calculate_performance_score(r) for r in rides) / len(rides), 1),
        "endurance": calculate_endurance_score(rides),
        "recovery": round(sum(calculate_recovery_score(r) for r in rides) / len(rides), 1),
        "efficiency": round(sum(calculate_efficiency_score(r) for r in rides) / len(rides), 1),
        "level": classify_athlete(rides),
        "total_rides": len(rides),
        "total_km": round(sum(r.distance_km for r in rides), 1),
    }
    return scores


def get_score_breakdown(ride: Ride) -> dict[str, float]:
    """Score per singola ride usati dai pannelli di dettaglio.

    Diverso da :func:`create_score_dashboard` perche' opera su una singola
    uscita (non su medie di popolazione) e include solo gli score
    ride-level (performance, recovery, efficiency). L'endurance score e'
    escluso perche' richiede un dataset multi-ride.
    """
    return {
        "performance": calculate_performance_score(ride),
        "recovery": calculate_recovery_score(ride),
        "efficiency": calculate_efficiency_score(ride),
    }
