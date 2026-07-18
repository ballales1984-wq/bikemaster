"""Performance calculator."""

from __future__ import annotations

from ..models import Ride


def performance_score(ride: Ride) -> float:
    """Punteggio performance (0-10) combinando velocita', durata e dislivello."""
    speed_factor = min(ride.avg_speed_kmh / 30.0, 1.0)
    duration_factor = min(ride.duration_hours / 2.0, 1.0)
    elevation_factor = min(ride.elevation_gain_m / 500.0, 1.0) if ride.elevation_gain_m else 0.0
    return round((speed_factor * 0.4 + duration_factor * 0.4 + elevation_factor * 0.2) * 10.0, 1)


def endurance_score(rides: list[Ride]) -> float:
    """Punteggio resistenza (0-10) su storico: uscite lunghe, costanza, volume."""
    if not rides:
        return 0.0
    long_rides = sum(1 for r in rides if r.duration_hours >= 2.0)
    long_ride_ratio = long_rides / len(rides)
    consistency = min(len(rides) / 20.0, 1.0)
    total_distance = sum(r.distance_km for r in rides)
    distance_factor = min(total_distance / 500.0, 1.0)
    return round((long_ride_ratio * 0.4 + consistency * 0.3 + distance_factor * 0.3) * 10.0, 1)


def recovery_score(ride: Ride) -> float:
    """Punteggio recupero (0-10): inverso della fatica dell'uscita."""
    from .fatigue import calculate_fatigue_score

    fatigue = calculate_fatigue_score(ride)
    return round(10.0 - fatigue, 1)


def efficiency_score(ride: Ride) -> float:
    """Efficienza energetica (0-10): kcal/km sotto benchmark 30 = 10."""
    if ride.distance_km <= 0:
        return 0.0
    calories_per_km = ride.calories / ride.distance_km
    benchmark = 30.0
    efficiency = max(0.0, min(10.0, 10.0 - (calories_per_km - benchmark) / 5.0))
    return round(efficiency, 1)


def monthly_scores(rides: list[Ride]) -> dict:
    """Aggrega score medi mensili (performance, endurance, recovery, efficiency, fatica)."""
    if not rides:
        return {"performance": 0, "endurance": 0, "recovery": 0, "efficiency": 0, "avg_fatigue": 0}
    from .fatigue import calculate_fatigue_score

    return {
        "performance": round(sum(performance_score(r) for r in rides) / len(rides), 1),
        "endurance": endurance_score(rides),
        "recovery": round(sum(recovery_score(r) for r in rides) / len(rides), 1),
        "efficiency": round(sum(efficiency_score(r) for r in rides) / len(rides), 1),
        "avg_fatigue": round(sum(calculate_fatigue_score(r) for r in rides) / len(rides), 1),
    }
