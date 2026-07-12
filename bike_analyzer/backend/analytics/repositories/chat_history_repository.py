"""Chat history repository - async persistence for AI Coach conversations.

Mirrors :class:`FitnessStateRepository`: it only operates against the async
session factory (PostgreSQL in production, SQLite for local dev). The synchronous
``db.database`` functions remain the source of truth for the SQLite path used by
the coach today; this repository is the counterpart for the async data layer
once the broader sync -> async migration lands.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class ChatHistoryRepository:
    """Async persistence for per-user AI Coach conversation history."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    @property
    def _table(self):
        from ...db.models import ChatHistoryModel

        return ChatHistoryModel

    async def save(self, athlete_id: int | None, role: str, content: str, tenant_id: int = 0) -> int:
        if self._session_factory is None:
            raise RuntimeError("Async session factory required for ChatHistoryRepository")
        from sqlalchemy import insert

        async with self._session_factory() as session:
            stmt = (
                insert(self._table)
                .values(
                    athlete_id=athlete_id,
                    tenant_id=tenant_id,
                    role=role,
                    content=content,
                    created_at=datetime.now(UTC),
                )
                .returning(self._table.id)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar_one()

    async def get_recent(self, athlete_id: int, limit: int = 10, tenant_id: int | None = None) -> list[dict[str, Any]]:
        if self._session_factory is None:
            return []
        from sqlalchemy import desc, select

        async with self._session_factory() as session:
            stmt = select(self._table).where(self._table.athlete_id == athlete_id)
            if tenant_id is not None:
                stmt = stmt.where(self._table.tenant_id == tenant_id)
            stmt = stmt.order_by(desc(self._table.created_at)).limit(limit)
            result = await session.execute(stmt)
            return [dict(row) for row in result.mappings().all()]

    async def clear(self, athlete_id: int, tenant_id: int | None = None) -> int:
        if self._session_factory is None:
            return 0
        from sqlalchemy import delete

        async with self._session_factory() as session:
            stmt = delete(self._table).where(self._table.athlete_id == athlete_id)
            if tenant_id is not None:
                stmt = stmt.where(self._table.tenant_id == tenant_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount or 0

    async def prune(self, athlete_id: int, retention_days: int = 90, tenant_id: int | None = None) -> int:
        if self._session_factory is None:
            return 0
        from sqlalchemy import delete

        cutoff = datetime.now(UTC).fromordinal(datetime.now(UTC).toordinal() - retention_days)
        async with self._session_factory() as session:
            stmt = delete(self._table).where(
                self._table.athlete_id == athlete_id,
                self._table.created_at < cutoff,
            )
            if tenant_id is not None:
                stmt = stmt.where(self._table.tenant_id == tenant_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount or 0
