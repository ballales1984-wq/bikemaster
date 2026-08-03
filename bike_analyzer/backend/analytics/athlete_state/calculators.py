"""Pure calculators for the Athlete State Engine.

All functions in this module are stateless and deterministic — no I/O, no
imports from infrastructure. They take plain values and return plain values so
the logic can be unit tested in isolation and reused by the orchestrating
services in ``service.py``.
"""

from __future__ import annotations

from collections.abc import Sequence

from ...models.models import Ride


def build_daily_tss_series(
    rides: Sequence[Ride],
    ftp: float = 250.0,
) -> list[tuple[str, float]]:
    """Aggregate rides into a dated TSS series for the load manager."""
    daily: dict[str, float] = {}
    for ride in rides:
        date_key = ride.date[:10] if ride.date and len(ride.date) >= 10 else "unknown"
        tss = estimate_tss_for_ride(ride, ftp)
        daily[date_key] = daily.get(date_key, 0.0) + tss
    return sorted(daily.items())


def estimate_tss_for_ride(ride: Ride, ftp: float = 250.0) -> float:
    """Estimate Training Stress Score for a single ride."""
    from ..training_stress import estimate_tss

    return estimate_tss(ride, ftp)


def average_fatigue_score(rides: Sequence[Ride], rider_age: int = 35) -> tuple[float, float]:
    """Return (avg_fatigue, max_fatigue) for a sequence of rides.

    If the sequence is empty, returns (0.0, 0.0).
    """
    if not rides:
        return 0.0, 0.0
    scores = [calculate_fatigue_for_ride(r, rider_age) for r in rides]
    avg = sum(scores) / len(scores)
    mx = max(scores)
    return round(avg, 1), round(mx, 1)


def calculate_fatigue_for_ride(ride: Ride, rider_age: int = 35) -> float:
    """Calculate fatigue score for a single ride."""
    from ..fatigue import calculate_fatigue_score

    return calculate_fatigue_score(ride, rider_age)


def estimate_recovery_hours(fatigue_score: float, tsb: float = 0.0) -> float:
    """Estimate recovery hours based on fatigue score and form (TSB)."""
    from ..fatigue import estimate_recovery_hours

    base = estimate_recovery_hours(fatigue_score)
    if tsb < -15:
        base *= 1.5
    return round(base, 1)


def compute_readiness(
    atl: float,
    ctl: float,
    tsb: float,
    fatigue_score: float,
    acwr: float,
) -> float:
    """Compute readiness score on a 0-100 scale.

    Higher values mean the athlete is fresher and better prepared.
    """
    readiness = 100.0

    if tsb < -30:
        readiness -= 35
    elif tsb < -20:
        readiness -= 25
    elif tsb < -10:
        readiness -= 15
    elif tsb < 0:
        readiness -= 8

    if fatigue_score >= 8:
        readiness -= 25
    elif fatigue_score >= 6:
        readiness -= 15
    elif fatigue_score >= 4:
        readiness -= 8
    elif fatigue_score >= 2:
        readiness -= 3

    if acwr > 1.5:
        readiness -= 20
    elif acwr > 1.3:
        readiness -= 10

    return max(0.0, min(100.0, round(readiness, 1)))


def compute_risk_level(
    atl: float,
    ctl: float,
    tsb: float,
    acwr: float,
    fatigue_score: float,
) -> str:
    """Return risk level string: ok, warning, high, or block."""
    if atl > ctl * 1.3 and tsb < -20:
        return "block"
    if acwr > 1.5 or tsb < -30 or fatigue_score >= 9:
        return "high"
    if acwr > 1.3 or tsb < -20 or fatigue_score >= 7:
        return "warning"
    return "ok"


def compute_recommendation(
    atl: float,
    ctl: float,
    tsb: float,
    fatigue_score: float,
    readiness: float,
) -> str:
    """Return a human-readable training recommendation."""
    if readiness < 30:
        return "Total rest recommended"
    if readiness < 50:
        return "Recovery focus - light activity only"
    if tsb > 15:
        return "Good freshness - race or hard effort possible"
    if tsb > 5:
        return "Ready for hard effort"
    if tsb > -10:
        return "Light training or recovery recommended"
    if tsb > -20:
        return "Urgent recovery needed. Reduce volume/intensity"
    return "Overtraining risk. Total rest for 2-3 days"


def build_risk_indicators(
    atl: float,
    ctl: float,
    tsb: float,
    acwr: float,
    fatigue_score: float,
    readiness: float,
) -> list[str]:
    """Build a list of risk indicator strings."""
    indicators: list[str] = []
    if atl > ctl * 1.3 and tsb < -20:
        indicators.append("overtraining_risk")
    if acwr > 1.5:
        indicators.append("high_acwr")
    if tsb < -20:
        indicators.append("low_form")
    if fatigue_score >= 8:
        indicators.append("high_fatigue")
    if readiness < 50:
        indicators.append("low_readiness")
    if ctl > 0 and atl > ctl * 1.2:
        indicators.append("acute_load_elevated")
    return indicators


__all__ = [
    "build_daily_tss_series",
    "estimate_tss_for_ride",
    "average_fatigue_score",
    "calculate_fatigue_for_ride",
    "estimate_recovery_hours",
    "compute_readiness",
    "compute_risk_level",
    "compute_recommendation",
    "build_risk_indicators",
]
