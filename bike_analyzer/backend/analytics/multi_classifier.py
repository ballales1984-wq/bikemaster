"""Multi-class ride classifier.

Classifies each ride into one or more activity categories based on
objective metrics rather than guessed labels:

- endurance, tempo, threshold, sweet_spot, vo2max, recovery, race, hilly
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..models.models import Ride


@dataclass
class ClassifiedRide:
    ride_id: int | None
    date: str
    categories: list[str]
    primary_category: str
    confidence: float
    metrics: dict[str, Any]


def _classify_ride(ride: Ride) -> list[str]:
    cats: list[str] = []
    dur = ride.duration_minutes or 0
    dist = ride.distance_km or 0
    speed = ride.avg_speed_kmh or 0
    elev = ride.elevation_gain_m or 0
    elev_per_km = (elev / dist) if dist > 0 else 0

    if dur >= 90 and speed < 30:
        cats.append("endurance")
    if 40 <= dur <= 90 and 28 <= speed <= 33:
        cats.append("tempo")
    if 30 <= dur <= 75 and 33 <= speed <= 37:
        cats.append("threshold")
    if 20 <= dur <= 60 and 30 <= speed <= 35:
        cats.append("sweet_spot")
    if dur <= 25 and speed >= 35:
        cats.append("vo2max")
    if dur <= 40 and speed < 22:
        cats.append("recovery")
    if dur >= 60 and speed >= 28:
        cats.append("race")
    if elev_per_km >= 10:
        cats.append("hilly")

    if not cats:
        cats.append("endurance")
    return cats


def classify_rides(rides: list[Ride]) -> list[ClassifiedRide]:
    results: list[ClassifiedRide] = []
    for ride in rides:
        cats = _classify_ride(ride)
        primary = cats[0] if cats else "endurance"
        confidence = min(1.0, 0.5 + 0.1 * len(cats))
        results.append(
            ClassifiedRide(
                ride_id=ride.id,
                date=ride.date[:10] if ride.date else "",
                categories=cats,
                primary_category=primary,
                confidence=round(confidence, 2),
                metrics={
                    "duration_minutes": ride.duration_minutes,
                    "distance_km": ride.distance_km,
                    "avg_speed_kmh": ride.avg_speed_kmh,
                    "elevation_gain_m": ride.elevation_gain_m,
                },
            )
        )
    return results


def category_distribution(rides: list[Ride]) -> dict[str, int]:
    dist: dict[str, int] = {}
    for cr in classify_rides(rides):
        for c in cr.categories:
            dist[c] = dist.get(c, 0) + 1
    return dict(sorted(dist.items(), key=lambda x: x[1], reverse=True))


__all__ = ["ClassifiedRide", "classify_rides", "category_distribution"]
