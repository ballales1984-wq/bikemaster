"""Async database layer for PostgreSQL (asyncpg) with SQLite fallback.

Mirrors the sync database.py API but uses async SQLAlchemy sessions.
Only active when DATABASE_URL points to PostgreSQL or when explicitly enabled.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..settings import get_settings

_engine = None
_async_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        s = get_settings()
        db_url = s.database_url or f"sqlite+aiosqlite:///{s.db_path}"
        _engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
    return _engine


def get_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_factory


async def get_async_session() -> AsyncSession:
    factory = get_session_factory()
    return factory()


async def init_async_db():
    from ..db.models import Base
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def save_ride_async(ride: dict) -> int:
    from ..db.models import RideModel
    async with get_async_session() as session:
        gps_points = json.dumps(ride.get("gps_points")) if ride.get("gps_points") else None
        stmt = insert(RideModel).values(
            athlete_id=ride.get("athlete_id"),
            date=ride.get("date"),
            distance_km=ride.get("distance_km", 0),
            duration_minutes=ride.get("duration_minutes", 0),
            avg_speed_kmh=ride.get("avg_speed_kmh", 0),
            weight_kg=ride.get("weight_kg", 70),
            calories=ride.get("calories", 0),
            heart_rate_avg=ride.get("heart_rate_avg"),
            elevation_gain_m=ride.get("elevation_gain_m"),
            gps_points=gps_points,
            created_at=datetime.now(timezone.utc),
        ).returning(RideModel.id)
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one()


async def get_ride_async(ride_id: int) -> Optional[dict]:
    from ..db.models import RideModel
    async with get_async_session() as session:
        stmt = select(RideModel).where(RideModel.id == ride_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return None
        gps = json.loads(row.gps_points) if row.gps_points else None
        return {
            "id": row.id,
            "athlete_id": row.athlete_id,
            "date": row.date,
            "distance_km": row.distance_km,
            "duration_minutes": row.duration_minutes,
            "avg_speed_kmh": row.avg_speed_kmh,
            "weight_kg": row.weight_kg,
            "calories": row.calories,
            "heart_rate_avg": row.heart_rate_avg,
            "elevation_gain_m": row.elevation_gain_m,
            "gps_points": gps,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }


async def get_all_rides_async() -> List[dict]:
    from ..db.models import RideModel
    async with get_async_session() as session:
        stmt = select(RideModel).order_by(RideModel.date.desc())
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [_ride_model_to_dict(r) for r in rows]


async def get_rides_by_athlete_async(athlete_id: int) -> List[dict]:
    from ..db.models import RideModel
    async with get_async_session() as session:
        stmt = select(RideModel).where(RideModel.athlete_id == athlete_id).order_by(RideModel.date.desc())
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [_ride_model_to_dict(r) for r in rows]


async def delete_ride_async(ride_id: int) -> bool:
    from ..db.models import RideModel
    async with get_async_session() as session:
        stmt = delete(RideModel).where(RideModel.id == ride_id)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0


async def save_athlete_async(athlete: dict) -> int:
    from ..db.models import AthleteModel
    async with get_async_session() as session:
        stmt = insert(AthleteModel).values(
            name=athlete.get("name"),
            age=athlete.get("age", 30),
            weight_kg=athlete.get("weight_kg", 70),
            height_cm=athlete.get("height_cm"),
            fat_percentage=athlete.get("fat_percentage"),
            years_active=athlete.get("years_active", 1),
            weekly_sessions=athlete.get("weekly_sessions", 3),
            monthly_hours=athlete.get("monthly_hours", 0),
            annual_hours=athlete.get("annual_hours", 0),
            experience_level=athlete.get("experience_level", "Beginner"),
            goals=athlete.get("goals"),
            preferred_terrain=athlete.get("preferred_terrain"),
            weekly_volume_km=athlete.get("weekly_volume_km", 0),
            best_segments=athlete.get("best_segments"),
            medical_notes=athlete.get("medical_notes"),
            equipment=athlete.get("equipment"),
            ftp_watts=athlete.get("ftp_watts"),
            created_at=datetime.now(timezone.utc),
        ).returning(AthleteModel.id)
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one()


def _ride_model_to_dict(row) -> dict:
    gps = json.loads(row.gps_points) if row.gps_points else None
    return {
        "id": row.id,
        "athlete_id": row.athlete_id,
        "date": row.date,
        "distance_km": row.distance_km,
        "duration_minutes": row.duration_minutes,
        "avg_speed_kmh": row.avg_speed_kmh,
        "weight_kg": row.weight_kg,
        "calories": row.calories,
        "heart_rate_avg": row.heart_rate_avg,
        "elevation_gain_m": row.elevation_gain_m,
        "gps_points": gps,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def close_async_db():
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
