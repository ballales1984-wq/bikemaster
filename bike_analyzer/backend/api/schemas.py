"""Pydantic schemas for API request/response validation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RideCreate(BaseModel):
    date: str = Field(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    distance_km: float = Field(default=0.0, ge=0, le=500)
    duration_minutes: float = Field(default=0.0, ge=1, le=1440)
    avg_speed_kmh: float | None = Field(default=None, ge=0, le=150)
    weight_kg: float = Field(default=70.0, ge=20, le=300)
    calories: float | None = Field(default=None, ge=0, le=50000)
    heart_rate_avg: float | None = Field(default=None, ge=30, le=220)
    elevation_gain_m: float | None = Field(default=None, ge=0, le=15000)
    gps_points: list[dict] | None = None


class RideResponse(RideCreate):
    id: int | None = None
    created_at: str | None = None


class AthleteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    age: int = Field(default=30, ge=10, le=100)
    weight_kg: float = Field(default=70.0, ge=20, le=300)
    height_cm: float | None = Field(default=None, ge=100, le=250)
    fat_percentage: float | None = Field(default=None, ge=3, le=60)
    years_active: int = Field(default=1, ge=0, le=80)
    weekly_sessions: int = Field(default=3, ge=0, le=14)
    monthly_hours: float = Field(default=0.0, ge=0)
    annual_hours: float = Field(default=0.0, ge=0)
    experience_level: str = Field(default="Beginner")
    goals: str | None = Field(default=None, max_length=500)
    preferred_terrain: str | None = Field(default=None, max_length=100)
    weekly_volume_km: float = Field(default=0.0, ge=0)
    best_segments: str | None = Field(default=None, max_length=500)
    medical_notes: str | None = Field(default=None, max_length=500)
    equipment: str | None = Field(default=None, max_length=500)
    ftp_watts: float | None = Field(default=None, ge=50, le=500)


class AthleteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    age: int | None = Field(default=None, ge=10, le=100)
    weight_kg: float | None = Field(default=None, ge=20, le=300)
    height_cm: float | None = Field(default=None, ge=100, le=250)
    fat_percentage: float | None = Field(default=None, ge=3, le=60)
    years_active: int | None = Field(default=None, ge=0, le=80)
    weekly_sessions: int | None = Field(default=None, ge=0, le=14)
    monthly_hours: float | None = Field(default=None, ge=0)
    annual_hours: float | None = Field(default=None, ge=0)
    experience_level: str | None = Field(default=None)
    goals: str | None = Field(default=None, max_length=500)
    preferred_terrain: str | None = Field(default=None, max_length=100)
    weekly_volume_km: float | None = Field(default=None, ge=0)
    best_segments: str | None = Field(default=None, max_length=500)
    medical_notes: str | None = Field(default=None, max_length=500)
    equipment: str | None = Field(default=None, max_length=500)
    ftp_watts: float | None = Field(default=None, ge=50, le=500)


class MetricCreate(BaseModel):
    fatigue_score: float | None = Field(default=None, ge=0, le=10)
    recovery_hours: float | None = Field(default=None, ge=0)
    calories_per_km: float | None = Field(default=None, ge=0)
    efficiency_score: float | None = Field(default=None, ge=0, le=10)


class RideAnalysisRequest(BaseModel):
    rides: list[RideCreate]


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


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenWithRefresh(Token):
    refresh_token: str | None = None


class TokenData(BaseModel):
    username: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None = None
    is_admin: bool = False
    is_active: bool = True
    created_at: str | None = None


class CalendarEventCreate(BaseModel):
    athlete_id: int
    title: str = Field(..., min_length=1, max_length=200)
    event_type: str = Field(default="training", pattern="^(training|race|recovery|goal_deadline|test|other)$")
    date: str = Field(..., min_length=10, max_length=10)
    duration_minutes: int = Field(default=0, ge=0)
    description: str | None = Field(default=None, max_length=1000)
    completed: bool = False
    lat: float | None = None
    lon: float | None = None


class WeatherResponse(BaseModel):
    temperature: float | None = None
    humidity: float | None = None
    description: str | None = None
    wind_speed: float | None = None
    score: int = 5
    advice: str = ""


class CalendarEventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    event_type: str | None = Field(default=None, pattern="^(training|race|recovery|goal_deadline|test|other)$")
    date: str | None = Field(default=None, min_length=10, max_length=10)
    duration_minutes: int | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=1000)
    completed: bool | None = None


class TrainingStressRequest(BaseModel):
    athlete_id: int = Field(..., ge=1)
    ftp: float = Field(default=250.0, ge=50, le=500)


class FitnessSnapshot(BaseModel):
    date: str
    atl: float
    ctl: float
    tsb: float


class TrainingStressResponse(BaseModel):
    latest: FitnessSnapshot
    history: list[FitnessSnapshot]
    trend: str
    recommendation: str


class TrainingGoalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    goal_type: str = Field(default="granfondo", pattern="^(granfondo|race|fitness|fondo|custom)$")
    target_date: str | None = Field(default=None)
    target_distance_km: float | None = Field(default=None, ge=10, le=500)
    target_elevation_m: float | None = Field(default=None, ge=0, le=10000)


class PlannedWorkoutResponse(BaseModel):
    id: int | None = None
    date: str
    title: str
    workout_type: str
    duration_minutes: int
    target_intensity: float
    completed: bool = False


class HeatmapPoint(BaseModel):
    lat: float
    lon: float
    count: int = 1


class HeatmapResponse(BaseModel):
    points: list[HeatmapPoint]
    bounds: dict
    total_points: int


class BadgeResponse(BaseModel):
    id: int | None = None
    name: str
    description: str
    icon: str
    category: str
    achieved: bool = False
    achieved_date: str | None = None
    progress: float = 0.0
    target: float = 100.0


class GranfondoPlanRequest(BaseModel):
    athlete_id: int = Field(..., ge=1)
    start_date: str = Field(..., min_length=10, max_length=10)
    target_weeks: int = Field(default=8, ge=8, le=12)


class GoogleAuthRequest(BaseModel):
    code: str
    redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"


class GoogleOAuthCallback(BaseModel):
    code: str
    redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"


class CoachChatRequest(BaseModel):
    athlete_id: int | None = None
    message: str = Field(..., min_length=1)
