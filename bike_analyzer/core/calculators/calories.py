"""Calories calculator."""

from __future__ import annotations

from ..models import Ride


def calories_met(ride: Ride) -> float:
    """Stima calorie con metodo MET (Metabolic Equivalent of Task) basato su velocita'."""
    speed = ride.avg_speed_kmh
    if speed is None:
        return 0.0
    met = 4.0 if speed < 16 else 6.0 if speed < 19 else 8.0 if speed < 22 else 10.0 + (speed - 22) * 0.5
    return met * ride.weight_kg * ride.duration_hours


def calories_physics(ride: Ride) -> float:
    """Stima calorie da modello fisico: potenza meccanica / efficienza metabolica."""
    if ride.avg_speed_kmh is None:
        return 0.0
    g, crr, rho, cdA, eff, J_PER_CAL = 9.81, 0.005, 1.225, 0.4, 0.25, 4184
    v_ms = ride.avg_speed_kmh * 1000 / 3600
    w_n = ride.weight_kg * g
    rolling = crr * w_n
    air = 0.5 * rho * cdA * v_ms**2
    grade = (
        (ride.elevation_gain_m / (ride.distance_km * 1000))
        if ride.elevation_gain_m and ride.distance_km and ride.distance_km > 0
        else 0.0
    )
    gravity = w_n * grade
    power = (rolling + air + gravity) * v_ms
    energy = power * (ride.duration_minutes * 60)
    return energy / (eff * J_PER_CAL)


def estimate(ride: Ride, method: str = "met") -> float:
    """Wrapper unico per stima calorie (MET o physics)."""
    return calories_physics(ride) if method == "physics" else calories_met(ride)


def per_km(ride: Ride) -> float:
    """Calorie per chilometro (0 se distanza nulla)."""
    return ride.calories / ride.distance_km if ride.distance_km > 0 else 0.0
