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
    DateTime,
    Float,
    ForeignKey,
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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AthleteModel(Base):
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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
    athlete_id: Mapped[int | None] = mapped_column(Integer)
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

    __table_args__ = (
        UniqueConstraint(
            "external_source", "external_id", name="uq_rides_external_identity"
        ),
    )


class FitnessStateModel(Base):
    __tablename__ = "fitness_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("athletes.id"))
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
    created_by: Mapped[int | None] = mapped_column(Integer)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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


class ChatHistoryModel(Base):
    """Persistent AI Coach conversation history (mirrors SQLite ``chat_history``)."""

    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int | None] = mapped_column(Integer, index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TrainingGoalModel(Base):
    """Training goal (e.g. granfondo target) for an athlete."""

    __tablename__ = "training_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("athletes.id"))
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
    """Planned workout linked to a training goal."""

    __tablename__ = "planned_workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("athletes.id"))
    tenant_id: Mapped[int] = mapped_column(Integer, default=0)
    goal_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("training_goals.id"))
    date: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    workout_type: Mapped[str] = mapped_column(String, default="endurance")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    target_intensity: Mapped[float] = mapped_column(Float, default=0.5)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[str | None] = mapped_column(String)


__all__ = [
    "Base",
    "EMBEDDING_DIMENSION",
    "UserModel",
    "AthleteModel",
    "RideModel",
    "FitnessStateModel",
    "POIModel",
    "KnowledgeChunkModel",
    "ChatHistoryModel",
    "TrainingGoalModel",
    "PlannedWorkoutModel",
]
