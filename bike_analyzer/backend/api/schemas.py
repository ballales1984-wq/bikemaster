"""Pydantic schemas for API request/response validation."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


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
    title: str | None = Field(default=None, max_length=150)
    external_source: str | None = Field(default=None, max_length=50)
    external_id: str | None = Field(default=None, max_length=100)


class RideResponse(RideCreate):
    id: int | None = None
    created_at: str | None = None


class RideUpdate(BaseModel):
    date: str | None = Field(default=None, min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    distance_km: float | None = Field(default=None, ge=0, le=500)
    duration_minutes: float | None = Field(default=None, ge=1, le=1440)
    avg_speed_kmh: float | None = Field(default=None, ge=0, le=150)
    weight_kg: float | None = Field(default=None, ge=20, le=300)
    calories: float | None = Field(default=None, ge=0, le=50000)
    heart_rate_avg: float | None = Field(default=None, ge=30, le=220)
    elevation_gain_m: float | None = Field(default=None, ge=0, le=15000)
    title: str | None = Field(default=None, max_length=150)


class AthleteCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    age: int = Field(default=30, ge=10, le=100)
    weight_kg: float = Field(default=70.0, ge=20, le=300)
    height_cm: float | None = Field(default=None, ge=100, le=250)
    fat_percentage: float | None = Field(default=None, ge=3, le=60)
    years_active: int = Field(default=1, ge=0, le=80)
    weekly_sessions: int = Field(default=3, ge=0, le=14)
    monthly_hours: float = Field(default=0.0, ge=0)
    annual_hours: float = Field(default=0.0, ge=0)
    experience_level: str = Field(default="Beginner", pattern="^(Beginner|Amateur|Intermediate|Advanced|Elite)$")
    goals: str | None = Field(default=None, max_length=500)
    preferred_terrain: str | None = Field(default=None, max_length=100)
    weekly_volume_km: float = Field(default=0.0, ge=0)
    best_segments: str | None = Field(default=None, max_length=500)
    medical_notes: str | None = Field(default=None, max_length=500)
    equipment: str | None = Field(default=None, max_length=500)
    ftp_watts: float | None = Field(default=None, ge=50, le=500)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return v
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Formato email non valido")
        return v


class AthleteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    age: int | None = Field(default=None, ge=10, le=100)
    weight_kg: float | None = Field(default=None, ge=20, le=300)
    height_cm: float | None = Field(default=None, ge=100, le=250)
    fat_percentage: float | None = Field(default=None, ge=3, le=60)
    years_active: int | None = Field(default=None, ge=0, le=80)
    weekly_sessions: int | None = Field(default=None, ge=0, le=14)
    monthly_hours: float | None = Field(default=None, ge=0)
    annual_hours: float | None = Field(default=None, ge=0)
    experience_level: str | None = Field(default=None, pattern="^(Beginner|Amateur|Intermediate|Advanced|Elite)$")
    goals: str | None = Field(default=None, max_length=500)
    preferred_terrain: str | None = Field(default=None, max_length=100)
    weekly_volume_km: float | None = Field(default=None, ge=0)
    best_segments: str | None = Field(default=None, max_length=500)
    medical_notes: str | None = Field(default=None, max_length=500)
    equipment: str | None = Field(default=None, max_length=500)
    ftp_watts: float | None = Field(default=None, ge=50, le=500)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return v
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Formato email non valido")
        return v


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    age: int | None = Field(default=None, ge=10, le=100)
    weight_kg: float | None = Field(default=None, ge=20, le=300)
    height_cm: float | None = Field(default=None, ge=100, le=250)
    experience_level: str | None = Field(default=None, pattern="^(Beginner|Amateur|Intermediate|Advanced|Elite)$")
    goals: str | None = Field(default=None, max_length=500)
    preferred_terrain: str | None = Field(default=None, max_length=100)
    weekly_volume_km: float | None = Field(default=None, ge=0)
    ftp_watts: float | None = Field(default=None, ge=50, le=500)
    equipment: str | None = Field(default=None, max_length=500)
    medical_notes: str | None = Field(default=None, max_length=500)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return v
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Formato email non valido")
        return v


class MetricCreate(BaseModel):
    fatigue_score: float | None = Field(default=None, ge=0, le=10)
    recovery_hours: float | None = Field(default=None, ge=0)
    calories_per_km: float | None = Field(default=None, ge=0)
    efficiency_score: float | None = Field(default=None, ge=0, le=10)


class RideAnalysisRequest(BaseModel):
    rides: list[RideCreate]


class BenchmarkCompareRequest(BaseModel):
    date: str = Field(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    distance_km: float = Field(..., gt=0, le=500)
    duration_minutes: float = Field(..., gt=0, le=1440)
    avg_speed_kmh: float | None = Field(default=None, ge=0, le=150)
    elevation_gain_m: float | None = Field(default=None, ge=0, le=15000)


class GoogleFitAuthQuery(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=256)
    redirect_uri: str = Field(default="http://localhost:8000/api/v1/import/google-fit/callback", max_length=2048)
    state: str = Field(default="", max_length=4096)


class GoogleFitTokenRequest(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=256)
    client_secret: str = Field(..., min_length=1, max_length=256)
    code: str = Field(..., min_length=1, max_length=2048)
    redirect_uri: str = Field(default="http://localhost:8000/api/v1/import/google-fit/callback", max_length=2048)


class GoogleFitImportPayload(BaseModel):
    access_token: str = Field(..., min_length=1, max_length=2048)
    refresh_token: str | None = Field(default=None, max_length=2048)


class GoogleHealthImportPayload(BaseModel):
    access_token: str = Field(..., min_length=1, max_length=2048)
    refresh_token: str | None = Field(default=None, max_length=2048)


class StravaCallbackRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=2048)
    code_verifier: str = Field(..., min_length=1, max_length=256)


class GarminCallbackRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=2048)
    redirect_uri: str | None = Field(default=None, max_length=2048)


class Token(BaseModel):
    access_token: str = Field(..., min_length=1, max_length=4096)
    token_type: str = Field(default="bearer", pattern="^(bearer|Bearer)$")


class TokenWithRefresh(Token):
    refresh_token: str | None = Field(default=None, max_length=4096)


class TokenData(BaseModel):
    username: str | None = Field(default=None, max_length=100)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1, max_length=4096)


class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return v
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Formato email non valido")
        return v


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None = None
    is_admin: bool = False
    is_active: bool = True
    created_at: str | None = None


class CalendarEventCreate(BaseModel):
    athlete_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=1, max_length=200)
    event_type: str = Field(default="training", pattern="^(training|race|recovery|goal_deadline|test|other)$")
    date: str = Field(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    duration_minutes: int = Field(default=0, ge=0, le=1440)
    description: str | None = Field(default=None, max_length=1000)
    completed: bool = False
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)


class WeatherResponse(BaseModel):
    temperature: float | None = Field(default=None)
    humidity: float | None = Field(default=None, ge=0, le=100)
    description: str | None = Field(default=None, max_length=100)
    wind_speed: float | None = Field(default=None, ge=0, le=200)
    score: int = Field(default=5, ge=1, le=10)
    advice: str = Field(default="", max_length=500)


class CalendarEventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    event_type: str | None = Field(default=None, pattern="^(training|race|recovery|goal_deadline|test|other)$")
    date: str | None = Field(default=None, min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    duration_minutes: int | None = Field(default=None, ge=0, le=1440)
    description: str | None = Field(default=None, max_length=1000)
    completed: bool | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)


class TrainingStressRequest(BaseModel):
    athlete_id: int = Field(..., gt=0)
    ftp: float = Field(default=250.0, ge=50, le=500)


class FitnessSnapshot(BaseModel):
    date: str = Field(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    atl: float = Field(..., ge=0)
    ctl: float = Field(..., ge=0)
    tsb: float


class TrainingStressResponse(BaseModel):
    latest: FitnessSnapshot
    history: list[FitnessSnapshot]
    trend: str = Field(..., min_length=1, max_length=50)
    recommendation: str = Field(..., min_length=1, max_length=1000)


class TrainingGoalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    goal_type: str = Field(default="granfondo", pattern="^(granfondo|race|fitness|fondo|custom)$")
    target_date: str | None = Field(default=None, min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    target_distance_km: float | None = Field(default=None, ge=10, le=500)
    target_elevation_m: float | None = Field(default=None, ge=0, le=10000)


class PlannedWorkoutResponse(BaseModel):
    id: int | None = None
    date: str = Field(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    title: str = Field(..., min_length=1, max_length=200)
    workout_type: str = Field(..., min_length=1, max_length=100)
    duration_minutes: int = Field(..., gt=0, le=1440)
    target_intensity: float = Field(..., ge=0, le=1)
    completed: bool = False


class HeatmapPoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    count: int = Field(default=1, ge=1, le=10000)


class HeatmapResponse(BaseModel):
    points: list[HeatmapPoint]
    bounds: dict = Field(..., min_length=1)
    total_points: int = Field(..., ge=0)


class BadgeResponse(BaseModel):
    id: int | None = None
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    icon: str = Field(..., min_length=1, max_length=50)
    category: str = Field(..., min_length=1, max_length=50)
    achieved: bool = False
    achieved_date: str | None = Field(default=None, min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    progress: float = Field(default=0.0, ge=0, le=100)
    target: float = Field(default=100.0, ge=0, le=100)


class GranfondoPlanRequest(BaseModel):
    athlete_id: int = Field(..., gt=0)
    start_date: str = Field(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    target_weeks: int = Field(default=8, ge=8, le=12)


class GoogleAuthRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=2048)
    redirect_uri: str = Field(default="http://localhost:8000/api/v1/auth/google/callback", max_length=2048)


class GoogleOAuthCallback(BaseModel):
    code: str = Field(..., min_length=1, max_length=2048)
    redirect_uri: str = Field(default="http://localhost:8000/api/v1/auth/google/callback", max_length=2048)


class CoachChatRequest(BaseModel):
    athlete_id: int | None = Field(default=None, ge=0)
    message: str = Field(..., min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message cannot be empty")
        return stripped
