"""Load Manager — Pydantic models.

Spec (agent): "Modelli Pydantic per TrainingStress, ChronicLoad, LoadBalance".
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .config import AthleteLevel


class StressMethod(str, Enum):
    POWER = "power"
    MET = "met"
    HR = "heart_rate"


class TrainingStress(BaseModel):
    """Result of a single-ride TSS calculation."""

    ride_id: Optional[int] = None
    date: str
    tss: float = Field(..., ge=0.0)
    intensity_factor: float = Field(..., ge=0.0)
    normalized_power: Optional[float] = Field(None, ge=0.0)
    avg_power: Optional[float] = Field(None, ge=0.0)
    method: StressMethod = StressMethod.MET
    duration_hours: float = Field(..., ge=0.0)
    ftp_watts: Optional[float] = Field(None, ge=0.0)
    elevation_gain_m: Optional[float] = Field(None, ge=0.0)
    terrain_correction: float = Field(0.0)


class ChronicLoad(BaseModel):
    """CTL/ATL/TSB state for a given date."""

    date: str
    ctl: float = Field(..., ge=0.0)
    atl: float = Field(..., ge=0.0)
    tsb: float
    tss: float = Field(0.0, ge=0.0)
    acwr: Optional[float] = Field(None, ge=0.0)


class LoadBalance(BaseModel):
    """Weekly load target and current standing for an athlete level."""

    level: AthleteLevel
    min_tss_per_week: float
    max_tss_per_week: float
    target_tss_per_week: float
    current_week_tss: float
    remaining_tss: float
    remaining_rides: int
    recommended_per_ride: float
    in_balance: bool


__all__ = ["StressMethod", "TrainingStress", "ChronicLoad", "LoadBalance"]
