"""SQLAlchemy ORM models for the async DB layer (SQLite primary / optional PostgreSQL cloud sync).

Mirrors the schema created by ``db/database.py`` (the synchronous SQLite layer)
so the async code paths can run against the local SQLite store or an optional
cloud PostgreSQL (sync). The sync layer remains the source of truth for the
SQLite schema; this module only defines the ORM mappings used by the async
session (cloud sync / community features).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

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


class AthleteModel(Base):
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
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
    password_hash: Mapped[str | None] = mapped_column(Text)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RideModel(Base):
    __tablename__ = "rides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("athletes.id", ondelete="CASCADE")
    )
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
    activity_type: Mapped[str] = mapped_column(String, default="ride")
    is_official: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String, default="manual")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint(
            "external_source", "external_id", name="uq_rides_external_identity"
        ),
    )


class FitnessStateModel(Base):
    __tablename__ = "fitness_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("athletes.id", ondelete="CASCADE")
    )
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


class TrainingStressDayModel(Base):
    __tablename__ = "training_stress_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("athletes.id", ondelete="CASCADE")
    )
    date: Mapped[str] = mapped_column(String, nullable=False)
    tss: Mapped[float | None] = mapped_column(Float)
    atl: Mapped[float | None] = mapped_column(Float)
    ctl: Mapped[float | None] = mapped_column(Float)
    tsb: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("athlete_id", "date", name="uq_training_stress_days"),
    )


class MetricModel(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("athletes.id", ondelete="CASCADE")
    )
    ride_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("rides.id", ondelete="CASCADE"), unique=True
    )
    fatigue_score: Mapped[float | None] = mapped_column(Float)
    recovery_hours: Mapped[float | None] = mapped_column(Float)
    calories_per_km: Mapped[float | None] = mapped_column(Float)
    efficiency_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)


class ChatHistoryModel(Base):
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("athletes.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CalendarEventModel(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("athletes.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, default="training")
    date: Mapped[str] = mapped_column(String, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    weather_temp: Mapped[float | None] = mapped_column(Float)
    weather_humidity: Mapped[float | None] = mapped_column(Float)
    weather_description: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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

    __table_args__ = (
        UniqueConstraint("lat", "lon", "date", name="uq_weather_cache"),
    )


class TrainingGoalModel(Base):
    __tablename__ = "training_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("athletes.id", ondelete="CASCADE")
    )
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    goal_type: Mapped[str] = mapped_column(String, default="granfondo")
    target_date: Mapped[str | None] = mapped_column(String)
    target_distance_km: Mapped[float | None] = mapped_column(Float)
    target_elevation_m: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlannedWorkoutModel(Base):
    __tablename__ = "planned_workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("athletes.id", ondelete="CASCADE")
    )
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    goal_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("training_goals.id", ondelete="SET NULL")
    )
    date: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    workout_type: Mapped[str] = mapped_column(String, default="endurance")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    target_intensity: Mapped[float] = mapped_column(Float, default=0.5)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[str | None] = mapped_column(String)


class RoadIncident(Base):
    __tablename__ = "road_incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    incident_date: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, default="medium")
    description: Mapped[str | None] = mapped_column(Text)
    road_type: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String, default="local")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("source_id", "source", name="uq_road_incidents"),
    )


class RouteSafetyScore(Base):
    __tablename__ = "route_safety_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ride_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("rides.id", ondelete="CASCADE")
    )
    athlete_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("athletes.id", ondelete="CASCADE")
    )
    risk_score: Mapped[float | None] = mapped_column(Float)
    label: Mapped[str | None] = mapped_column(String)
    advice: Mapped[str | None] = mapped_column(Text)
    road_type_counts: Mapped[str | None] = mapped_column(Text)
    has_bike_infrastructure: Mapped[bool | None] = mapped_column(Boolean)
    incident_count: Mapped[int | None] = mapped_column(Integer)
    route_length_km: Mapped[float | None] = mapped_column(Float)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)


class POIModel(Base):
    """Point of Interest (vista, fontana, ristoro, bivio, pericolo, culturale, tecnico)."""

    __tablename__ = "pois"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    photos: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(String)
    difficulty_note: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(Text)
    itinerary_id: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL")
    )
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StravaToken(Base):
    __tablename__ = "strava_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("athletes.id", ondelete="CASCADE"), unique=True
    )
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
    athlete_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("athletes.id", ondelete="CASCADE"), unique=True
    )
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

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="uq_sync_entity_state"),
    )


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
    embedding: Mapped[Any] = mapped_column(
        Vector(EMBEDDING_DIMENSION) if _HAS_PGVECTOR else Text
    )
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
    athlete_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("athletes.id", ondelete="CASCADE"), index=True
    )
    refresh_token: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    jti: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = [
    "Base",
    "EMBEDDING_DIMENSION",
    "UserModel",
    "AthleteModel",
    "RideModel",
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
]
