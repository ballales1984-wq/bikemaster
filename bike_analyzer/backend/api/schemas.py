"""Pydantic schemas for API request/response validation."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class RideCreate(BaseModel):
    """Schema di richiesta per creare una nuova uscita/ride."""
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
    activity_type: str | None = Field(default="ride", pattern="^(ride|walk|hike|run|indoor|other)$")
    is_official: bool | None = Field(default=True)
    source: str | None = Field(default="manual", max_length=50)


class RideResponse(RideCreate):
    """Schema di risposta per una ride (include id e timestamp)."""

    id: int | None = None
    created_at: str | None = None
    tenant_id: int = 0


class RideUpdate(BaseModel):
    """Schema di richiesta per aggiornare una ride (campi opzionali)."""
    date: str | None = Field(default=None, min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    distance_km: float | None = Field(default=None, ge=0, le=500)
    duration_minutes: float | None = Field(default=None, ge=1, le=1440)
    avg_speed_kmh: float | None = Field(default=None, ge=0, le=150)
    weight_kg: float | None = Field(default=None, ge=20, le=300)
    calories: float | None = Field(default=None, ge=0, le=50000)
    heart_rate_avg: float | None = Field(default=None, ge=30, le=220)
    elevation_gain_m: float | None = Field(default=None, ge=0, le=15000)
    title: str | None = Field(default=None, max_length=150)
    activity_type: str | None = Field(default=None, pattern="^(ride|walk|hike|run|indoor|other)$")
    is_official: bool | None = Field(default=None)
    source: str | None = Field(default=None, max_length=50)


class AthleteCreate(BaseModel):
    """Schema di richiesta per creare un profilo atleta."""
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
    body_water_percentage: float | None = Field(default=None, ge=0, le=100)
    muscle_mass_percentage: float | None = Field(default=None, ge=0, le=100)
    bmr_kcal: float | None = Field(default=None, ge=500, le=10000)
    fat_mass_kg: float | None = Field(default=None, ge=0, le=300)
    subcutaneous_fat_kg: float | None = Field(default=None, ge=0, le=100)
    subcutaneous_fat_percentage: float | None = Field(default=None, ge=0, le=100)
    visceral_fat_level: float | None = Field(default=None, ge=1, le=59)
    visceral_fat_percentage: float | None = Field(default=None, ge=0, le=100)
    visceral_fat_kg: float | None = Field(default=None, ge=0, le=50)
    muscle_mass_kg: float | None = Field(default=None, ge=0, le=120)
    bone_mass_kg: float | None = Field(default=None, ge=0, le=20)
    protein_percentage: float | None = Field(default=None, ge=0, le=100)
    protein_kg: float | None = Field(default=None, ge=0, le=100)
    body_age: int | None = Field(default=None, ge=10, le=100)
    apparent_age: int | None = Field(default=None, ge=10, le=100)
    bmi: float | None = Field(default=None, ge=0, le=100)
    lean_body_mass_kg: float | None = Field(default=None, ge=0, le=300)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Valida il formato email (deve contenere @ e dominio)."""
        if v is None or v == "":
            return v
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Formato email non valido")
        return v


class AthleteUpdate(BaseModel):
    """Schema di richiesta per aggiornare un profilo atleta (campi opzionali)."""
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
    body_water_percentage: float | None = Field(default=None, ge=0, le=100)
    muscle_mass_percentage: float | None = Field(default=None, ge=0, le=100)
    bmr_kcal: float | None = Field(default=None, ge=500, le=10000)
    fat_mass_kg: float | None = Field(default=None, ge=0, le=300)
    subcutaneous_fat_kg: float | None = Field(default=None, ge=0, le=100)
    subcutaneous_fat_percentage: float | None = Field(default=None, ge=0, le=100)
    visceral_fat_level: float | None = Field(default=None, ge=1, le=59)
    visceral_fat_percentage: float | None = Field(default=None, ge=0, le=100)
    visceral_fat_kg: float | None = Field(default=None, ge=0, le=50)
    muscle_mass_kg: float | None = Field(default=None, ge=0, le=120)
    bone_mass_kg: float | None = Field(default=None, ge=0, le=20)
    protein_percentage: float | None = Field(default=None, ge=0, le=100)
    protein_kg: float | None = Field(default=None, ge=0, le=100)
    body_age: int | None = Field(default=None, ge=10, le=100)
    apparent_age: int | None = Field(default=None, ge=10, le=100)
    bmi: float | None = Field(default=None, ge=0, le=100)
    lean_body_mass_kg: float | None = Field(default=None, ge=0, le=300)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Valida il formato email (deve contenere @ e dominio)."""
        if v is None or v == "":
            return v
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Formato email non valido")
        return v


class ProfileUpdate(BaseModel):
    """Schema di richiesta per aggiornare il profilo utente (campi opzionali)."""
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
    fat_percentage: float | None = Field(default=None, ge=2, le=60)
    mood: float | None = Field(default=None, ge=1, le=10)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    equipment: str | None = Field(default=None, max_length=500)
    medical_notes: str | None = Field(default=None, max_length=500)
    body_water_percentage: float | None = Field(default=None, ge=0, le=100)
    muscle_mass_percentage: float | None = Field(default=None, ge=0, le=100)
    bmr_kcal: float | None = Field(default=None, ge=500, le=10000)
    fat_mass_kg: float | None = Field(default=None, ge=0, le=300)
    subcutaneous_fat_kg: float | None = Field(default=None, ge=0, le=100)
    subcutaneous_fat_percentage: float | None = Field(default=None, ge=0, le=100)
    visceral_fat_level: float | None = Field(default=None, ge=1, le=59)
    visceral_fat_percentage: float | None = Field(default=None, ge=0, le=100)
    visceral_fat_kg: float | None = Field(default=None, ge=0, le=50)
    muscle_mass_kg: float | None = Field(default=None, ge=0, le=120)
    bone_mass_kg: float | None = Field(default=None, ge=0, le=20)
    protein_percentage: float | None = Field(default=None, ge=0, le=100)
    protein_kg: float | None = Field(default=None, ge=0, le=100)
    body_age: int | None = Field(default=None, ge=10, le=100)
    apparent_age: int | None = Field(default=None, ge=10, le=100)
    bmi: float | None = Field(default=None, ge=0, le=100)
    lean_body_mass_kg: float | None = Field(default=None, ge=0, le=300)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Valida il formato email (deve contenere @ e dominio)."""
        if v is None or v == "":
            return v
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Formato email non valido")
        return v


class MetricCreate(BaseModel):
    """Schema di richiesta per creare metriche di performance."""

    fatigue_score: float | None = Field(default=None, ge=0, le=10)
    recovery_hours: float | None = Field(default=None, ge=0)
    calories_per_km: float | None = Field(default=None, ge=0)
    efficiency_score: float | None = Field(default=None, ge=0, le=10)


class RideAnalysisRequest(BaseModel):
    """Schema di richiesta per analisi di una lista di ride."""

    rides: list[RideCreate]


class BenchmarkCompareRequest(BaseModel):
    """Schema di richiesta per confronto benchmark."""

    date: str = Field(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    distance_km: float = Field(..., gt=0, le=500)
    duration_minutes: float = Field(..., gt=0, le=1440)
    avg_speed_kmh: float | None = Field(default=None, ge=0, le=150)
    elevation_gain_m: float | None = Field(default=None, ge=0, le=15000)


class GoogleFitAuthQuery(BaseModel):
    """Parametri di query per l'autenticazione Google Fit OAuth2."""

    client_id: str = Field(..., min_length=1, max_length=256)
    redirect_uri: str = Field(default="http://localhost:8000/api/v1/import/google-fit/callback", max_length=2048)
    state: str = Field(default="", max_length=4096)


class GoogleFitTokenRequest(BaseModel):
    """Schema di richiesta per scambio codice OAuth2 Google Fit."""

    client_id: str = Field(..., min_length=1, max_length=256)
    client_secret: str = Field(..., min_length=1, max_length=256)
    code: str = Field(..., min_length=1, max_length=2048)
    redirect_uri: str = Field(default="http://localhost:8000/api/v1/import/google-fit/callback", max_length=2048)


class GoogleFitImportPayload(BaseModel):
    """Payload per import dati da Google Fit."""

    access_token: str = Field(..., min_length=1, max_length=2048)
    refresh_token: str | None = Field(default=None, max_length=2048)


class GoogleHealthImportPayload(BaseModel):
    """Payload per import dati da Google Health Connect."""

    access_token: str = Field(..., min_length=1, max_length=2048)
    refresh_token: str | None = Field(default=None, max_length=2048)


class StravaCallbackRequest(BaseModel):
    """Payload di callback OAuth2 da Strava."""

    code: str = Field(..., min_length=1, max_length=2048)
    code_verifier: str = Field(..., min_length=1, max_length=256)


class GarminCallbackRequest(BaseModel):
    """Payload di callback OAuth2 da Garmin."""

    code: str = Field(..., min_length=1, max_length=2048)
    redirect_uri: str | None = Field(default=None, max_length=2048)


class WahooCallbackRequest(BaseModel):
    """Payload di callback OAuth2 da Wahoo."""

    code: str = Field(..., min_length=1, max_length=2048)
    code_verifier: str = Field(..., min_length=1, max_length=256)


class BleDeviceRegister(BaseModel):
    """Schema di registrazione di un dispositivo BLE."""

    device_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=200)
    device_type: str = Field(default="weight_scale", pattern="^(weight_scale|heart_rate|blood_pressure|thermometer|generic)$")
    service_uuid: str | None = Field(default=None, max_length=36)
    characteristic_uuid: str | None = Field(default=None, max_length=36)
    mac_address: str | None = Field(default=None, max_length=24)


class BleDeviceUpdate(BaseModel):
    """Schema di aggiornamento di un dispositivo BLE."""

    name: str | None = Field(default=None, max_length=200)
    paired: bool | None = None
    settings: str | None = Field(default=None, max_length=2048)


class BleDeviceOut(BaseModel):
    """Schema di risposta per un dispositivo BLE."""

    id: int
    athlete_id: int
    tenant_id: int
    device_id: str
    name: str
    device_type: str
    service_uuid: str | None
    characteristic_uuid: str | None
    mac_address: str | None
    paired: bool
    last_connected_at: str | None
    last_synced_at: str | None
    settings: str
    created_at: str | None
    updated_at: str | None

    model_config = {"from_attributes": True}


class BleDeviceSync(BaseModel):
    """Payload per la sincronizzazione di un dato misurato da un dispositivo BLE.

    Il frontend si occupa di connettersi al dispositivo via Web Bluetooth,
    leggere la caratteristica e parsare il valore, quindi lo invia qui.
    """

    value: float | None = Field(default=None, ge=-1000, le=1000)
    unit: str | None = Field(default=None, max_length=20)
    recorded_at: str | None = Field(default=None, max_length=32)


class HealthConnectPayload(BaseModel):
    """Payload per sincronizzazione dati da Android Health Connect."""

    metrics: list[dict] = Field(default_factory=list)
    source: str = Field(default="health_connect")


class HrSampleCreate(BaseModel):
    """Un singolo campione di frequenza cardiaca per il tracciamento 24h."""

    heart_rate: int = Field(..., ge=1, le=300)
    recorded_at: str | None = Field(default=None, max_length=32)
    source: str | None = Field(default="ble")
    device_id: str | None = Field(default=None)


class HrSamplesBulk(BaseModel):
    """Payload per l'inserimento bulk di campioni HR 24h."""

    samples: list[HrSampleCreate]
    source: str | None = Field(default="ble")


class HrMonitoringSettings(BaseModel):
    """Impostazioni del tracciamento HR 24h."""

    enabled: bool = True
    interval_seconds: int = Field(default=30, ge=5, le=3600)
    source: str = Field(default="ble")
    device_id: str | None = None
    max_hr: int | None = Field(default=None, ge=50, le=300)
    resting_hr: int | None = Field(default=None, ge=30, le=250)


class Hr24hSummary(BaseModel):
    """Riepilogo giornaliero della frequenza cardiaca."""

    day: str
    resting_hr: int | None = None
    avg_hr: float | None = None
    max_hr: int | None = None
    min_hr: int | None = None
    sample_count: int = 0


class SensorSample(BaseModel):
    """Raw BLE sensor reading (heart-rate, GPS, accelerometer)."""

    ts: str
    heart_rate: int | None = Field(default=None, ge=0, le=300)
    lat: float | None = None
    lng: float | None = None
    altitude: float | None = None
    accel_x: float | None = None
    accel_y: float | None = None
    accel_z: float | None = None
    speed_kmh: float | None = None


class SensorSamplesBulk(BaseModel):
    """Bulk payload for raw sensor data."""

    samples: list[SensorSample]


class ActivityClassification(BaseModel):
    """Daily activity classification derived from HR + GPS + movement."""

    date: str
    label: str = Field(..., pattern=r"^(sleep|recovery|active|rest)$")
    hr_resting: int | None = None
    hr_avg: float | None = None
    hours: float | None = None
    steps_estimated: int | None = None
    distance_km: float | None = None
    rides_count: int | None = None
    confidence: float | None = None


class ActivitySummaryResponse(BaseModel):
    """Paginated activity classification summary."""

    history: list[ActivityClassification]




class Token(BaseModel):
    """Token di accesso JWT."""

    access_token: str = Field(..., min_length=1, max_length=4096)
    token_type: str = Field(default="bearer", pattern="^(bearer|Bearer)$")


class TokenWithRefresh(Token):
    """Token di accesso con refresh token incluso."""

    refresh_token: str | None = Field(default=None, max_length=4096)


class TokenData(BaseModel):
    """Dati decodificati dal token JWT."""

    username: str | None = Field(default=None, max_length=100)


class RefreshTokenRequest(BaseModel):
    """Schema di richiesta per refresh del token JWT."""

    refresh_token: str = Field(..., min_length=1, max_length=4096)


class UserLogin(BaseModel):
    """Schema di richiesta per login utente."""

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)


class UserCreate(BaseModel):
    """Schema di richiesta per creazione utente."""

    username: str = Field(..., min_length=3, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Valida il formato email (deve contenere @ e dominio)."""
        if v is None or v == "":
            return v
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Formato email non valido")
        return v


class UserResponse(BaseModel):
    """Schema di risposta per dati utente (senza password)."""

    id: int
    username: str
    email: str | None = None
    is_admin: bool = False
    is_client: bool = False
    is_active: bool = True
    created_at: str | None = None


class UserUpdate(BaseModel):
    """Schema di richiesta per aggiornamento utente (campi opzionali)."""

    email: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=100)
    is_admin: bool | None = None
    is_client: bool | None = None
    is_active: bool | None = None


class CalendarEventCreate(BaseModel):
    """Schema di richiesta per creare un evento di calendario."""

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
    """Schema di risposta per dati meteo."""

    temperature: float | None = Field(default=None)
    humidity: float | None = Field(default=None, ge=0, le=100)
    description: str | None = Field(default=None, max_length=100)
    wind_speed: float | None = Field(default=None, ge=0, le=200)
    score: int = Field(default=5, ge=1, le=10)
    advice: str = Field(default="", max_length=500)


class CalendarEventUpdate(BaseModel):
    """Schema di richiesta per aggiornare un evento di calendario (campi opzionali)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    event_type: str | None = Field(default=None, pattern="^(training|race|recovery|goal_deadline|test|other)$")
    date: str | None = Field(default=None, min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    duration_minutes: int | None = Field(default=None, ge=0, le=1440)
    description: str | None = Field(default=None, max_length=1000)
    completed: bool | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)


class TrainingStressRequest(BaseModel):
    """Schema di richiesta per calcolo stress di allenamento."""

    athlete_id: int = Field(..., gt=0)
    ftp: float = Field(default=250.0, ge=50, le=500)


class FitnessSnapshot(BaseModel):
    """Snapshot ATL/CTL/TSB per una data specifica."""

    date: str = Field(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    atl: float = Field(..., ge=0)
    ctl: float = Field(..., ge=0)
    tsb: float


class TrainingStressResponse(BaseModel):
    """Schema di risposta per analisi stress di allenamento."""

    latest: FitnessSnapshot
    history: list[FitnessSnapshot]
    trend: str = Field(..., min_length=1, max_length=50)
    recommendation: str = Field(..., min_length=1, max_length=1000)


class TrainingGoalCreate(BaseModel):
    """Schema di richiesta per creare un obiettivo di allenamento."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    goal_type: str = Field(default="granfondo", pattern="^(granfondo|race|fitness|fondo|custom)$")
    target_date: str | None = Field(default=None, min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    target_distance_km: float | None = Field(default=None, ge=10, le=500)
    target_elevation_m: float | None = Field(default=None, ge=0, le=10000)


class PlannedWorkoutResponse(BaseModel):
    """Schema di risposta per una sessione di allenamento programmata."""

    id: int | None = None
    date: str = Field(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    title: str = Field(..., min_length=1, max_length=200)
    workout_type: str = Field(..., min_length=1, max_length=100)
    duration_minutes: int = Field(..., gt=0, le=1440)
    target_intensity: float = Field(..., ge=0, le=1)
    completed: bool = False


class HeatmapPoint(BaseModel):
    """Punto della heatmap di attivita'."""

    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    count: int = Field(default=1, ge=1, le=10000)


class HeatmapResponse(BaseModel):
    """Schema di risposta per heatmap di attivita'."""

    points: list[HeatmapPoint]
    bounds: dict = Field(..., min_length=1)
    total_points: int = Field(..., ge=0)


class BadgeResponse(BaseModel):
    """Schema di risposta per badge/achievement."""

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
    """Schema di richiesta per generare piano allenamento granfondo."""

    athlete_id: int = Field(..., gt=0)
    start_date: str = Field(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    target_weeks: int = Field(default=8, ge=8, le=12)


class GranfondoPlanWorkout(BaseModel):
    """Singola sessione di allenamento nel piano granfondo."""

    date: str = Field(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    title: str = Field(..., min_length=1, max_length=200)
    workout_type: str = Field(default="training", min_length=1, max_length=100)
    duration_minutes: int = Field(default=0, ge=0, le=1440)
    target_intensity: float = Field(default=0.0, ge=0, le=1)
    description: str | None = Field(default=None, max_length=1000)


class GranfondoSaveRequest(BaseModel):
    """Schema di richiesta per salvare un piano granfondo."""

    plan: list[GranfondoPlanWorkout] = Field(..., min_length=1, max_length=200)
    athlete_id: int | None = Field(default=None, gt=0)


class GoogleAuthRequest(BaseModel):
    """Schema di richiesta per autenticazione Google OAuth2."""

    code: str = Field(..., min_length=1, max_length=2048)
    redirect_uri: str = Field(default="http://localhost:8000/api/v1/auth/google/callback", max_length=2048)


class GoogleOAuthCallback(BaseModel):
    """Payload di callback OAuth2 da Google."""

    code: str = Field(..., min_length=1, max_length=2048)
    redirect_uri: str = Field(default="http://localhost:8000/api/v1/auth/google/callback", max_length=2048)


class CoachChatRequest(BaseModel):
    """Schema di richiesta per chat con AI Coach."""

    athlete_id: int | None = Field(default=None, ge=0)
    message: str = Field(..., min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Valida che il messaggio non sia vuoto dopo strip."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message cannot be empty")
        return stripped


POI_TYPES = ("vista", "fontana", "ristoro", "bivio", "pericolo", "culturale", "tecnico")
_POI_TYPE_PATTERN = "^(" + "|".join(POI_TYPES) + ")$"


class POICreate(BaseModel):
    """Schema di richiesta per creare un Point of Interest."""

    name: str = Field(..., min_length=3, max_length=120)
    description: str = Field(..., max_length=2000)
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    type: str = Field(..., pattern=_POI_TYPE_PATTERN)
    photos: list[str] = Field(default_factory=list, max_length=20)
    video_url: str | None = Field(default=None, max_length=2000)
    difficulty_note: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=20)
    itinerary_id: int | None = Field(default=None, gt=0)


class POIResponse(POICreate):
    """Schema di risposta per un Point of Interest (include id e metadata)."""

    id: int | None = None
    created_by: int | None = None
    tenant_id: int | None = None
    created_at: str | None = None


class ItineraryCreate(BaseModel):
    """Schema di richiesta per creare un itinerario."""

    name: str = Field(..., min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    start_date: str | None = Field(
        default=None, min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    end_date: str | None = Field(
        default=None, min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    total_km: float | None = Field(default=None, ge=0, le=100000)
    total_elevation_m: float | None = Field(default=None, ge=0, le=100000)


class ItineraryResponse(ItineraryCreate):
    """Schema di risposta per un itinerario (include id e metadata)."""

    id: int | None = None
    athlete_id: int | None = None
    tenant_id: int = 0
    created_at: str | None = None


class StageCreate(BaseModel):
    """Schema di richiesta per creare una tappa di un itinerario."""

    stage_day: int = Field(default=1, ge=1, le=366)
    title: str | None = Field(default=None, max_length=150)
    distance_km: float | None = Field(default=None, ge=0, le=100000)
    elevation_gain_m: float | None = Field(default=None, ge=0, le=100000)
    estimated_km: float | None = Field(default=None, ge=0, le=100000)
    estimated_elevation_m: float | None = Field(default=None, ge=0, le=100000)
    ride_id: int | None = Field(default=None, gt=0)
    poi_id: int | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=2000)


class StageResponse(StageCreate):
    """Schema di risposta per una tappa (include id e metadata)."""

    id: int | None = None
    created_at: str | None = None


# ---------------------------------------------------------------------------
# Proactive Assistant — notifications, context, scoring
# ---------------------------------------------------------------------------


class NotificationPreferences(BaseModel):
    """Athlete-controlled notification preferences (Proactive Assistant)."""

    language: str = Field(default="it", pattern="^(it|en)$")
    quiet_hours_start: int = Field(default=23, ge=0, le=23)
    quiet_hours_end: int = Field(default=7, ge=0, le=23)
    max_background_per_ride: int = Field(default=2, ge=1, le=10)
    allow_voice_coach: bool = True
    allow_email_summary: bool = True
    paused: bool = False
    # Preferred delivery channel order, most preferred first.
    channel_priority: list[str] = Field(
        default_factory=lambda: ["app", "voice", "dashboard", "email"]
    )
    respect_quiet_hours: bool = True

    @field_validator("channel_priority")
    @classmethod
    def validate_channels(cls, v: list[str]) -> list[str]:
        """Filtra i canali di notifica mantenendo solo quelli consentiti."""
        allowed = {"app", "voice", "dashboard", "email"}
        cleaned = [c for c in v if c in allowed]
        if not cleaned:
            return ["app", "voice", "dashboard", "email"]
        return cleaned


class NotificationContextIn(BaseModel):
    """Context used to evaluate whether a notification is worth sending."""

    athlete_state: dict = Field(default_factory=dict)
    plan: dict | None = None
    current_ride: dict | None = None
    weather: dict | None = None
    now: str | None = Field(default=None, description="ISO datetime, defaults to now")
    intensity_zone: int | None = Field(
        default=None, ge=0, le=5, description="Current training zone 0-5"
    )


class NotificationScoreOut(BaseModel):
    """Schema di risposta per scoring notifica (urgenza, rilevanza, tempestivita')."""

    urgency: int = Field(..., ge=1, le=5)
    relevance: int = Field(..., ge=1, le=5)
    timeliness: int = Field(..., ge=1, le=5)
    score: float = Field(..., ge=0, le=5)
    should_notify: bool
    reasons: list[str] = Field(default_factory=list)


class NotificationOut(BaseModel):
    """Schema di risposta per una notifica generata."""

    id: str
    category: str
    channel: str
    title: str
    message: str
    tts_text: str | None = None
    score: float
    priority: int = Field(default=5, ge=1, le=5)
    language: str = "it"
    created_at: str | None = None


class NotificationListOut(BaseModel):
    """Schema di risposta per lista notifiche con metadata."""

    notifications: list[NotificationOut]
    meta: dict = Field(default_factory=dict)


class MetabolicProfileCreate(BaseModel):
    """Schema di richiesta per creare/aggiornare il profilo metabolico."""
    sex: str = Field(default="male", pattern="^(male|female)$")
    bmr_formula: str = Field(default="mifflin", pattern="^(mifflin|cunningham)$")
    activity_level: str = Field(default="moderate", pattern="^(sedentary|light|moderate|active|very_active)$")
    bmr_kcal: float | None = Field(default=None, ge=500, le=5000)
    tdee_kcal: float | None = Field(default=None, ge=500, le=10000)
    notes: str | None = Field(default=None, max_length=500)


class MetabolicProfileResponse(MetabolicProfileCreate):
    """Schema di risposta per il profilo metabolico."""
    athlete_id: int
    created_at: str | None = None
    updated_at: str | None = None


class FoodLogCreate(BaseModel):
    """Schema di richiesta per creare un log alimentare."""
    date: str = Field(..., min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    meal_type: str = Field(default="other", pattern="^(breakfast|lunch|dinner|snack|other)$")
    description: str = Field(..., min_length=1, max_length=500)
    kcal: float = Field(default=0, ge=0, le=50000)
    carbs_g: float | None = Field(default=None, ge=0, le=2000)
    protein_g: float | None = Field(default=None, ge=0, le=1000)
    fat_g: float | None = Field(default=None, ge=0, le=1000)
    fiber_g: float | None = Field(default=None, ge=0, le=500)
    water_ml: float | None = Field(default=None, ge=0, le=10000)
    note: str | None = Field(default=None, max_length=500)
    recorded_at: str | None = Field(default=None, description="ISO datetime")


class FoodLogUpdate(BaseModel):
    """Schema di richiesta per aggiornare un log alimentare."""
    date: str | None = Field(default=None, min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    meal_type: str | None = Field(default=None, pattern="^(breakfast|lunch|dinner|snack|other)$")
    description: str | None = Field(default=None, min_length=1, max_length=500)
    kcal: float | None = Field(default=None, ge=0, le=50000)
    carbs_g: float | None = Field(default=None, ge=0, le=2000)
    protein_g: float | None = Field(default=None, ge=0, le=1000)
    fat_g: float | None = Field(default=None, ge=0, le=1000)
    fiber_g: float | None = Field(default=None, ge=0, le=500)
    water_ml: float | None = Field(default=None, ge=0, le=10000)
    note: str | None = Field(default=None, max_length=500)
    recorded_at: str | None = Field(default=None, description="ISO datetime")


class FoodLogResponse(FoodLogCreate):
    """Schema di risposta per un log alimentare."""
    id: int | None = None
    athlete_id: int
    tenant_id: int = 0
    created_at: str | None = None


class MetabolicDailySummaryResponse(BaseModel):
    """Schema di risposta per il riepilogo metabolico giornaliero."""
    id: int | None = None
    athlete_id: int
    tenant_id: int = 0
    date: str
    bmr_kcal: float = 0.0
    neat_kcal: float = 0.0
    eat_kcal: float = 0.0
    climb_bonus_kcal: float = 0.0
    tdee_kcal: float = 0.0
    intake_kcal: float = 0.0
    balance_kcal: float = 0.0
    steps_estimated: int | None = None
    elevation_gain_estimated_m: float | None = None
    rides_count: int = 0
    gps_neat_kcal: float = 0.0
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class MetabolicReferenceValueCreate(BaseModel):
    """Import a known average (mean) metabolic value for a demographic bracket."""

    sex: str = Field(default="male", pattern="^(male|female)$")
    age_bracket_lo: int = Field(..., ge=0, le=130)
    age_bracket_hi: int = Field(..., ge=0, le=130)
    weight_bracket_lo: int = Field(..., ge=20, le=300)
    weight_bracket_hi: int = Field(..., ge=20, le=300)
    bmr_kcal: float | None = Field(default=None, ge=500, le=5000)
    tdee_kcal: float | None = Field(default=None, ge=500, le=10000)
    activity_level: str = Field(default="moderate", pattern="^(sedentary|light|moderate|active|very_active)$")
    source: str = Field(default="import", max_length=50)


class MetabolicReferenceImportRequest(BaseModel):
    """Batch import of reference values (mean values per bracket)."""

    values: list[MetabolicReferenceValueCreate] = Field(default_factory=list, max_length=2000)


class MetabolicCalibrationRequest(BaseModel):
    """Ingest sensor-derived values to calibrate per-athlete weights."""

    sensor_bmr_kcal: float | None = Field(default=None, ge=500, le=5000)
    sensor_tdee_kcal: float | None = Field(default=None, ge=500, le=10000)
    date: str | None = Field(default=None, min_length=10, max_length=10, pattern="^\\d{4}-\\d{2}-\\d{2}$")


class MetabolicWeightsResponse(BaseModel):
    """Per-athlete adaptive weights and sensor confidence."""

    athlete_id: int
    activity_multiplier_w: float = 1.0
    neat_w: float = 1.0
    climb_bonus_w: float = 1.0
    sensor_bmr_conf: float = 1.0
    sensor_tdee_conf: float = 1.0
    learning_rate: float = 0.1
    confidence_lr: float = 0.05
    n_updates: int = 0
    updated_at: str | None = None


class MetabolicCalibrationResponse(BaseModel):
    """Result of a calibration step."""

    athlete_id: int
    reference: dict
    sensor: dict
    weights: MetabolicWeightsResponse


class NutritionFoodItem(BaseModel):
    """Schema for a nutrition database food item."""

    id: int | None = None
    tenant_id: int = 0
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(default="other", max_length=50)
    kcal_per_100g: float = Field(..., ge=0, le=5000)
    carbs_g_per_100g: float = Field(default=0, ge=0, le=500)
    protein_g_per_100g: float = Field(default=0, ge=0, le=500)
    fat_g_per_100g: float = Field(default=0, ge=0, le=500)
    fiber_g_per_100g: float = Field(default=0, ge=0, le=100)
    source: str = Field(default="builtin", max_length=50)
    is_builtin: bool = False
    created_at: str | None = None
    updated_at: str | None = None


class NutritionFoodItemCreate(BaseModel):
    """Schema for creating a new food item."""

    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(default="other", max_length=50)
    kcal_per_100g: float = Field(..., ge=0, le=5000)
    carbs_g_per_100g: float = Field(default=0, ge=0, le=500)
    protein_g_per_100g: float = Field(default=0, ge=0, le=500)
    fat_g_per_100g: float = Field(default=0, ge=0, le=500)
    fiber_g_per_100g: float = Field(default=0, ge=0, le=100)


class NutritionFoodItemUpdate(BaseModel):
    """Schema for updating a food item (user-added only)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=50)
    kcal_per_100g: float | None = Field(default=None, ge=0, le=5000)
    carbs_g_per_100g: float | None = Field(default=None, ge=0, le=500)
    protein_g_per_100g: float | None = Field(default=None, ge=0, le=500)
    fat_g_per_100g: float | None = Field(default=None, ge=0, le=500)
    fiber_g_per_100g: float | None = Field(default=None, ge=0, le=100)


class NutritionSearchRequest(BaseModel):
    """Schema for searching food items."""

    query: str = Field(..., min_length=1, max_length=100)
    category: str | None = Field(default=None, max_length=50)
    limit: int = Field(default=50, ge=1, le=200)


BeckAnswer = tuple[int, int]
BeckSubmission = list[BeckAnswer]
BeckCategory = str
BECK_ITEMS = 21


def _validate_beck_answer(value: int) -> int:
    if not 0 <= value <= 3:
        raise ValueError("BDI item score must be between 0 and 3")
    return value


class BeckAssessmentResponse(BaseModel):
    """Schema di risposta per un assessment Beck completato."""

    id: int | None = None
    athlete_id: int
    tenant_id: int = 0
    total_score: int = Field(..., ge=0, le=63)
    severity: BeckCategory = Field(default="minimal")
    answers: list[BeckAnswer] = Field(default_factory=list, max_length=BECK_ITEMS)
    notes: str | None = Field(default=None, max_length=2000)
    created_at: str | None = None
    updated_at: str | None = None


class BeckAssessmentCreate(BaseModel):
    """Schema di richiesta per creare/salvare un assessment Beck."""

    answers: list[BeckAnswer] = Field(..., min_length=BECK_ITEMS, max_length=BECK_ITEMS)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, value: list[BeckAnswer]) -> list[BeckAnswer]:
        if len(value) != BECK_ITEMS:
            raise ValueError(f"BDI requires exactly {BECK_ITEMS} item answers")
        return [_validate_beck_answer(int(score)) for _, score in value]


class BeckHistoryResponse(BaseModel):
    """Schema di risposta per lo storico assessment Beck."""

    items: list[BeckAssessmentResponse] = Field(default_factory=list)
    latest: BeckAssessmentResponse | None = None
    trend: list[dict] = Field(default_factory=list)


class UserOAuthCredentials(BaseModel):
    """Schema per le credenziali OAuth personalizzate dell'utente."""

    provider: str = Field(..., pattern="^(strava|wahoo|garmin|google_fit|google_health)$")
    client_id: str | None = Field(default=None, max_length=255)
    client_secret: str | None = Field(default=None, max_length=255)
    redirect_uri: str | None = Field(default=None, max_length=500)
    scope: str | None = Field(default=None, max_length=500)


class UserOAuthCredentialsOut(BaseModel):
    """Schema di risposta per le credenziali OAuth (senza segreti)."""

    id: int
    provider: str
    client_id: str | None
    redirect_uri: str | None
    scope: str | None
    has_secret: bool
    created_at: str | None
    updated_at: str | None
