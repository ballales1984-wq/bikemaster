"""Point-wise cycling physics — the forward and inverse models.

Unlike ``core/calculators`` (ride-level scalars), these functions operate on a
single instant / segment so they can drive a time-step simulation and the
"what-if" engine.
"""

from __future__ import annotations

import math

from ..models import GPSPoint, haversine_distance_m
from .constants import GRAVITY, RiderBikeParams


def grade_between(p1: GPSPoint, p2: GPSPoint) -> float:
    """Slope (rise/run) between two GPS points.

    Returns 0.0 when the horizontal distance is negligible.
    """
    if p1.altitude is None or p2.altitude is None:
        return 0.0
    horizontal = haversine_distance_m(p1.lat, p1.lon, p2.lat, p2.lon)
    if horizontal <= 0.0:
        return 0.0
    return (p2.altitude - p1.altitude) / horizontal


def instantaneous_power(
    v_ms: float,
    grade: float,
    params: RiderBikeParams | None = None,
    wind_ms: float = 0.0,
) -> float:
    """Mechanical power (W) required to sustain speed ``v_ms`` on slope ``grade``.

    Forward model: ``P = (rolling + aero + gravity) * v`` where the apparent
    wind is ``v + wind_ms`` (positive wind_ms = headwind).
    """
    if v_ms <= 0.0:
        return 0.0
    p = params or RiderBikeParams()
    theta = math.atan(grade)
    mass = p.total_mass_kg
    v_app = v_ms + wind_ms
    rolling = p.crr * mass * GRAVITY * math.cos(theta)
    aero = 0.5 * p.rho * p.cda * v_app**2
    gravity = mass * GRAVITY * math.sin(theta)
    return (rolling + aero + gravity) * v_ms


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
