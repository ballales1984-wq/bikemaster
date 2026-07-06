"""VIP Predictor — estimates Very Important Performance metrics.

Predicts near-term performance ceiling probability based on recent training
load, consistency, and fatigue recovery patterns.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models.models import Ride


@dataclass
class VIPResult:
    probability_index: float
    readiness_score: float
    recommendation: str
    risk_factors: list[str]


def _consistency_score(rides: list[Ride]) -> float:
    if len(rides) < 3:
        return 0.0
    dates = sorted(r.date for r in rides if r.date)
    if len(dates) < 3:
        return 0.0
    gaps = []
    for i in range(1, len(dates)):
        try:
            from datetime import date

            d1 = date.fromisoformat(dates[i - 1][:10])
            d2 = date.fromisoformat(dates[i][:10])
            gaps.append((d2 - d1).days)
        except ValueError:
            continue
    if not gaps:
        return 0.0
    avg_gap = sum(gaps) / len(gaps)
    return max(0.0, min(1.0, 1.0 - (avg_gap / 14.0)))


def estimate_vip(rides: list[Ride], athlete_ftp: float = 250.0) -> VIPResult:
    if len(rides) < 3:
        return VIPResult(
            probability_index=0.0,
            readiness_score=0.0,
            recommendation="Need more rides to estimate VIP.",
            risk_factors=["insufficient_data"],
        )

    recent = rides[-8:]
    avg_speed = sum(r.avg_speed_kmh for r in recent) / len(recent)
    avg_dur = sum(r.duration_minutes for r in recent) / len(recent)
    consistency = _consistency_score(recent)

    speed_ratio = avg_speed / (athlete_ftp / 10.0) if athlete_ftp else 0.0
    prob = min(1.0, max(0.0, (consistency * 0.6 + speed_ratio * 0.4)))

    risks = []
    if avg_dur < 30:
        risks.append("low_duration")
    if consistency < 0.5:
        risks.append("inconsistent_training")

    if prob >= 0.75:
        rec = "High performance potential. Maintain current workload."
    elif prob >= 0.5:
        rec = "Moderate potential. Increase duration and consistency."
    else:
        rec = "Low readiness. Focus on base building and recovery."

    return VIPResult(
        probability_index=round(prob, 2),
        readiness_score=round(consistency, 2),
        recommendation=rec,
        risk_factors=risks,
    )


__all__ = ["VIPResult", "estimate_vip"]
