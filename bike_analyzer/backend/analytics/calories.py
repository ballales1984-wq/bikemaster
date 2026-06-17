"""Calorie estimation using MET and physics models."""

from __future__ import annotations

from ..models.models import Ride
from .calculators.calories import estimate as _core_estimate


def calculate_calories_met(ride: Ride) -> float:
    return _core_estimate(ride, method="met")


def calculate_calories_physics(ride: Ride) -> float:
    return _core_estimate(ride, method="physics")


def estimate_calories(ride: Ride, method: str = "met") -> float:
    return _core_estimate(ride, method=method)


def calories_per_km(ride: Ride) -> float:
    return ride.calories / ride.distance_km if ride.distance_km > 0 else 0.0
