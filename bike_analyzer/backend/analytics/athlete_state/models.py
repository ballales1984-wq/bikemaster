"""Pydantic models for the Athlete State Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AthleteState(BaseModel):
    """Canonical Pydantic model for the athlete's current physiological state."""

    model_config = ConfigDict(from_attributes=True)

    athlete_id: int
    computed_at: datetime = Field(default_factory=datetime.now)

    fatigue_score: float = Field(default=0.0, ge=0.0, le=10.0)
    readiness: float = Field(default=100.0, ge=0.0, le=100.0)
    acwr: float = Field(default=1.0, ge=0.0)
    tsb: float = Field(default=0.0)
    atl: float = Field(default=0.0)
    ctl: float = Field(default=0.0)
    fitness: float = Field(default=0.0)
    form: float = Field(default=0.0)
    recovery_hours_needed: float = Field(default=0.0, ge=0.0)
    weekly_tss: float = Field(default=0.0, ge=0.0)
    monthly_tss: float = Field(default=0.0, ge=0.0)
    trend_7d: str = Field(default="stable")
    trend_30d: str = Field(default="stable")
    risk_indicators: list[str] = Field(default_factory=list)
    recommendation: str = Field(default="")
    risk_level: str = Field(default="ok", pattern="^(ok|warning|high|block)$")

    @property
    def is_overtraining_risk(self) -> bool:
        return self.atl > self.ctl * 1.3 and self.tsb < -20

    @property
    def is_fresh(self) -> bool:
        return self.tsb > 15

    @property
    def is_ready_for_hard_effort(self) -> bool:
        return self.tsb > 5 and self.atl < self.ctl * 1.1

    def to_notification_signals(self) -> dict[str, Any]:
        return {
            "insufficient_recovery": self.tsb < -15,
            "risk": self.risk_level in ("high", "block") or self.is_overtraining_risk,
            "overtraining_risk": self.is_overtraining_risk,
            "fresh": self.is_fresh,
            "ready_for_hard_effort": self.is_ready_for_hard_effort,
            "fatigue_score": self.fatigue_score,
            "readiness": self.readiness,
            "acwr": self.acwr,
            "recovery_hours_needed": self.recovery_hours_needed,
        }

    def to_notification_context_dict(self) -> dict[str, Any]:
        return {
            "athlete_id": self.athlete_id,
            "tsb": self.tsb,
            "atl": self.atl,
            "ctl": self.ctl,
            "fatigue_score": self.fatigue_score,
            "readiness": self.readiness,
            "acwr": self.acwr,
            "recovery_hours_needed": self.recovery_hours_needed,
            "risk_level": self.risk_level,
            "is_overtraining_risk": self.is_overtraining_risk,
            "is_fresh": self.is_fresh,
            "is_ready_for_hard_effort": self.is_ready_for_hard_effort,
            "weekly_tss": self.weekly_tss,
            "trend_7d": self.trend_7d,
        }

    def to_dataclass(self) -> Any:
        from ..adaptation_rules import AthleteState as DC_AthleteState

        return DC_AthleteState(
            fatigue_score=self.fatigue_score,
            readiness=self.readiness,
            acwr=self.acwr,
            tsb=self.tsb,
            atl=self.atl,
            ctl=self.ctl,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "athlete_id": self.athlete_id,
            "computed_at": self.computed_at.isoformat(),
            "fatigue_score": round(self.fatigue_score, 1),
            "readiness": round(self.readiness, 1),
            "acwr": round(self.acwr, 3),
            "tsb": round(self.tsb, 1),
            "atl": round(self.atl, 1),
            "ctl": round(self.ctl, 1),
            "fitness": round(self.fitness, 1),
            "form": round(self.form, 1),
            "recovery_hours_needed": round(self.recovery_hours_needed, 1),
            "weekly_tss": round(self.weekly_tss, 1),
            "monthly_tss": round(self.monthly_tss, 1),
            "trend_7d": self.trend_7d,
            "trend_30d": self.trend_30d,
            "risk_indicators": self.risk_indicators,
            "recommendation": self.recommendation,
            "risk_level": self.risk_level,
            "is_overtraining_risk": self.is_overtraining_risk,
            "is_fresh": self.is_fresh,
            "is_ready_for_hard_effort": self.is_ready_for_hard_effort,
        }


class PersonalResponseModel(BaseModel):
    """API response wrapping athlete state with optional profile snapshot."""

    athlete_id: int
    computed_at: datetime
    state: AthleteState
    profile: dict[str, Any] | None = None


__all__ = ["AthleteState", "PersonalResponseModel"]
