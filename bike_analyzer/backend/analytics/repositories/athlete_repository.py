"""Athlete repository - data access abstraction for athletes."""

from __future__ import annotations

from datetime import UTC, datetime

from ..models.models import AthleteProfile


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
