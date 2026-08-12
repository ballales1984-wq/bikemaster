"""SQLAlchemy ORM models for the async DB layer (SQLite primary / optional PostgreSQL cloud sync).

Mirrors the schema created by ``db/database.py`` (the synchronous SQLite layer)
so the async code paths can run against the local SQLite store or an optional
cloud PostgreSQL (sync). The sync layer remains the source of truth for the
SQLite schema; this module only defines the ORM mappings used by the async
session (cloud sync / community features).
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

try:  # pragma: no cover - pgvector is optional at import time
    from pgvector.sqlalchemy import Vector

    _HAS_PGVECTOR = True
except Exception:  # noqa: BLE001
    Vector = None  # type: ignore[assignment]
    _HAS_PGVECTOR = False


# all-MiniLM-L6-v2 produces 384-dimensional embeddings.
EMBEDDING_DIMENSION = 384


class Base(DeclarativeBase):
    pass


class ActivityType(enum.StrEnum):
    RIDE = "ride"
    WALK = "walk"
    HIKE = "hike"
    RUN = "run"
    SWIM = "swim"
    INDOOR = "indoor"
    OTHER = "other"


class EventType(enum.StrEnum):
    TRAINING = "training"
    RACE = "race"
    RECOVERY = "recovery"
    OTHER = "other"


class WorkoutType(enum.StrEnum):
    ENDURANCE = "endurance"
    INTERVAL = "interval"
    THRESHOLD = "threshold"
    VO2MAX = "vo2max"
    RECOVERY = "recovery"
    STRENGTH = "strength"
    FARTLEK = "fartlek"
    TEMPO = "tempo"
    OTHER = "other"


class GoalType(enum.StrEnum):
    GRANFONDO = "granfondo"
    MARATHON = "marathon"
    CENTURY = "century"
    WEIGHT_LOSS = "weight_loss"
    FTP_IMPROVEMENT = "ftp_improvement"
    GENERAL_FITNESS = "general_fitness"
    RACE = "race"
    OTHER = "other"


class SyncStatus(enum.StrEnum):
    LOCAL = "local"
    PENDING = "pending"
    SYNCED = "synced"
    CONFLICT = "conflict"
    ERROR = "error"


class ConflictResolution(enum.StrEnum):
    LOCAL_WINS = "local"
    REMOTE_WINS = "remote"
    UNRESOLVED = "unresolved"


class IncidentSeverity(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class POIType(enum.StrEnum):
    VIEWPOINT = "viewpoint"
    FOUNTAIN = "fountain"
    REFUGE = "refuge"
    JUNCTION = "junction"
    DANGER = "danger"
    CULTURAL = "cultural"
    TECHNICAL = "technical"
    PARKING = "parking"
    OTHER = "other"


class RiskLabel(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    email: Mapped[str | None] = mapped_column(String, unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_client: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    athletes: Mapped[list[AthleteModel]] = relationship(back_populates="user", cascade="all, delete-orphan")
    oauth_identities: Mapped[list[ExternalIdentityModel]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    external_tokens: Mapped[list[ExternalTokenModel]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    totp_secrets: Mapped[list[TOTPSecretModel]] = relationship(back_populates="user", cascade="all, delete-orphan")
    oauth_credentials: Mapped[list[UserOAuthCredentials]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_users_username", "username"),
        Index("ix_users_email", "email"),
        Index("ix_users_is_active", "is_active"),
    )


class AthleteModel(Base):
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String)
    picture: Mapped[str | None] = mapped_column(String)
    age: Mapped[int] = mapped_column(Integer, default=30)
    weight_kg: Mapped[float] = mapped_column(Float, default=70.0)
    height_cm: Mapped[float | None] = mapped_column(Float)
    fat_percentage: Mapped[float | None] = mapped_column(Float)
    years_active: Mapped[int] = mapped_column(Integer, default=1)
    weekly_sessions: Mapped[int] = mapped_column(Integer, default=3)
    monthly_hours: Mapped[float] = mapped_column(Float, default=0.0)
    annual_hours: Mapped[float] = mapped_column(Float, default=0.0)
    experience_level: Mapped[str] = mapped_column(String, default="Beginner")
    goals: Mapped[str | None] = mapped_column(Text)
    preferred_terrain: Mapped[str | None] = mapped_column(Text)
    weekly_volume_km: Mapped[float] = mapped_column(Float, default=0.0)
    best_segments: Mapped[str | None] = mapped_column(Text)
    medical_notes: Mapped[str | None] = mapped_column(Text)
    equipment: Mapped[str | None] = mapped_column(Text)
    ftp_watts: Mapped[float | None] = mapped_column(Float)
    body_water_percentage: Mapped[float | None] = mapped_column(Float)
    muscle_mass_percentage: Mapped[float | None] = mapped_column(Float)
    bmr_kcal: Mapped[float | None] = mapped_column(Float)
    fat_mass_kg: Mapped[float | None] = mapped_column(Float)
    subcutaneous_fat_kg: Mapped[float | None] = mapped_column(Float)
    subcutaneous_fat_percentage: Mapped[float | None] = mapped_column(Float)
    visceral_fat_level: Mapped[float | None] = mapped_column(Float)
    visceral_fat_percentage: Mapped[float | None] = mapped_column(Float)
    visceral_fat_kg: Mapped[float | None] = mapped_column(Float)
    muscle_mass_kg: Mapped[float | None] = mapped_column(Float)
    bone_mass_kg: Mapped[float | None] = mapped_column(Float)
    protein_percentage: Mapped[float | None] = mapped_column(Float)
    protein_kg: Mapped[float | None] = mapped_column(Float)
    body_age: Mapped[int | None] = mapped_column(Integer)
    apparent_age: Mapped[int | None] = mapped_column(Integer)
    bmi: Mapped[float | None] = mapped_column(Float)
    lean_body_mass_kg: Mapped[float | None] = mapped_column(Float)
    password_hash: Mapped[str | None] = mapped_column(Text)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserModel | None] = relationship(back_populates="athletes")
    rides: Mapped[list[RideModel]] = relationship(back_populates="athlete", cascade="all, delete-orphan")
    chat_history: Mapped[list[ChatHistoryModel]] = relationship(back_populates="athlete", cascade="all, delete-orphan")
    calendar_events: Mapped[list[CalendarEventModel]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    training_stress_days: Mapped[list[TrainingStressDayModel]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    fitness_states: Mapped[list[FitnessStateModel]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    training_goals: Mapped[list[TrainingGoalModel]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    planned_workouts: Mapped[list[PlannedWorkoutModel]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    metrics: Mapped[list[MetricModel]] = relationship(back_populates="athlete", cascade="all, delete-orphan")
    route_safety_scores: Mapped[list[RouteSafetyScore]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    pois: Mapped[list[POIModel]] = relationship(back_populates="created_by_athlete", cascade="all, delete-orphan")
    itineraries: Mapped[list[ItineraryModel]] = relationship(back_populates="athlete", cascade="all, delete-orphan")
    external_identities: Mapped[list[ExternalIdentityModel]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    external_tokens: Mapped[list[ExternalTokenModel]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    metric_logs: Mapped[list[AthleteMetricLogModel]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    metabolic_profile: Mapped[MetabolicProfileModel | None] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    food_logs: Mapped[list[FoodLogModel]] = relationship(back_populates="athlete", cascade="all, delete-orphan")
    metabolic_daily_summaries: Mapped[list[MetabolicDailySummaryModel]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    beck_assessments: Mapped[list[BeckAssessmentModel]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_athletes_tenant", "tenant_id"),
        Index("ix_athletes_name", "name"),
        Index("ix_athletes_experience_level", "experience_level"),
        Index("ix_athletes_email", "email"),
        Index("ix_athletes_user_id", "user_id"),
    )


class AthleteMetricLogModel(Base):
    """Serie storica dei valori dell'atleta (peso, % grassa, FTP, umore, sonno).

    Ogni modifica manuale (o import da bilancia) di una metrica tracciata
    registra una riga con il valore e il timestamp dell'evento, cosi' e'
    possibile disegnare grafici di andamento temporale. Una sola tabella
    polivalente indicizzata per (athlete_id, metric_type, recorded_at).
    """

    __tablename__ = "athlete_metric_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    metric_type: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String, default="manual")
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    athlete: Mapped[AthleteModel | None] = relationship(back_populates="metric_logs")

    __table_args__ = (
        Index("ix_metric_log_athlete_metric", "athlete_id", "metric_type"),
        Index("ix_metric_log_recorded", "athlete_id", "metric_type", "recorded_at"),
        Index("ix_metric_log_tenant", "tenant_id"),
    )


class AthleteHistoryModel(Base):
    """Snapshots completi del profilo atleta ad ogni modifica.

    Ogni UPDATE del profilo atleta salva un'immagine completa dello stato
    precedente con il timestamp dell'evento. Questo permette di ricostruire
    l'evoluzione temporale di qualsiasi campo del profilo.
    La password_hash e' esclusa per sicurezza.
    """

    __tablename__ = "athlete_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    changed_by: Mapped[int | None] = mapped_column(Integer)
    name: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    picture: Mapped[str | None] = mapped_column(String)
    age: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    height_cm: Mapped[float | None] = mapped_column(Float)
    fat_percentage: Mapped[float | None] = mapped_column(Float)
    years_active: Mapped[int | None] = mapped_column(Integer)
    weekly_sessions: Mapped[int | None] = mapped_column(Integer)
    monthly_hours: Mapped[float | None] = mapped_column(Float)
    annual_hours: Mapped[float | None] = mapped_column(Float)
    experience_level: Mapped[str | None] = mapped_column(String)
    goals: Mapped[str | None] = mapped_column(Text)
    preferred_terrain: Mapped[str | None] = mapped_column(Text)
    weekly_volume_km: Mapped[float | None] = mapped_column(Float)
    best_segments: Mapped[str | None] = mapped_column(Text)
    medical_notes: Mapped[str | None] = mapped_column(Text)
    equipment: Mapped[str | None] = mapped_column(Text)
    ftp_watts: Mapped[float | None] = mapped_column(Float)
    body_water_percentage: Mapped[float | None] = mapped_column(Float)
    muscle_mass_percentage: Mapped[float | None] = mapped_column(Float)
    bmr_kcal: Mapped[float | None] = mapped_column(Float)
    fat_mass_kg: Mapped[float | None] = mapped_column(Float)
    subcutaneous_fat_kg: Mapped[float | None] = mapped_column(Float)
    subcutaneous_fat_percentage: Mapped[float | None] = mapped_column(Float)
    visceral_fat_level: Mapped[float | None] = mapped_column(Float)
    visceral_fat_percentage: Mapped[float | None] = mapped_column(Float)
    visceral_fat_kg: Mapped[float | None] = mapped_column(Float)
    muscle_mass_kg: Mapped[float | None] = mapped_column(Float)
    bone_mass_kg: Mapped[float | None] = mapped_column(Float)
    protein_percentage: Mapped[float | None] = mapped_column(Float)
    protein_kg: Mapped[float | None] = mapped_column(Float)
    body_age: Mapped[int | None] = mapped_column(Integer)
    apparent_age: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        Index("ix_history_athlete_recorded", "athlete_id", "recorded_at"),
        Index("ix_history_tenant", "tenant_id"),
    )


class RideModel(Base):
    __tablename__ = "rides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    date: Mapped[str] = mapped_column(String, nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, default=0.0)
    duration_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    avg_speed_kmh: Mapped[float] = mapped_column(Float, default=0.0)
    weight_kg: Mapped[float] = mapped_column(Float, default=70.0)
    calories: Mapped[float] = mapped_column(Float, default=0.0)
    heart_rate_avg: Mapped[float | None] = mapped_column(Float)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float)
    gps_points: Mapped[str | None] = mapped_column(Text)
    external_source: Mapped[str | None] = mapped_column(String)
    external_id: Mapped[str | None] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String)
    activity_type: Mapped[ActivityType] = mapped_column(Enum(ActivityType), default=ActivityType.RIDE)
    is_official: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String, default="manual")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    athlete: Mapped[AthleteModel | None] = relationship(back_populates="rides")
    metrics: Mapped[list[MetricModel]] = relationship(back_populates="ride", cascade="all, delete-orphan")
    route_safety_scores: Mapped[list[RouteSafetyScore]] = relationship(
        back_populates="ride", cascade="all, delete-orphan"
    )
    stages: Mapped[list[StageModel]] = relationship(back_populates="ride", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("external_source", "external_id", name="uq_rides_external_identity"),
        Index("ix_rides_athlete_id", "athlete_id"),
        Index("ix_rides_date", "date"),
        Index("ix_rides_tenant", "tenant_id"),
    )


class FitnessStateModel(Base):
    __tablename__ = "fitness_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    date: Mapped[str] = mapped_column(String, nullable=False)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fitness: Mapped[float] = mapped_column(Float, default=0.0)
    fatigue: Mapped[float] = mapped_column(Float, default=0.0)
    form: Mapped[float] = mapped_column(Float, default=0.0)
    atl: Mapped[float] = mapped_column(Float, default=0.0)
    ctl: Mapped[float] = mapped_column(Float, default=0.0)
    tsb: Mapped[float] = mapped_column(Float, default=0.0)
    recovery_hours_needed: Mapped[float] = mapped_column(Float, default=0.0)
    weekly_tss: Mapped[float] = mapped_column(Float, default=0.0)
    monthly_tss: Mapped[float] = mapped_column(Float, default=0.0)
    trend_7d: Mapped[str] = mapped_column(String, default="stable")
    trend_30d: Mapped[str] = mapped_column(String, default="stable")
    risk_indicators: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)

    athlete: Mapped[AthleteModel | None] = relationship(back_populates="fitness_states")


class TrainingStressDayModel(Base):
    __tablename__ = "training_stress_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"))
    date: Mapped[str] = mapped_column(String, nullable=False)
    tss: Mapped[float | None] = mapped_column(Float)
    atl: Mapped[float | None] = mapped_column(Float)
    ctl: Mapped[float | None] = mapped_column(Float)
    tsb: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)

    athlete: Mapped[AthleteModel] = relationship(back_populates="training_stress_days")

    __table_args__ = (
        UniqueConstraint("athlete_id", "date", name="uq_training_stress_days"),
        Index("ix_training_stress_days_athlete", "athlete_id"),
        Index("ix_training_stress_days_date", "date"),
        Index("ix_training_stress_days_tenant", "tenant_id"),
    )


class MetricModel(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"))
    ride_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("rides.id", ondelete="CASCADE"), unique=True)
    fatigue_score: Mapped[float | None] = mapped_column(Float)
    recovery_hours: Mapped[float | None] = mapped_column(Float)
    calories_per_km: Mapped[float | None] = mapped_column(Float)
    efficiency_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)

    athlete: Mapped[AthleteModel | None] = relationship(back_populates="metrics")
    ride: Mapped[RideModel | None] = relationship(back_populates="metrics")

    __table_args__ = (
        Index("ix_metrics_ride_id", "ride_id"),
        Index("ix_metrics_athlete_id", "athlete_id"),
        Index("ix_metrics_tenant", "tenant_id"),
    )


class ChatHistoryModel(Base):
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    athlete: Mapped[AthleteModel | None] = relationship(back_populates="chat_history")


class CalendarEventModel(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), default=EventType.TRAINING)
    date: Mapped[str] = mapped_column(String, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    weather_temp: Mapped[float | None] = mapped_column(Float)
    weather_humidity: Mapped[float | None] = mapped_column(Float)
    weather_description: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    athlete: Mapped[AthleteModel | None] = relationship(back_populates="calendar_events")

    __table_args__ = (
        Index("ix_calendar_events_athlete_id", "athlete_id"),
        Index("ix_calendar_events_date", "date"),
        Index("ix_calendar_events_tenant", "tenant_id"),
        Index("ix_calendar_events_athlete_date", "athlete_id", "date"),
    )


class WeatherCache(Base):
    __tablename__ = "weather_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    date: Mapped[str] = mapped_column(String, nullable=False)
    temperature: Mapped[float | None] = mapped_column(Float)
    humidity: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(String)
    cached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("lat", "lon", "date", name="uq_weather_cache"),)


class TrainingGoalModel(Base):
    __tablename__ = "training_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    goal_type: Mapped[GoalType] = mapped_column(Enum(GoalType), default=GoalType.GRANFONDO)
    target_date: Mapped[str | None] = mapped_column(String)
    target_distance_km: Mapped[float | None] = mapped_column(Float)
    target_elevation_m: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    athlete: Mapped[AthleteModel] = relationship(back_populates="training_goals")
    planned_workouts: Mapped[list[PlannedWorkoutModel]] = relationship(
        back_populates="goal", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_training_goals_athlete", "athlete_id"),
        Index("ix_training_goals_tenant", "tenant_id"),
        Index("ix_training_goals_status", "status"),
    )


class PlannedWorkoutModel(Base):
    __tablename__ = "planned_workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    goal_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("training_goals.id", ondelete="SET NULL"))
    date: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    workout_type: Mapped[WorkoutType] = mapped_column(Enum(WorkoutType), default=WorkoutType.ENDURANCE)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    target_intensity: Mapped[float] = mapped_column(Float, default=0.5)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[str | None] = mapped_column(String)

    athlete: Mapped[AthleteModel] = relationship(back_populates="planned_workouts")
    goal: Mapped[TrainingGoalModel | None] = relationship(back_populates="planned_workouts")

    __table_args__ = (
        Index("ix_planned_workouts_athlete", "athlete_id"),
        Index("ix_planned_workouts_goal", "goal_id"),
        Index("ix_planned_workouts_date", "date"),
        Index("ix_planned_workouts_tenant", "tenant_id"),
        Index("ix_planned_workouts_completed", "completed"),
    )


class RoadIncident(Base):
    __tablename__ = "road_incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    incident_date: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[IncidentSeverity] = mapped_column(Enum(IncidentSeverity), default=IncidentSeverity.MEDIUM)
    description: Mapped[str | None] = mapped_column(Text)
    road_type: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String, default="local")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("source_id", "source", name="uq_road_incidents"),
        Index("ix_road_incidents_coords", "lat", "lon"),
        Index("ix_road_incidents_source", "source"),
        Index("ix_road_incidents_severity", "severity"),
    )


class RouteSafetyScore(Base):
    __tablename__ = "route_safety_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ride_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("rides.id", ondelete="CASCADE"))
    athlete_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"))
    risk_score: Mapped[float | None] = mapped_column(Float)
    label: Mapped[RiskLabel | None] = mapped_column(Enum(RiskLabel))
    advice: Mapped[str | None] = mapped_column(Text)
    road_type_counts: Mapped[str | None] = mapped_column(Text)
    has_bike_infrastructure: Mapped[bool | None] = mapped_column(Boolean)
    incident_count: Mapped[int | None] = mapped_column(Integer)
    route_length_km: Mapped[float | None] = mapped_column(Float)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)

    ride: Mapped[RideModel | None] = relationship(back_populates="route_safety_scores")
    athlete: Mapped[AthleteModel | None] = relationship(back_populates="route_safety_scores")

    __table_args__ = (
        Index("ix_route_safety_scores_ride", "ride_id"),
        Index("ix_route_safety_scores_athlete", "athlete_id"),
        Index("ix_route_safety_scores_tenant", "tenant_id"),
    )


class POIModel(Base):
    """Point of Interest (vista, fontana, ristoro, bivio, pericolo, culturale, tecnico)."""

    __tablename__ = "pois"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False, default=POIType.OTHER.value)
    photos: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(String)
    difficulty_note: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(Text)
    itinerary_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("itineraries.id", ondelete="SET NULL"))
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="SET NULL"))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_by_athlete: Mapped[AthleteModel | None] = relationship(back_populates="pois")
    itinerary: Mapped[ItineraryModel | None] = relationship(back_populates="pois")
    stages: Mapped[list[StageModel]] = relationship(back_populates="poi", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_pois_coords", "lat", "lon"),
        Index("ix_pois_type", "type"),
        Index("ix_pois_tenant", "tenant_id"),
    )


class ItineraryModel(Base):
    """Multi-day tour itinerary composed of stages."""

    __tablename__ = "itineraries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[str | None] = mapped_column(String)
    end_date: Mapped[str | None] = mapped_column(String)
    total_km: Mapped[float] = mapped_column(Float, default=0.0)
    total_elevation_m: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    athlete: Mapped[AthleteModel | None] = relationship(back_populates="itineraries")
    stages: Mapped[list[StageModel]] = relationship(back_populates="itinerary", cascade="all, delete-orphan")
    pois: Mapped[list[POIModel]] = relationship(back_populates="itinerary")

    __table_args__ = (
        Index("ix_itineraries_athlete", "athlete_id"),
        Index("ix_itineraries_tenant", "tenant_id"),
    )


class StageModel(Base):
    """A single day/stage within an itinerary."""

    __tablename__ = "stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    itinerary_id: Mapped[int] = mapped_column(Integer, ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False)
    stage_day: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    distance_km: Mapped[float | None] = mapped_column(Float)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float)
    estimated_km: Mapped[float | None] = mapped_column(Float)
    estimated_elevation_m: Mapped[float | None] = mapped_column(Float)
    ride_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("rides.id", ondelete="SET NULL"))
    poi_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("pois.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(Text)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    itinerary: Mapped[ItineraryModel] = relationship(back_populates="stages")
    ride: Mapped[RideModel | None] = relationship(back_populates="stages")
    poi: Mapped[POIModel | None] = relationship(back_populates="stages")

    __table_args__ = (
        Index("ix_stages_itinerary", "itinerary_id"),
        Index("ix_stages_ride", "ride_id"),
        Index("ix_stages_poi", "poi_id"),
        Index("ix_stages_tenant", "tenant_id"),
    )


class StravaToken(Base):
    __tablename__ = "strava_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), unique=True)
    access_token: Mapped[str] = mapped_column(String(1024), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(1024), nullable=False)
    expires_at: Mapped[int | None] = mapped_column(Integer)
    scope: Mapped[str | None] = mapped_column(String(200))
    athlete_name: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)


class GarminToken(Base):
    __tablename__ = "garmin_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), unique=True)
    access_token: Mapped[str] = mapped_column(String(1024), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(1024), nullable=False)
    expires_at: Mapped[int | None] = mapped_column(Integer)
    scope: Mapped[str | None] = mapped_column(String(200))
    athlete_name: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)


class SyncEntityState(Base):
    __tablename__ = "sync_entity_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String, default="device")
    reliability_score: Mapped[float] = mapped_column(Float, default=1.0)
    last_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    sync_status: Mapped[str] = mapped_column(String, default="local")
    sync_error: Mapped[str | None] = mapped_column(Text)
    cloud_id: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("entity_type", "entity_id", name="uq_sync_entity_state"),)


class SyncSetting(Base):
    __tablename__ = "sync_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SyncConflict(Base):
    __tablename__ = "sync_conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    local_data: Mapped[str] = mapped_column(Text, nullable=False)
    remote_data: Mapped[str] = mapped_column(Text, nullable=False)
    local_reliability: Mapped[float] = mapped_column(Float, nullable=False)
    remote_reliability: Mapped[float] = mapped_column(Float, nullable=False)
    local_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    remote_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    resolution: Mapped[str] = mapped_column(String, default="unresolved")
    resolved_data: Mapped[str | None] = mapped_column(Text)
    resolution_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class KnowledgeChunkModel(Base):
    """Knowledge base chunk for PGVector similarity search (optional)."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String, default="")
    chunk_id: Mapped[str] = mapped_column(String, default="")
    text: Mapped[str] = mapped_column(Text, default="")
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    section: Mapped[str | None] = mapped_column(String)
    embedding: Mapped[Any] = mapped_column(Vector(EMBEDDING_DIMENSION) if _HAS_PGVECTOR else Text)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String, nullable=False)
    resource: Mapped[str] = mapped_column(String, nullable=False)
    resource_id: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[str] = mapped_column(Text, default="{}")
    ip_address: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), index=True)
    refresh_token: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    jti: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SegmentModel(Base):
    """Named segment within a ride (e.g., climb, sprint)."""

    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ride_id: Mapped[int] = mapped_column(Integer, ForeignKey("rides.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    start_index: Mapped[int] = mapped_column(Integer, nullable=False)
    end_index: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_m: Mapped[float | None] = mapped_column(Float)
    avg_speed_kmh: Mapped[float | None] = mapped_column(Float)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (Index("ix_segments_ride_id", "ride_id"),)


class PauseModel(Base):
    """Pause/stop within a ride."""

    __tablename__ = "pauses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ride_id: Mapped[int] = mapped_column(Integer, ForeignKey("rides.id", ondelete="CASCADE"), nullable=False)
    start_index: Mapped[int] = mapped_column(Integer, nullable=False)
    end_index: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (Index("ix_pauses_ride_id", "ride_id"),)


class ExternalIdentityModel(Base):
    """Maps an external OAuth identity (Google sub, Strava athlete_id, etc.) to a local user/athlete."""

    __tablename__ = "external_identities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    athlete_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    external_email: Mapped[str | None] = mapped_column(String)
    display_name: Mapped[str | None] = mapped_column(String)
    picture_url: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserModel | None] = relationship(back_populates="oauth_identities")
    athlete: Mapped[AthleteModel | None] = relationship(back_populates="external_identities")

    __table_args__ = (
        UniqueConstraint("provider", "external_id", name="uq_external_identity"),
        Index("ix_external_identity_provider", "provider"),
        Index("ix_external_identity_external_id", "external_id"),
        Index("ix_external_identity_athlete", "athlete_id"),
    )


class ExternalTokenModel(Base):
    """Encrypted/obfuscated OAuth tokens for external providers."""

    __tablename__ = "external_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    athlete_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String, nullable=False)
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scope: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserModel | None] = relationship(back_populates="external_tokens")
    athlete: Mapped[AthleteModel | None] = relationship(back_populates="external_tokens")

    __table_args__ = (
        UniqueConstraint("athlete_id", "provider", name="uq_external_token_athlete_provider"),
        Index("ix_external_token_athlete", "athlete_id"),
        Index("ix_external_token_provider", "provider"),
        Index("ix_external_token_expires", "expires_at"),
    )


class TOTPSecretModel(Base):
    """TOTP 2FA secrets (stored server-side, not in JWT)."""

    __tablename__ = "totp_secrets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    secret: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserModel] = relationship(back_populates="totp_secrets")

    __table_args__ = (UniqueConstraint("user_id", name="uq_totp_user"),)


class UserOAuthCredentials(Base):
    """User-provided OAuth app credentials for external providers (Strava, Wahoo, Garmin, Google).

    Allows users to override the global app credentials with their own,
    enabling private OAuth apps where the user controls the client_id/secret.
    """

    __tablename__ = "user_oauth_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    client_id: Mapped[str | None] = mapped_column(String)
    client_secret: Mapped[str | None] = mapped_column(String)
    redirect_uri: Mapped[str | None] = mapped_column(String)
    scope: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserModel] = relationship(back_populates="oauth_credentials")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_oauth_credentials_user_provider"),
        Index("ix_user_oauth_credentials_user", "user_id"),
    )


class MetabolicProfileModel(Base):
    """Metabolic profile for BMR/TDEE calculation."""

    __tablename__ = "metabolic_profiles"

    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    sex: Mapped[str] = mapped_column(String, default="male")
    bmr_formula: Mapped[str] = mapped_column(String, default="mifflin")
    activity_level: Mapped[str] = mapped_column(String, default="moderate")
    bmr_kcal: Mapped[float | None] = mapped_column(Float)
    tdee_kcal: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    athlete: Mapped[AthleteModel | None] = relationship(back_populates="metabolic_profile")


class FoodLogModel(Base):
    """Food log entry for daily nutrition tracking."""

    __tablename__ = "food_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    date: Mapped[str] = mapped_column(String, nullable=False)
    meal_type: Mapped[str] = mapped_column(String, default="other")
    description: Mapped[str] = mapped_column(String, nullable=False)
    kcal: Mapped[float] = mapped_column(Float, default=0.0)
    carbs_g: Mapped[float | None] = mapped_column(Float)
    protein_g: Mapped[float | None] = mapped_column(Float)
    fat_g: Mapped[float | None] = mapped_column(Float)
    fiber_g: Mapped[float | None] = mapped_column(Float)
    water_ml: Mapped[float | None] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text)
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    athlete: Mapped[AthleteModel | None] = relationship(back_populates="food_logs")

    __table_args__ = (Index("ix_food_logs_athlete_date", "athlete_id", "date"),)


class MetabolicDailySummaryModel(Base):
    """Aggregated daily metabolic and nutrition summary."""

    __tablename__ = "metabolic_daily_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    date: Mapped[str] = mapped_column(String, nullable=False)
    bmr_kcal: Mapped[float] = mapped_column(Float, default=0.0)
    neat_kcal: Mapped[float] = mapped_column(Float, default=0.0)
    eat_kcal: Mapped[float] = mapped_column(Float, default=0.0)
    climb_bonus_kcal: Mapped[float] = mapped_column(Float, default=0.0)
    tdee_kcal: Mapped[float] = mapped_column(Float, default=0.0)
    intake_kcal: Mapped[float] = mapped_column(Float, default=0.0)
    balance_kcal: Mapped[float] = mapped_column(Float, default=0.0)
    steps_estimated: Mapped[int | None] = mapped_column(Integer)
    elevation_gain_estimated_m: Mapped[float | None] = mapped_column(Float)
    rides_count: Mapped[int] = mapped_column(Integer, default=0)
    gps_neat_kcal: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    athlete: Mapped[AthleteModel | None] = relationship(back_populates="metabolic_daily_summaries")

    __table_args__ = (
        UniqueConstraint("athlete_id", "date", name="uq_metabolic_summary_athlete_date"),
        Index("ix_metabolic_summaries_athlete_date", "athlete_id", "date"),
    )


class BeckAssessmentModel(Base):
    """Beck Depression Inventory assessment for an athlete."""

    __tablename__ = "beck_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    severity: Mapped[str] = mapped_column(String, nullable=False, default="minimal")
    answers: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    athlete: Mapped[AthleteModel | None] = relationship(back_populates="beck_assessments")

    __table_args__ = (
        Index("ix_beck_assessments_athlete", "athlete_id"),
        Index("ix_beck_assessments_athlete_date", "athlete_id", "created_at"),
    )


class MetabolicReferenceValueModel(Base):
    """Imported mean metabolic value for a demographic bracket (age/sex/weight)."""

    __tablename__ = "metabolic_reference_values"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    sex: Mapped[str] = mapped_column(String, nullable=False)
    age_bracket_lo: Mapped[int] = mapped_column(Integer, nullable=False)
    age_bracket_hi: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_bracket_lo: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_bracket_hi: Mapped[int] = mapped_column(Integer, nullable=False)
    bmr_kcal: Mapped[float | None] = mapped_column(Float)
    tdee_kcal: Mapped[float | None] = mapped_column(Float)
    activity_level: Mapped[str] = mapped_column(String, default="moderate")
    source: Mapped[str] = mapped_column(String, default="import")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MetabolicAdaptiveWeightsModel(Base):
    """Per-athlete adaptive model weights and sensor confidence."""

    __tablename__ = "metabolic_adaptive_weights"

    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    activity_multiplier_w: Mapped[float] = mapped_column(Float, default=1.0)
    neat_w: Mapped[float] = mapped_column(Float, default=1.0)
    climb_bonus_w: Mapped[float] = mapped_column(Float, default=1.0)
    sensor_bmr_conf: Mapped[float] = mapped_column(Float, default=1.0)
    sensor_tdee_conf: Mapped[float] = mapped_column(Float, default=1.0)
    learning_rate: Mapped[float] = mapped_column(Float, default=0.1)
    confidence_lr: Mapped[float] = mapped_column(Float, default=0.05)
    n_updates: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    athlete: Mapped[AthleteModel | None] = relationship(back_populates="metabolic_adaptive_weights")


AthleteModel.metabolic_adaptive_weights = relationship(
    "MetabolicAdaptiveWeightsModel", back_populates="athlete", uselist=False, cascade="all, delete-orphan"
)


class AetherMapObjectModel(Base):
    __tablename__ = "aethermap_objects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tipo: Mapped[str] = mapped_column(String, nullable=False, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    alt: Mapped[float] = mapped_column(Float, server_default="0.0")
    s2: Mapped[str | None] = mapped_column(String, index=True)
    h3: Mapped[str | None] = mapped_column(String, index=True)
    cube_face: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cube_u: Mapped[float | None] = mapped_column(Float, nullable=True)
    cube_v: Mapped[float | None] = mapped_column(Float, nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=sa.text("now()"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=sa.text("now()"))


class AetherMapStateHistoryModel(Base):
    __tablename__ = "aethermap_state_history"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    object_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    campi: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    t: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, server_default="1.0")


class HR24hSampleModel(Base):
    __tablename__ = "hr_24h_samples"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hr_bpm: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String, default="manual")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HRMonitoringSettingsModel(Base):
    __tablename__ = "hr_monitoring_settings"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), unique=True)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    max_hr: Mapped[int | None] = mapped_column(Integer)
    resting_hr: Mapped[int | None] = mapped_column(Integer)
    hr_zones: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BLEDeviceModel(Base):
    __tablename__ = "ble_devices"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    device_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    device_type: Mapped[str] = mapped_column(String, default="weight_scale")
    service_uuid: Mapped[str | None] = mapped_column(String)
    characteristic_uuid: Mapped[str | None] = mapped_column(String)
    mac_address: Mapped[str | None] = mapped_column(String)
    settings: Mapped[str | None] = mapped_column(Text)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("athlete_id", "device_id", name="uq_ble_devices_athlete_device"),
        Index("ix_ble_devices_athlete_id", "athlete_id"),
    )


class ConsentModel(Base):
    __tablename__ = "user_consent"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    consent_type: Mapped[str] = mapped_column(String, nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String, default="web")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("athlete_id", "consent_type", name="uq_user_consent_athlete_type"),
    )


class LegalAcceptanceModel(Base):
    __tablename__ = "legal_acceptances"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    acceptance_type: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, default="web")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("athlete_id", "acceptance_type", "version", name="uq_legal_acceptances_athlete_type_version"),
    )


class AIAuditLogModel(Base):
    __tablename__ = "ai_audit_log"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String, nullable=False)
    response_length: Mapped[int] = mapped_column(Integer, default=0)
    tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_ai_audit_log_athlete_id", "athlete_id"),
    )


__all__ = [
    "Base",
    "EMBEDDING_DIMENSION",
    "ActivityType",
    "EventType",
    "WorkoutType",
    "GoalType",
    "SyncStatus",
    "ConflictResolution",
    "IncidentSeverity",
    "POIType",
    "RiskLabel",
    "UserModel",
    "AthleteModel",
    "RideModel",
    "SegmentModel",
    "PauseModel",
    "FitnessStateModel",
    "TrainingStressDayModel",
    "MetricModel",
    "ChatHistoryModel",
    "CalendarEventModel",
    "WeatherCache",
    "TrainingGoalModel",
    "PlannedWorkoutModel",
    "RoadIncident",
    "RouteSafetyScore",
    "POIModel",
    "StravaToken",
    "GarminToken",
    "SyncEntityState",
    "SyncSetting",
    "SyncConflict",
    "KnowledgeChunkModel",
    "AuditLog",
    "SessionModel",
    "ExternalIdentityModel",
    "ExternalTokenModel",
    "TOTPSecretModel",
    "MetabolicReferenceValueModel",
    "MetabolicAdaptiveWeightsModel",
    "ItineraryModel",
    "StageModel",
    "AetherMapObjectModel",
    "AetherMapStateHistoryModel",
    "HR24hSampleModel",
    "HRMonitoringSettingsModel",
    "BLEDeviceModel",
    "ConsentModel",
    "LegalAcceptanceModel",
    "AIAuditLogModel",
]
