"""Ride Routes Estimator.

Suggests route characteristics based on historical ride preferences
and training goals.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models.models import AthleteProfile, Ride


@dataclass
class RouteSuggestion:
    name: str
    distance_km: float
    elevation_gain_m: int
    avg_speed_target_kmh: float
    duration_minutes: int
    terrain: str
    rationale: str


def estimate_route_preferences(athlete: AthleteProfile, rides: list[Ride]) -> list[RouteSuggestion]:
    if not rides:
        return [
            RouteSuggestion(
                name="Base recovery",
                distance_km=30.0,
                elevation_gain_m=200,
                avg_speed_target_kmh=22.0,
                duration_minutes=80,
                terrain="flat",
                rationale="No history available. Default safe starter route.",
            )
        ]

    avg_dist = sum(r.distance_km for r in rides[-10:]) / min(len(rides), 10)
    avg_elev = sum(r.elevation_gain_m or 0 for r in rides[-10:]) / min(len(rides), 10)
    avg_speed = sum(r.avg_speed_kmh for r in rides[-10:]) / min(len(rides), 10)

    suggestions = [
        RouteSuggestion(
            name="Endurance base",
            distance_km=round(avg_dist * 1.1, 1),
            elevation_gain_m=int(avg_elev * 1.2),
            avg_speed_target_kmh=round(avg_speed * 0.95, 1),
            duration_minutes=int(avg_dist / (avg_speed * 0.95) * 60),
            terrain=athlete.preferred_terrain or "mixed",
            rationale="Slightly longer than usual for aerobic base build.",
        ),
        RouteSuggestion(
            name="Speed work",
            distance_km=round(avg_dist * 0.5, 1),
            elevation_gain_m=int(avg_elev * 0.5),
            avg_speed_target_kmh=round(avg_speed * 1.08, 1),
            duration_minutes=int(avg_dist * 0.5 / (avg_speed * 1.08) * 60),
            terrain="flat",
            rationale="Shorter, faster effort to improve threshold.",
        ),
    ]

    if avg_elev > 200:
        suggestions.append(
            RouteSuggestion(
                name="Climbing repeat",
                distance_km=round(avg_dist * 0.7, 1),
                elevation_gain_m=int(avg_elev * 1.5),
                avg_speed_target_kmh=round(avg_speed * 0.85, 1),
                duration_minutes=int(avg_dist * 0.7 / (avg_speed * 0.85) * 60),
                terrain="hilly",
                rationale="You usually ride with significant elevation. Add a climbing-focused session.",
            )
        )

    return suggestions


__all__ = ["RouteSuggestion", "estimate_route_preferences"]
