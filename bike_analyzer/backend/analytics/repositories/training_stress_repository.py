"""Training stress repository."""

from __future__ import annotations


class TrainingStressRepository:
    def __init__(self, session_factory=None, sync_conn=None):
        self._session_factory = session_factory
        self._sync_conn = sync_conn

    async def upsert_day(self, athlete_id: int, date: str, tss: float, atl: float, ctl: float, tsb: float) -> None:
        if self._session_factory:
            return await self._upsert_async(athlete_id, date, tss, atl, ctl, tsb)
        return self._upsert_sync(athlete_id, date, tss, atl, ctl, tsb)

    async def get_history(self, athlete_id: int, limit: int = 90) -> list[dict]:
        if self._session_factory:
            return await self._get_history_async(athlete_id, limit)
        return self._get_history_sync(athlete_id, limit)

    async def get_latest(self, athlete_id: int) -> dict | None:
        if self._session_factory:
            return await self._get_latest_async(athlete_id)
        return self._get_latest_sync(athlete_id)

    def _upsert_sync(self, athlete_id: int, date: str, tss: float, atl: float, ctl: float, tsb: float) -> None:
        from ..db.database import upsert_training_stress_day
        upsert_training_stress_day(athlete_id, date, tss, atl, ctl, tsb)

    def _get_history_sync(self, athlete_id: int, limit: int = 90) -> list[dict]:
        from ..db.database import get_training_stress_days
        return get_training_stress_days(athlete_id, limit)

    def _get_latest_sync(self, athlete_id: int) -> dict | None:
        from ..db.database import get_latest_training_stress
        return get_latest_training_stress(athlete_id)
