"""Async DB facade for FastAPI routes.

Single async interface that wraps the async SQLAlchemy session.
Routes should use this instead of mixing sync db calls.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import insert

from ..db.async_db import get_session_factory
from ..db.models import AthleteModel, RideModel


async def init_db() -> None:
    from ..db.async_db import init_async_db

    await init_async_db()


def _model_to_dict(model, extra: dict | None = None) -> dict:
    d: dict[str, Any] = {
        "id": model.id,
        "athlete_id": model.athlete_id,
        "date": model.date,
        "distance_km": model.distance_km,
        "duration_minutes": model.duration_minutes,
        "avg_speed_kmh": model.avg_speed_kmh,
        "weight_kg": model.weight_kg,
        "calories": model.calories,
        "heart_rate_avg": model.heart_rate_avg,
        "elevation_gain_m": model.elevation_gain_m,
        "external_source": model.external_source,
        "external_id": model.external_id,
        "title": model.title,
        "created_at": model.created_at.isoformat() if model.created_at else None,
    }
    if extra:
        d.update(extra)
    return {k: v for k, v in d.items() if not (k.startswith("_") or v is None)}


def _ride_to_dict(row) -> dict[str, Any]:
    from bike_analyzer.backend.models.models import Ride as CoreRide

    gps = None
    if row.gps_points:
        try:
            import json

            data = json.loads(row.gps_points)
            gps = [CoreRide._gps_point_from_dict(p) if hasattr(CoreRide, "_gps_point_from_dict") else p for p in data]
        except (json.JSONDecodeError, TypeError):
            gps = None

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


async def get_db_session():
    return get_session_factory()()


async def get_ride(ride_id: int, tenant_id: int | None = None) -> dict | None:
    async with get_session_factory()() as session:
        from sqlalchemy import select

        stmt = select(RideModel).where(RideModel.id == ride_id)
        if tenant_id is not None:
            stmt = stmt.where(RideModel.tenant_id == tenant_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return _ride_to_dict(row)


async def get_rides_by_athlete(athlete_id: int, limit: int = 1000, tenant_id: int | None = None) -> list[dict]:
    async with get_session_factory()() as session:
        from sqlalchemy import select

        stmt = (
            select(RideModel)
            .where(RideModel.athlete_id == athlete_id)
            .order_by(RideModel.date.desc())
            .limit(limit)
        )
        if tenant_id is not None:
            stmt = stmt.where(RideModel.tenant_id == tenant_id)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [_ride_to_dict(r) for r in rows]


async def get_athlete(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    async with get_session_factory()() as session:
        from sqlalchemy import select

        stmt = select(AthleteModel).where(AthleteModel.id == athlete_id)
        if tenant_id is not None:
            stmt = stmt.where(AthleteModel.tenant_id == tenant_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return {
            "id": row.id,
            "name": row.name,
            "age": row.age,
            "weight_kg": row.weight_kg,
            "height_cm": row.height_cm,
            "fat_percentage": row.fat_percentage,
            "years_active": row.years_active,
            "weekly_sessions": row.weekly_sessions,
            "monthly_hours": row.monthly_hours,
            "annual_hours": row.annual_hours,
            "experience_level": row.experience_level,
            "goals": row.goals,
            "preferred_terrain": row.preferred_terrain,
            "weekly_volume_km": row.weekly_volume_km,
            "best_segments": row.best_segments,
            "medical_notes": row.medical_notes,
            "equipment": row.equipment,
            "ftp_watts": row.ftp_watts,
            "password_hash": row.password_hash,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "tenant_id": row.tenant_id,
        }


async def get_athlete_by_name(name: str, tenant_id: int | None = None) -> dict | None:
    async with get_session_factory()() as session:
        from sqlalchemy import select

        stmt = select(AthleteModel).where(AthleteModel.name == name)
        if tenant_id is not None:
            stmt = stmt.where(AthleteModel.tenant_id == tenant_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return {
            "id": row.id,
            "name": row.name,
            "age": row.age,
            "weight_kg": row.weight_kg,
            "height_cm": row.height_cm,
            "fat_percentage": row.fat_percentage,
            "years_active": row.years_active,
            "weekly_sessions": row.weekly_sessions,
            "monthly_hours": row.monthly_hours,
            "annual_hours": row.annual_hours,
            "experience_level": row.experience_level,
            "goals": row.goals,
            "preferred_terrain": row.preferred_terrain,
            "weekly_volume_km": row.weekly_volume_km,
            "best_segments": row.best_segments,
            "medical_notes": row.medical_notes,
            "equipment": row.equipment,
            "ftp_watts": row.ftp_watts,
            "password_hash": row.password_hash,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "tenant_id": row.tenant_id,
        }


async def save_athlete(athlete_data: dict, athlete_id: int | None = None) -> int:
    async with get_session_factory()() as session:
        from sqlalchemy import insert, select

        if athlete_id:
            existing = await session.execute(select(AthleteModel).where(AthleteModel.id == athlete_id))
            if existing.scalar_one_or_none():
                model = existing.scalar_one()
                model.name = athlete_data.get("name", model.name)
                model.weight_kg = athlete_data.get("weight_kg", model.weight_kg)
                model.age = athlete_data.get("age", model.age)
                model.password_hash = athlete_data.get("password_hash", model.password_hash)
                model.tenant_id = athlete_data.get("tenant_id", athlete_id)
                await session.commit()
                return athlete_id

        stmt = (
            insert(AthleteModel)
            .values(
                id=athlete_id,
                name=athlete_data.get("name", ""),
                age=athlete_data.get("age", 30),
                weight_kg=athlete_data.get("weight_kg", 70.0),
                height_cm=athlete_data.get("height_cm"),
                fat_percentage=athlete_data.get("fat_percentage"),
                years_active=athlete_data.get("years_active", 1),
                weekly_sessions=athlete_data.get("weekly_sessions", 3),
                monthly_hours=athlete_data.get("monthly_hours", 0.0),
                annual_hours=athlete_data.get("annual_hours", 0.0),
                experience_level=athlete_data.get("experience_level", "Beginner"),
                goals=athlete_data.get("goals"),
                preferred_terrain=athlete_data.get("preferred_terrain"),
                weekly_volume_km=athlete_data.get("weekly_volume_km", 0.0),
                best_segments=athlete_data.get("best_segments"),
                medical_notes=athlete_data.get("medical_notes"),
                equipment=athlete_data.get("equipment"),
                ftp_watts=athlete_data.get("ftp_watts"),
                password_hash=athlete_data.get("password_hash"),
                tenant_id=athlete_data.get("tenant_id", athlete_id),
                created_at=datetime.now(UTC),
            )
            .returning(AthleteModel.id)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one()


async def save_ride(ride_data: dict) -> int:
    import json

    async with get_session_factory()() as session:
        gps_points = json.dumps(ride_data.get("gps_points")) if ride_data.get("gps_points") else None
        tenant_id = ride_data.get("tenant_id", ride_data.get("athlete_id"))
        stmt = (
            insert(RideModel)
            .values(
                athlete_id=ride_data.get("athlete_id"),
                date=ride_data.get("date"),
                distance_km=ride_data.get("distance_km", 0.0),
                duration_minutes=ride_data.get("duration_minutes", 0.0),
                avg_speed_kmh=ride_data.get("avg_speed_kmh", 0.0),
                weight_kg=ride_data.get("weight_kg", 70.0),
                calories=ride_data.get("calories", 0.0),
                heart_rate_avg=ride_data.get("heart_rate_avg"),
                elevation_gain_m=ride_data.get("elevation_gain_m"),
                gps_points=gps_points,
                external_source=ride_data.get("external_source"),
                external_id=ride_data.get("external_id"),
                title=ride_data.get("title"),
                tenant_id=tenant_id,
                created_at=datetime.now(UTC),
            )
            .returning(RideModel.id)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one()


__all__ = [
    "init_db",
    "get_db_session",
    "get_ride",
    "get_rides_by_athlete",
    "get_athlete",
    "get_athlete_by_name",
    "save_athlete",
    "save_ride",
]
