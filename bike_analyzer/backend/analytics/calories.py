"""Calorie estimation using MET and physics models."""

from __future__ import annotations

from dataclasses import replace

from bike_analyzer.core.calculators.calories import estimate as _core_estimate

from ..models.models import Ride


def calculate_calories_met(ride: Ride) -> float:
    """Stima calorie con metodo MET (Metabolic Equivalent of Task)."""
    return _core_estimate(ride, method="met")


def calculate_calories_physics(ride: Ride) -> float:
    """Stima calorie da modello fisico (potenza meccanica / efficienza metabolica)."""
    return _core_estimate(ride, method="physics")


def estimate_calories(ride: Ride, method: str = "met") -> float:
    """Wrapper unico per stima calorie (MET o physics)."""
    return _core_estimate(ride, method=method)


def calories_per_km(ride: Ride) -> float:
    """Calorie per chilometro (0 se distanza nulla)."""
    return ride.calories / ride.distance_km if ride.distance_km > 0 else 0.0


def ensure_calories(ride: Ride) -> float:
    """Return ``ride.calories``, estimating it when not already set.

    Mirrors the logic used when creating a ride: if no calories are stored but the
    ride has the data needed (speed/distance/duration), compute average speed when
    missing and fall back to a physics-based estimate so the value is never silently 0.
    """
    if ride.calories:
        return float(ride.calories)
    avg_speed = ride.avg_speed_kmh
    if (
        not avg_speed
        and ride.distance_km
        and ride.duration_minutes
        and ride.duration_minutes > 0
    ):
        avg_speed = ride.distance_km / (ride.duration_minutes / 60)
    if not avg_speed:
        return 0.0
    updated = replace(
        ride,
        avg_speed_kmh=avg_speed,
        weight_kg=ride.weight_kg or 70.0,
    )
    return estimate_calories(updated, method="physics")
