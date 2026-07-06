"""Inactivity Balance Estimator.

Estimates fitness decay and rebalancing time after periods of inactivity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ..models.models import Ride


@dataclass
class InactivityReport:
    current_streak_days: int
    estimated_ftp_loss_pct: float
    estimated_endurance_loss_pct: float
    recovery_plan_days: int
    advice: str


def estimate_inactivity(rides: list[Ride], current_ftp: float = 250.0) -> InactivityReport:
    if not rides:
        return InactivityReport(
            current_streak_days=999,
            estimated_ftp_loss_pct=15.0,
            estimated_endurance_loss_pct=20.0,
            recovery_plan_days=21,
            advice="No recent rides found. Start with 30-minute easy rides for 2 weeks.",
        )

    sorted_rides = sorted([r for r in rides if r.date], key=lambda r: r.date)
    now = datetime.now(UTC)
    last_date = sorted_rides[-1].date[:10]
    try:
        last_dt = datetime.fromisoformat(last_date).replace(tzinfo=UTC)
        streak = (now - last_dt).days
    except ValueError:
        streak = 999

    if streak <= 3:
        ftp_loss = 0.0
        endurance_loss = 0.0
        recovery = 0
        advice = "Active. Keep it up."
    elif streak <= 7:
        ftp_loss = 2.0
        endurance_loss = 3.0
        recovery = streak
        advice = "Short break. Resume with 60-minute Z2 rides."
    elif streak <= 14:
        ftp_loss = 5.0
        endurance_loss = 8.0
        recovery = streak + 3
        advice = "Moderate inactivity. Build back with progressive Z2/Z3."
    elif streak <= 30:
        ftp_loss = 10.0
        endurance_loss = 15.0
        recovery = streak + 7
        advice = "Significant fitness loss. Start with 45-minute easy rides, increase 10% weekly."
    else:
        ftp_loss = 15.0
        endurance_loss = 20.0
        recovery = 21
        advice = "Major detraining. Treat as return-to-cycling: 3 weeks progressive base building."

    return InactivityReport(
        current_streak_days=streak,
        estimated_ftp_loss_pct=ftp_loss,
        estimated_endurance_loss_pct=endurance_loss,
        recovery_plan_days=recovery,
        advice=advice,
    )


__all__ = ["InactivityReport", "estimate_inactivity"]
