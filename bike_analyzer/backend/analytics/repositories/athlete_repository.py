"""Athlete repository - data access abstraction for athletes."""

from __future__ import annotations

from datetime import UTC, datetime


class AthleteRepository:
    def __init__(self, session_factory=None, sync_conn=None):
        self._session_factory = session_factory
        self._sync_conn = sync_conn

    async def save(self, athlete: dict, athlete_id=None, tenant_id: int = 0) -> int:
        if self._session_factory:
            return await self._save_async(athlete, tenant_id)
        if self._sync_conn:
            return self._sync_conn.save_athlete(athlete, athlete_id, tenant_id)
        return self._save_sync(athlete, athlete_id, tenant_id)

    async def get_by_id(self, athlete_id: int, tenant_id: int | None = None) -> dict | None:
        if self._session_factory:
            return await self._get_by_id_async(athlete_id, tenant_id)
        if self._sync_conn:
            return self._sync_conn.get_athlete(athlete_id)
        return self._get_by_id_sync(athlete_id, tenant_id)

    async def get_by_name(self, name: str, tenant_id: int | None = None) -> dict | None:
        if self._session_factory:
            return await self._get_by_name_async(name, tenant_id)
        if self._sync_conn:
            return self._sync_conn.get_athlete_by_name(name, tenant_id)
        return self._get_by_name_sync(name, tenant_id)

    async def list_all(self) -> list[dict]:
        if self._session_factory:
            return await self._list_all_async()
        if self._sync_conn:
            return self._sync_conn.get_all_athletes()
        return self._list_all_sync()

    async def _save_async(self, athlete: dict, tenant_id: int = 0) -> int:
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
                    tenant_id=athlete.get("tenant_id", tenant_id),
                    created_at=datetime.now(UTC),
                )
                .returning(self._table.id)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar_one()

    async def _get_by_id_async(self, athlete_id: int, tenant_id: int | None = None) -> dict | None:
        from sqlalchemy import select

        async with self._session_factory() as session:
            stmt = select(self._table).where(self._table.id == athlete_id)
            if tenant_id is not None:
                stmt = stmt.where(self._table.tenant_id == tenant_id)
            result = await session.execute(stmt)
            row = result.scalars().first()
            if row is None:
                return None
            return {c.name: getattr(row, c.name) for c in self._table.__table__.columns}

    async def _get_by_name_async(self, name: str, tenant_id: int | None = None) -> dict | None:
        from sqlalchemy import select

        async with self._session_factory() as session:
            stmt = select(self._table).where(self._table.name == name)
            if tenant_id is not None:
                stmt = stmt.where(self._table.tenant_id == tenant_id)
            result = await session.execute(stmt)
            row = result.scalars().first()
            if row is None:
                return None
            return {c.name: getattr(row, c.name) for c in self._table.__table__.columns}

    async def _list_all_async(self) -> list[dict]:
        from sqlalchemy import select

        async with self._session_factory() as session:
            stmt = select(self._table)
            result = await session.execute(stmt)
            return [
                {c.name: getattr(row, c.name) for c in self._table.__table__.columns}
                for row in result.scalars().all()
            ]

    @property
    def _table(self):
        from ...db.models import AthleteModel

        return AthleteModel

    def _save_sync(self, athlete: dict, athlete_id=None, tenant_id: int = 0) -> int:
        from ..db.database import save_athlete

        return save_athlete(athlete, athlete_id, tenant_id)

    def _get_by_id_sync(self, athlete_id: int, tenant_id: int | None = None) -> dict | None:
        from ..db.database import get_athlete

        athlete = get_athlete(athlete_id, tenant_id)
        return athlete

    def _list_all_sync(self) -> list[dict]:
        from ..db.database import get_all_athletes

        return get_all_athletes()

    def delete(self, athlete_id: int, user_id: int) -> bool:
        from ..db.database import delete_athlete

        return delete_athlete(athlete_id, user_id)
