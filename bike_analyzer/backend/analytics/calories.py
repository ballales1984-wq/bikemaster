"""Calorie estimation using MET and physics models."""
from __future__ import annotations

from ..models.models import Ride


def calculate_calories_met(ride: Ride) -> float:
    speed = ride.avg_speed_kmh
    met = 4.0 if speed < 16 else 6.0 if speed < 19 else 8.0 if speed < 22 else 10.0 + (speed - 22) * 0.5
    return met * ride.weight_kg * ride.duration_hours

def calculate_calories_physics(ride: Ride) -> float:
    g, crr, rho, cdA, eff, J_PER_CAL = 9.81, 0.005, 1.225, 0.4, 0.25, 4184
    v_ms = ride.avg_speed_kmh * 1000 / 3600
    w_n = ride.weight_kg * g
    rolling = crr * w_n
    air = 0.5 * rho * cdA * v_ms ** 2
    grade = (ride.elevation_gain_m / (ride.distance_km * 1000)) if ride.elevation_gain_m and ride.distance_km and ride.distance_km > 0 else 0
    gravity = w_n * grade
    power = (rolling + air + gravity) * v_ms
    energy = power * (ride.duration_minutes * 60)
    return energy / (eff * J_PER_CAL)

def estimate_calories(ride: Ride, method: str = "met") -> float:
    return calculate_calories_physics(ride) if method == "physics" else calculate_calories_met(ride)

def calories_per_km(ride: Ride) -> float:
    return ride.calories / ride.distance_km if ride.distance_km > 0 else 0.0
