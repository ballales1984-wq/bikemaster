"""Point-wise cycling physics — the single numeric kernel for BikeMaster.

This module is the canonical forward/inverse model used by both the lean
``core`` calculators and the heavier ``bm2`` simulation framework, so the
physics lives in exactly one place.

Conventions (aligned with ``core.calculators.calories.calories_physics`` and
``bm2.algorithms.base.Algorithm._cycling_forces``):
  * ``grade`` is the linear slope ratio (rise/run), not an angle.
  * rolling resistance force  = crr * mass * g
  * gravity force             = mass * g * grade
  * aerodynamic force         = 0.5 * rho * cda * (v + wind)^2
  * mechanical power at crank = (rolling + aero + gravity) * v / drivetrain_eff
"""

from __future__ import annotations

from ..models import GPSPoint, haversine_distance_m
from .constants import AIR_DENSITY, GRAVITY, RiderBikeParams


def grade_between(p1: GPSPoint, p2: GPSPoint) -> float:
    """Slope (rise/run) between two GPS points.

    Returns 0.0 when the horizontal distance is negligible or altitude is
    missing on either point.
    """
    if p1.altitude is None or p2.altitude is None:
        return 0.0
    horizontal = haversine_distance_m(p1.lat, p1.lon, p2.lat, p2.lon)
    if horizontal <= 0.0:
        return 0.0
    return (p2.altitude - p1.altitude) / horizontal


def cycling_forces(
    v_ms: float,
    mass_kg: float,
    grade: float,
    crr: float,
    cda: float,
    rho: float = AIR_DENSITY,
    wind_ms: float = 0.0,
    drivetrain_efficiency: float = 1.0,
) -> dict[str, float]:
    """Resistance forces and crank power required to sustain ``v_ms``.

    Returns a dict with ``roll``, ``grav``, ``air`` and ``power_w`` so callers
    (e.g. ``bm2``) can surface the force breakdown alongside the power.
    """
    if v_ms <= 0.0:
        return {"roll": 0.0, "grav": 0.0, "air": 0.0, "power_w": 0.0}
    v_app = v_ms + wind_ms
    roll = crr * mass_kg * GRAVITY
    grav = mass_kg * GRAVITY * grade
    air = 0.5 * rho * cda * v_app**2
    eff = drivetrain_efficiency if drivetrain_efficiency > 0 else 1.0
    power_w = (roll + grav + air) * v_ms / eff
    return {"roll": roll, "grav": grav, "air": air, "power_w": power_w}


def instantaneous_power(
    v_ms: float,
    grade: float,
    params: RiderBikeParams | None = None,
    wind_ms: float = 0.0,
    drivetrain_efficiency: float | None = None,
) -> float:
    """Mechanical crank power (W) to sustain ``v_ms`` on slope ``grade``.

    Forward model. ``drivetrain_efficiency`` defaults to the value carried by
    ``params`` (1.0 when omitted), matching ``calories_physics`` which treats
    efficiency as a food-energy conversion factor rather than a power divisor.
    """
    p = params or RiderBikeParams()
    eff = drivetrain_efficiency if drivetrain_efficiency is not None else p.drivetrain_efficiency
    return cycling_forces(
        v_ms, p.total_mass_kg, grade, p.crr, p.cda, p.rho, wind_ms, eff
    )["power_w"]


def required_speed_for_power(
    target_power: float,
    grade: float,
    params: RiderBikeParams | None = None,
    wind_ms: float = 0.0,
    v_low: float = 0.1,
    v_high: float = 30.0,
    tol: float = 1e-3,
    max_iter: int = 100,
) -> float:
    """Inverse model: speed (m/s) that yields ``target_power`` on ``grade``.

    ``P(v)`` is strictly increasing for ``v > 0``, so bisection converges.
    Returns 0.0 for non-positive targets.
    """
    if target_power <= 0.0:
        return 0.0
    lo, hi = v_low, v_high
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        p_mid = instantaneous_power(mid, grade, params, wind_ms)
        if abs(p_mid - target_power) <= tol:
            return mid
        if p_mid < target_power:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
