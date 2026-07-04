"""Pydantic-based validation models for BikeMaster.

These models validate incoming data (API requests, file imports, external sources)
before it reaches the core domain layer. They wrap existing dataclass models
with strong type constraints and business rules.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class ValidatedGPSPoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitudine WGS84")
    lon: float = Field(..., ge=-180, le=180, description="Longitudine WGS84")
    timestamp: datetime
    altitude: float | None = Field(None, ge=-500, le=9000)
    speed: float | None = Field(None, ge=0, le=120)
    power: float | None = Field(None, ge=0, le=2000)
    heart_rate: int | None = Field(None, ge=30, le=220)
    cadence: int | None = Field(None, ge=0, le=200)

    @field_validator("timestamp")
    @classmethod
    def timestamp_not_in_future(cls, v: datetime) -> datetime:

        now = datetime.now(UTC)
        if v.tzinfo is None:
            v = v.replace(tzinfo=UTC)
        if v > now:
            raise ValueError("Timestamp futuro non consentito")
        return v


class ValidatedRide(BaseModel):
    athlete_id: int = Field(..., gt=0)
    date: date
    distance_km: float = Field(..., gt=0, le=500)
    duration_minutes: float = Field(..., gt=0, le=1440)
    avg_speed_kmh: float | None = Field(None, ge=0, le=80)
    elevation_gain_m: float | None = Field(None, ge=0, le=15000)
    calories: float | None = Field(None, ge=0)
    gps_points: list[ValidatedGPSPoint] = Field(default_factory=list)
    title: str | None = Field(None, max_length=150)
    external_source: str | None = None
    external_id: str | None = None

    @model_validator(mode="after")
    def validate_ride_consistency(self) -> ValidatedRide:
        if self.gps_points and len(self.gps_points) < 2:
            raise ValueError("Una ride valida richiede almeno 2 punti GPS")

        if self.distance_km > 0 and self.duration_minutes > 0:
            calculated = (self.distance_km / self.duration_minutes) * 60
            if self.avg_speed_kmh and abs(calculated - self.avg_speed_kmh) > 25:
                raise ValueError(
                    f"Velocita media incoerente: "
                    f"distanza={self.distance_km}km, durata={self.duration_minutes}min "
                    f"-> calcolata={calculated:.1f}km/h, dichiarata={self.avg_speed_kmh}km/h"
                )
        return self


class ValidatedAthleteProfile(BaseModel):
    id: int | None = None
    name: str = Field(..., min_length=2, max_length=100)
    age: int = Field(..., ge=10, le=100)
    weight_kg: float = Field(..., gt=30, le=200)
    height_cm: float | None = Field(None, ge=100, le=250)
    ftp_watts: int | None = Field(None, ge=50, le=600)
    experience_level: str = Field(..., pattern="^(Beginner|Intermediate|Advanced|Elite)$")

    @field_validator("weight_kg")
    @classmethod
    def realistic_weight(cls, v: float) -> float:
        if v < 40 or v > 150:
            raise ValueError("Peso non realistico per un ciclista")
        return v
