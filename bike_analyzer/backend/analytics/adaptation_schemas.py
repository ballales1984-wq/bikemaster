"""Pydantic request/response schemas for the adaptation API."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventType(StrEnum):
    SKIPPED_RIDE = "skipped_ride"
    PARTIAL_RIDE = "partial_ride"
    LONGER_RIDE = "longer_ride"
    LOW_RECOVERY = "low_recovery"
    GOAL_CHANGE = "goal_change"
    CALENDAR_BLOCK = "calendar_block"
    BAD_WEATHER = "bad_weather"


class AdaptationStrategy(StrEnum):
    RECOVER_VOLUME = "recover_volume"
    MAINTAIN = "maintain"
    QUALITY_SWAP = "quality_swap"
    RECOVERY_ONLY = "recovery_only"
    REDUCE_OVERLOAD = "reduce_overload"


class WorkoutPlanItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: str
    workout_type: str
    distance_km: float = 0.0
    duration_minutes: float = 0.0
    intensity_factor: float = 0.6
    title: str = ""
    description: str = ""
    is_recovery: bool = False
    locked: bool = False


class AthleteStateIn(BaseModel):
    fatigue_score: float = 0.0
    readiness: float = 100.0
    acwr: float = 1.0
    tsb: float = 0.0
    atl: float = 0.0
    ctl: float = 0.0


class AdaptationRequest(BaseModel):
    event_type: EventType
    planned: list[WorkoutPlanItem]
    skipped_index: int = 0
    actual_km: float | None = None
    actual_minutes: float | None = None
    current_acute_load: float = 0.0
    athlete_state: AthleteStateIn = Field(default_factory=AthleteStateIn)
    from_index: int = 0


class LoadRedistributionOut(BaseModel):
    missing_km: float
    missing_minutes: float
    affected_workouts: list[dict[str, Any]]
    resulting_acwr: float
    safe: bool
    note: str


class AdaptationResponse(BaseModel):
    triggered_by: str
    strategy: str
    rationale: str
    alerts: list[str]
    redistribution: LoadRedistributionOut | None = None
    original_plan: list[WorkoutPlanItem]
    adapted_plan: list[WorkoutPlanItem]
    audit: dict[str, Any]
    generated_at: datetime
