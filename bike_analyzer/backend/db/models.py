"""SQLAlchemy async ORM models for PostgreSQL + SQLite support.

Provides:
- Declarative models matching the existing dataclass schema
- Metadata for Alembic migrations
- Dual-engine support (asyncpg for Postgres, aiosqlite for SQLite)
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

try:
    from pgvector.sqlalchemy import Vector

    VECTOR_TYPE = Vector(1536)
except ImportError:
    VECTOR_TYPE = Text


class Base(DeclarativeBase):
    pass


class AthleteModel(Base):
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    weight_kg: Mapped[float] = mapped_column(
        Float, nullable=False, default=70.0
    )
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    years_active: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    weekly_sessions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3
    )
    monthly_hours: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    annual_hours: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    experience_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Beginner"
    )
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_terrain: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    weekly_volume_km: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    best_segments: Mapped[str | None] = mapped_column(Text, nullable=True)
    medical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    equipment: Mapped[str | None] = mapped_column(Text, nullable=True)
    ftp_watts: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_athletes_experience_level", "experience_level"),
        Index("ix_athletes_name", "name"),
    )


class RideModel(Base):
    __tablename__ = "rides"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    athlete_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    distance_km: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    duration_minutes: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    avg_speed_kmh: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    weight_kg: Mapped[float] = mapped_column(
        Float, nullable=False, default=70.0
    )
    calories: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    heart_rate_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation_gain_m: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    external_source: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gps_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_rides_athlete_date", "athlete_id", "date"),
        Index("ix_rides_distance", "distance_km"),
        Index("ix_rides_elevation", "elevation_gain_m"),
        Index("uq_rides_external_identity", "external_source", "external_id", unique=True),
    )


class FitnessStateModel(Base):
    __tablename__ = "fitness_states"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    athlete_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    date: Mapped[str] = mapped_column(String(20), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fitness: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fatigue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    form: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    atl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ctl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tsb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recovery_hours_needed: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    weekly_tss: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    monthly_tss: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    trend_7d: Mapped[str] = mapped_column(String(20), nullable=False, default="stable")
    trend_30d: Mapped[str] = mapped_column(String(20), nullable=False, default="stable")
    risk_indicators: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_fitness_states_athlete_date", "athlete_id", "date"),
        Index("ix_fitness_states_ctl", "ctl"),
    )


AthleteTable = AthleteModel
RideTable = RideModel
FitnessStateTable = FitnessStateModel


class MetricModel(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    athlete_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )


class StravaTokenModel(Base):
    __tablename__ = "strava_tokens"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    athlete_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    access_token: Mapped[str] = mapped_column(String(1024), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(1024), nullable=False)
    expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scope: Mapped[str | None] = mapped_column(String(200), nullable=True)
    athlete_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_strava_tokens_athlete", "athlete_id", unique=True),
    )


class GarminTokenModel(Base):
    __tablename__ = "garmin_tokens"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    athlete_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    access_token: Mapped[str] = mapped_column(String(1024), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(1024), nullable=False)
    expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scope: Mapped[str | None] = mapped_column(String(200), nullable=True)
    athlete_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_garmin_tokens_athlete", "athlete_id", unique=True),
    )


class CalendarEventModel(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    athlete_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="training"
    )
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )


class KnowledgeChunkModel(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(200), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(VECTOR_TYPE, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    section: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_knowledge_chunks_topic", "topic"),
    )


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    athlete_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )


KnowledgeChunkTable = KnowledgeChunkModel
ChatMessageTable = ChatMessageModel
