"""Fitness State Vector - the athlete's current physiological state snapshot."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TrainingStressDay:
    date: date
    tss: float = 0.0
    atl: float = 0.0
    ctl: float = 0.0
    tsb: float = 0.0


@dataclass
class FitnessStateVector:
    athlete_id: int
    computed_at: datetime
    atl: float = 0.0
    ctl: float = 0.0
    tsb: float = 0.0
    fitness: float = 0.0
    fatigue: float = 0.0
    form: float = 0.0
    recovery_hours_needed: float = 0.0
    weekly_tss: float = 0.0
    monthly_tss: float = 0.0
    trend_7d: str = "stable"
    trend_30d: str = "stable"
    risk_indicators: list[str] = field(default_factory=list)
    recommendation: str = ""

    @property
    def is_overtraining_risk(self) -> bool:
        return self.atl > self.ctl * 1.3 and self.tsb < -20

    @property
    def is_fresh(self) -> bool:
        return self.tsb > 15

    @property
    def is_ready_for_hard_effort(self) -> bool:
        return self.tsb > 5 and self.atl < self.ctl * 1.1

    def to_dict(self) -> dict:
        return {
            "athlete_id": self.athlete_id,
            "computed_at": self.computed_at.isoformat(),
            "atl": round(self.atl, 1),
            "ctl": round(self.ctl, 1),
            "tsb": round(self.tsb, 1),
            "fitness": round(self.fitness, 1),
            "fatigue": round(self.fatigue, 1),
            "form": round(self.form, 1),
            "recovery_hours_needed": round(self.recovery_hours_needed, 1),
            "weekly_tss": round(self.weekly_tss, 1),
            "monthly_tss": round(self.monthly_tss, 1),
            "trend_7d": self.trend_7d,
            "trend_30d": self.trend_30d,
            "risk_indicators": self.risk_indicators,
            "recommendation": self.recommendation,
            "is_overtraining_risk": self.is_overtraining_risk,
            "is_fresh": self.is_fresh,
            "is_ready_for_hard_effort": self.is_ready_for_hard_effort,
        }
