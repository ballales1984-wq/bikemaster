"""Calories calculator.

Three estimation methods:
- MET (Metabolic Equivalent of Task): speed-based lookup, simplest.
- Physics: mechanical power from cycling forces / metabolic efficiency.
- HR (heart rate): HR reserve * weight * duration factor.

The physics method is the most accurate when speed and elevation are known.
MET is the default fallback. HR requires a heart rate sensor.
"""

from __future__ import annotations

from ..models import Ride


def calories_met(ride: Ride) -> float:
    """Stima calorie con metodo MET (Metabolic Equivalent of Task) basato su velocita'.

    Uses speed brackets to select a MET value, then:
    kcal = MET * weight_kg * duration_hours

    Speed brackets: <16 km/h -> MET 4.0, 16-19 -> 6.0, 19-22 -> 8.0,
    22+ -> 10.0 + (speed-22)*0.5

    Args:
        ride: Cycling activity with avg_speed_kmh, weight_kg, duration_minutes.

    Returns:
        Estimated calories in kcal.
    """
    speed = ride.avg_speed_kmh
    if speed is None:
        return 0.0
    met = 4.0 if speed < 16 else 6.0 if speed < 19 else 8.0 if speed < 22 else 10.0 + (speed - 22) * 0.5
    return met * ride.weight_kg * ride.duration_hours


def calories_physics(ride: Ride) -> float:
    """Stima calorie da modello fisico: potenza meccanica / efficienza metabolica.

    Computes the mechanical power required to overcome:
    - Rolling resistance: CRR * weight * g
    - Aerodynamic drag: 0.5 * rho * CdA * v^2
    - Gravity: weight * g * grade (from elevation_gain / distance)

    Then converts mechanical energy to metabolic energy by dividing by
    drivetrain efficiency (0.97) and the physiological conversion factor
    (4184 J/kcal).

    Args:
        ride: Cycling activity with avg_speed_kmh, weight_kg, elevation_gain_m,
              distance_km, duration_minutes.

    Returns:
        Estimated calories in kcal.
    """
    if ride.avg_speed_kmh is None:
        return 0.0
    g, crr, rho, cdA, eff, J_PER_CAL = 9.81, 0.005, 1.225, 0.4, 0.97, 4184
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


def calories_hr(ride: Ride, resting_hr: float = 60.0) -> float:
    """Stima calorie da frequenza cardiaca (method HR).

    Uses the formula:
    kcal = (HR_avg - resting_HR) * weight_kg * 0.0175 * duration_minutes

    Args:
        ride: Cycling activity with heart_rate_avg, weight_kg, duration_minutes.
        resting_hr: Resting heart rate in bpm (default 60).

    Returns:
        Estimated calories in kcal, or 0 if HR data missing.
    """
    if ride.heart_rate_avg is None or ride.weight_kg is None:
        return 0.0
    hr_factor = ride.heart_rate_avg - resting_hr
    if hr_factor <= 0:
        return 0.0
    return hr_factor * ride.weight_kg * 0.0175 * ride.duration_minutes


def estimate(ride: Ride, method: str = "met") -> float:
    """Wrapper unico per stima calorie (MET, physics, o hr).

    Args:
        ride: Cycling activity.
        method: One of ``"met"``, ``"physics"``, ``"hr"``. Default ``"met"``.

    Returns:
        Estimated calories in kcal.
    """
    if method == "hr":
        return calories_hr(ride)
    return calories_physics(ride) if method == "physics" else calories_met(ride)


def per_km(ride: Ride) -> float:
    """Calorie per chilometro (0 se distanza nulla)."""
    return ride.calories / ride.distance_km if ride.distance_km > 0 else 0.0
