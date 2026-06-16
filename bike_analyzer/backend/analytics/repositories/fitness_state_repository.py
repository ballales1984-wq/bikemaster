"""Fitness State repository - persistence for Fitness State Vector."""

from __future__ import annotations

import json
from datetime import UTC, datetime, date
from typing import Any


class FitnessStateRepository:
    """Repository for Fitness State Vector persistence."""

    def __init__(self, session_factory=None, sync_conn=None):
        self._session_factory = session_factory
        self._sync_conn = sync_conn

    @property
    def _table(self):
        from ..db.models import FitnessStateModel
        return FitnessStateModel

    async def save(self, state: dict[str, Any]) -> int:
        if self._session_factory:
            return await self._save_async(state)
        raise RuntimeError("Async session factory required for FitnessStateRepository")

    async def _save_async(self, state: dict[str, Any]) -> int:
        from sqlalchemy import insert

        async with self._session_factory() as session:
            stmt = insert(self._table).values(
                athlete_id=state.get("athlete_id"),
                date=state.get("date", date.today().isoformat()),
                computed_at=state.get("computed_at", datetime.now(UTC)),
                fitness=state.get("fitness", 0.0),
                fatigue=state.get("fatigue", 0.0),
                form=state.get("form", 0.0),
                atl=state.get("atl", 0.0),
                ctl=state.get("ctl", 0.0),
                tsb=state.get("tsb", 0.0),
                recovery_hours_needed=state.get("recovery_hours_needed", 0.0),
                weekly_tss=state.get("weekly_tss", 0.0),
                monthly_tss=state.get("monthly_tss", 0.0),
                trend_7d=state.get("trend_7d", "stable"),
                trend_30d=state.get("trend_30d", "stable"),
                risk_indicators=json.dumps(state.get("risk_indicators", [])),
                recommendation=state.get("recommendation"),
            ).returning(self._table.id)
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar_one()

    async def get_latest(self, athlete_id: int) -> dict[str, Any] | None:
        if self._session_factory:
            return await self._get_latest_async(athlete_id)
        return None

    async def _get_latest_async(self, athlete_id: int) -> dict[str, Any] | None:
        from sqlalchemy import select, desc

        async with self._session_factory() as session:
            stmt = (
                select(self._table)
                .where(self._table.athlete_id == athlete_id)
                .order_by(desc(self._table.date))
                .limit(1)
            )
            result = await session.execute(stmt)
            row = result.mappings().first()
            if not row:
                return None
            data = dict(row)
            if data.get("risk_indicators"):
                data["risk_indicators"] = json.loads(data["risk_indicators"])
            return data

    async def get_history(self, athlete_id: int, days: int = 30) -> list[dict[str, Any]]:
        if self._session_factory:
            return await self._get_history_async(athlete_id, days)
        return []

    async def _get_history_async(self, athlete_id: int, days: int = 30) -> list[dict[str, Any]]:
        from sqlalchemy import select, desc

        async with self._session_factory() as session:
            stmt = (
                select(self._table)
                .where(self._table.athlete_id == athlete_id)
                .order_by(desc(self._table.date))
                .limit(days)
            )
            result = await session.execute(stmt)
            rows = result.mappings().all()
            histories = []
            for row in rows:
                data = dict(row)
                if data.get("risk_indicators"):
                    data["risk_indicators"] = json.loads(data["risk_indicators"])
                histories.append(data)
            return histories