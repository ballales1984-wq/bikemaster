"""Pydantic schemas for API request/response validation."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class RideCreate(BaseModel):
    date: str = Field(..., min_length=1)
    distance_km: float = Field(default=0.0, ge=0)
    duration_minutes: float = Field(default=0.0, ge=0)
    avg_speed_kmh: float = Field(default=0.0, ge=0)
    weight_kg: float = Field(default=70.0, ge=20, le=300)
    calories: float = Field(default=0.0, ge=0)
    heart_rate_avg: Optional[float] = Field(default=None, ge=30, le=220)
    elevation_gain_m: Optional[float] = Field(default=None, ge=0)
    gps_points: Optional[List[dict]] = None

class RideResponse(RideCreate):
    id: Optional[int] = None
    created_at: Optional[str] = None

class AthleteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(default=30, ge=10, le=100)
    weight_kg: float = Field(default=70.0, ge=20, le=300)
    height_cm: Optional[float] = Field(default=None, ge=100, le=250)
    fat_percentage: Optional[float] = Field(default=None, ge=3, le=60)
    years_active: int = Field(default=1, ge=0, le=80)
    weekly_sessions: int = Field(default=3, ge=0, le=14)
    monthly_hours: float = Field(default=0.0, ge=0)
    annual_hours: float = Field(default=0.0, ge=0)
    experience_level: str = Field(default="Beginner")

class AthleteUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    age: Optional[int] = Field(default=None, ge=10, le=100)
    weight_kg: Optional[float] = Field(default=None, ge=20, le=300)
    height_cm: Optional[float] = Field(default=None, ge=100, le=250)
    fat_percentage: Optional[float] = Field(default=None, ge=3, le=60)
    years_active: Optional[int] = Field(default=None, ge=0, le=80)
    weekly_sessions: Optional[int] = Field(default=None, ge=0, le=14)
    monthly_hours: Optional[float] = Field(default=None, ge=0)
    annual_hours: Optional[float] = Field(default=None, ge=0)
    experience_level: Optional[str] = Field(default=None)

class MetricCreate(BaseModel):
    fatigue_score: Optional[float] = Field(default=None, ge=0, le=10)
    recovery_hours: Optional[float] = Field(default=None, ge=0)
    calories_per_km: Optional[float] = Field(default=None, ge=0)
    efficiency_score: Optional[float] = Field(default=None, ge=0, le=10)

class RideAnalysisRequest(BaseModel):
    rides: List[RideCreate]

class GoogleFitAuthQuery(BaseModel):
    client_id: str
    redirect_uri: str = "http://localhost:8000/api/v1/import/google-fit/callback"
    state: str = ""

class GoogleFitTokenRequest(BaseModel):
    client_id: str
    client_secret: str
    code: str
    redirect_uri: str = "http://localhost:8000/api/v1/import/google-fit/callback"

class GoogleFitImportRequest(BaseModel):
    access_token: str
