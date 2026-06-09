"""SQLAlchemy async ORM models for PostgreSQL + SQLite support.

Provides:
- Declarative models matching the existing dataclass schema
- Metadata for Alembic migrations
- Dual-engine support (asyncpg for Postgres, aiosqlite for SQLite)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Float, Integer, Boolean, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Date


class Base(DeclarativeBase):
    pass


class AthleteModel(Base):
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False, default=70.0)
    height_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fat_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    years_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    weekly_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    monthly_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    annual_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    experience_level: Mapped[str] = mapped_column(String(20), nullable=False, default="Beginner")
    goals: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preferred_terrain: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    weekly_volume_km: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    best_segments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    medical_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    equipment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ftp_watts: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_athletes_experience_level", "experience_level"),
        Index("ix_athletes_name", "name"),
    )


class RideModel(Base):
    __tablename__ = "rides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duration_minutes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_speed_kmh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False, default=70.0)
    calories: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    heart_rate_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    elevation_gain_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gps_points: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_rides_athlete_date", "athlete_id", "date"),
        Index("ix_rides_distance", "distance_km"),
        Index("ix_rides_elevation", "elevation_gain_m"),
    )


class MetricModel(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class CalendarEventModel(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, default="training")
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
