"""Pydantic models for the training plan engine."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GoalType(StrEnum):
    GRANFONDO = "granfondo"
    FTP_IMPROVEMENT = "ftp_improvement"
    WEIGHT_LOSS = "weight_loss"
    MAINTENANCE = "maintenance"
    BEGINNER_BASE = "beginner_base"


class WorkoutType(StrEnum):
    ENDURANCE = "endurance"
    THRESHOLD = "threshold"
    SWEETSPOT = "sweetspot"
    INTERVALS = "intervals"
    RECOVERY = "recovery"
    LONG_RIDE = "long_ride"
    RACE = "race"
    OPENERS = "openers"


class AdaptationEventType(StrEnum):
    SKIPPED = "skipped"
    MODIFIED = "modified"
    STRAVA = "strava"
    RECOVERY_INSUFFICIENT = "recovery_insufficient"
    IMPROVEMENT = "improvement"
    INJURY = "injury"


class ScenarioType(StrEnum):
    RECOVER_VOLUME = "recover_volume"
    MAINTAIN_PLAN = "maintain_plan"
    CHANGE_TYPE = "change_type"


class TrainingGoal(BaseModel):
    goal_type: GoalType = Field(default=GoalType.MAINTENANCE)
    target_date: str | None = Field(default=None)
    target_distance_km: float | None = Field(default=None)
    target_elevation_m: float | None = Field(default=None)
    ftp_improvement_pct: float | None = Field(default=None)
    ftp_timeframe_weeks: int | None = Field(default=None)
    weight_target_kg: float | None = Field(default=None)
    caloric_deficit_kcal: int | None = Field(default=None)
    description: str = Field(default="")

    @field_validator("target_date")
    @classmethod
    def validate_date(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return v
        import datetime
        datetime.date.fromisoformat(v)
        return v


class PlanConstraints(BaseModel):
    days_per_week: int = Field(default=3, ge=1, le=14)
    hours_per_session: float = Field(default=1.5, ge=0.5, le=8.0)
    preferred_windows: list[str] = Field(default_factory=lambda: ["morning", "evening"])
    equipment: list[str] = Field(default_factory=lambda: ["road_bike"])
    season: str = Field(default="spring")
    max_weekly_tss: float | None = Field(default=None)
    available_dates: list[str] | None = Field(default=None)

    @field_validator("preferred_windows")
    @classmethod
    def valid_windows(cls, v: list[str]) -> list[str]:
        allowed = {"morning", "afternoon", "evening", "night"}
        return [w for w in v if w in allowed]


class WorkoutBlock(BaseModel):
    block_type: Literal["warmup", "main", "cooldown"] = "main"
    duration_minutes: int = Field(default=0, ge=0)
    intensity_pct_ftp: float | None = Field(default=None)
    target_zone: str = Field(default="Z2")
    description: str = Field(default="")
    repetition_count: int = Field(default=1, ge=1)
    repetition_duration_min: int | None = Field(default=None)
    repetition_rest_min: int | None = Field(default=None)


class Workout(BaseModel):
    date: str = Field(..., min_length=10, max_length=10)
    title: str = Field(default="", max_length=120)
    workout_type: WorkoutType = Field(default=WorkoutType.ENDURANCE)
    duration_minutes: int = Field(default=60, ge=1, le=600)
    distance_target_km: float | None = Field(default=None)
    elevation_gain_m: int = Field(default=0, ge=0)
    intensity_pct_ftp: float | None = Field(default=None)
    target_zone: str = Field(default="Z2")
    rpe_target: int | None = Field(default=None, ge=1, le=10)
    blocks: list[WorkoutBlock] = Field(default_factory=list)
    notes: str = Field(default="", max_length=500)
    estimated_tss: float = Field(default=0.0, ge=0)

    def total_block_minutes(self) -> int:
        return sum(b.duration_minutes for b in self.blocks)


class WeeklyPlan(BaseModel):
    plan_name: str = Field(default="Weekly Training Plan")
    start_date: str = Field(..., min_length=10, max_length=10)
    end_date: str = Field(..., min_length=10, max_length=10)
    days: list[Workout] = Field(default_factory=list)
    total_tss: float = Field(default=0.0, ge=0)
    total_distance_km: float = Field(default=0.0, ge=0)
    total_duration_min: int = Field(default=0, ge=0)
    microcycle_weeks: int = Field(default=1, ge=1, le=52)
    phase: str = Field(default="base")
    generated_at: str = Field(default="")
    parameters: dict = Field(default_factory=dict)


class AdaptationEvent(BaseModel):
    event_type: AdaptationEventType
    planned_workout: Workout | None = Field(default=None)
    actual_data: dict = Field(default_factory=dict)
    occurred_date: str = Field(..., min_length=10, max_length=10)


class Scenario(BaseModel):
    scenario_type: ScenarioType
    label: str = Field(default="")
    description: str = Field(default="")
    plan: WeeklyPlan = Field(...)
    score: float = Field(default=0.0)
    rationale: str = Field(default="")


__all__ = [
    "AdaptationEvent",
    "AdaptationEventType",
    "GoalType",
    "PlanConstraints",
    "Scenario",
    "ScenarioType",
    "TrainingGoal",
    "WeeklyPlan",
    "Workout",
    "WorkoutBlock",
    "WorkoutType",
]
