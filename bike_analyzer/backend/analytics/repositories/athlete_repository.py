"""Athlete repository - data access abstraction for athletes."""

from __future__ import annotations

from datetime import UTC, datetime

from ...db.models import AthleteModel as AthleteTable


class AthleteRepository:
    def __init__(self, session_factory=None, sync_conn=None):
        self._session_factory = session_factory
        self._sync_conn = sync_conn

    async def save(self, athlete: dict, athlete_id=None) -> int:
        if self._session_factory:
            return await self._save_async(athlete)
        return self._save_sync(athlete, athlete_id)

    async def get_by_id(self, athlete_id: int) -> dict | None:
        if self._session_factory:
            return await self._get_by_id_async(athlete_id)
        return self._get_by_id_sync(athlete_id)

    async def get_by_name(self, name: str) -> dict | None:
        if self._session_factory:
            return await self._get_by_name_async(name)
        return self._get_by_name_sync(name)

    async def list_all(self) -> list[dict]:
        if self._session_factory:
            return await self._list_all_async()
        return self._list_all_sync()

    async def _save_async(self, athlete: dict) -> int:
        from sqlalchemy import insert

        async with self._session_factory() as session:
            stmt = (
                insert(self._table)
                .values(
                    name=athlete.get("name", ""),
                    age=athlete.get("age", 30),
                    weight_kg=athlete.get("weight_kg", 70.0),
                    height_cm=athlete.get("height_cm"),
                    experience_level=athlete.get("experience_level", "Beginner"),
                    goals=athlete.get("goals"),
                    preferred_terrain=athlete.get("preferred_terrain"),
                    weekly_volume_km=athlete.get("weekly_volume_km", 0.0),
                    ftp_watts=athlete.get("ftp_watts"),
                    created_at=datetime.now(UTC),
                )
                .returning(self._table.id)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar_one()

    async def _get_by_id_async(self, athlete_id: int) -> dict | None:
        from sqlalchemy import select

        async with self._session_factory() as session:
            stmt = select(self._table).where(self._table.id == athlete_id)
            result = await session.execute(stmt)
            row = result.mappings().first()
            return dict(row) if row else None

    async def _get_by_name_async(self, name: str) -> dict | None:
        from sqlalchemy import select

        async with self._session_factory() as session:
            stmt = select(self._table).where(self._table.name == name)
            result = await session.execute(stmt)
            row = result.mappings().first()
            return dict(row) if row else None

    async def _list_all_async(self) -> list[dict]:
        from sqlalchemy import select

        async with self._session_factory() as session:
            stmt = select(self._table)
            result = await session.execute(stmt)
            return [dict(row) for row in result.mappings().all()]

    @property
    def _table(self):
        from ..db.async_db import AthleteTable
        return AthleteTable

    def _save_sync(self, athlete: dict, athlete_id=None) -> int:
        from ..db.database import save_athlete
        return save_athlete(athlete, athlete_id)

    def _get_by_id_sync(self, athlete_id: int) -> dict | None:
        from ..db.database import get_athlete
        return get_athlete(athlete_id)

    def _get_by_name_sync(self, name: str) -> dict | None:
        from ..db.database import get_athlete_by_name
        return get_athlete_by_name(name)

    def _list_all_sync(self) -> list[dict]:
        from ..db.database import get_all_athletes
        return get_all_athletes()
