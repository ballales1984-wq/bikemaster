"""Fitness State repository - persistence for Fitness State Vector."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any


class FitnessStateRepository:
    """Repository for Fitness State Vector persistence."""

    def __init__(self, session_factory=None, sync_conn=None):
        self._session_factory = session_factory
        self._sync_conn = sync_conn

    @property
    def _table(self):
        from ...db.models import FitnessStateModel

        return FitnessStateModel

    async def save(self, state: dict[str, Any], tenant_id: int = 0) -> int:
        if self._session_factory:
            return await self._save_async(state, tenant_id)
        raise RuntimeError("Async session factory required for FitnessStateRepository")

    async def _save_async(self, state: dict[str, Any], tenant_id: int = 0) -> int:
        from sqlalchemy import insert

        async with self._session_factory() as session:
            stmt = (
                insert(self._table)
                .values(
                    athlete_id=state.get("athlete_id"),
                    tenant_id=state.get("tenant_id", tenant_id),
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
                )
                .returning(self._table.id)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar_one()

    async def get_latest(self, athlete_id: int, tenant_id: int | None = None) -> dict[str, Any] | None:
        if self._session_factory:
            return await self._get_latest_async(athlete_id, tenant_id)
        return None

    async def _get_latest_async(self, athlete_id: int, tenant_id: int | None = None) -> dict[str, Any] | None:
        from sqlalchemy import desc, select

        async with self._session_factory() as session:
            stmt = select(self._table).where(self._table.athlete_id == athlete_id)
            if tenant_id is not None:
                stmt = stmt.where(self._table.tenant_id == tenant_id)
            stmt = stmt.order_by(desc(self._table.date)).limit(1)
            result = await session.execute(stmt)
            row = result.scalars().first()
            if row is None:
                return None
            data = {c.name: getattr(row, c.name) for c in self._table.__table__.columns}
            if data.get("risk_indicators"):
                data["risk_indicators"] = json.loads(data["risk_indicators"])
            return data

    async def get_history(self, athlete_id: int, days: int = 30, tenant_id: int | None = None) -> list[dict[str, Any]]:
        if self._session_factory:
            return await self._get_history_async(athlete_id, days, tenant_id)
        return []

    async def _get_history_async(
        self, athlete_id: int, days: int = 30, tenant_id: int | None = None
    ) -> list[dict[str, Any]]:
        from sqlalchemy import desc, select

        async with self._session_factory() as session:
            stmt = select(self._table).where(self._table.athlete_id == athlete_id)
            if tenant_id is not None:
                stmt = stmt.where(self._table.tenant_id == tenant_id)
            stmt = stmt.order_by(desc(self._table.date)).limit(days)
            result = await session.execute(stmt)
            histories = []
            for row in result.scalars().all():
                data = {c.name: getattr(row, c.name) for c in self._table.__table__.columns}
                if data.get("risk_indicators"):
                    data["risk_indicators"] = json.loads(data["risk_indicators"])
                histories.append(data)
            return histories
