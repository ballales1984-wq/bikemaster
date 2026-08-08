"""AetherMap PostgreSQL store (Sprint 3 — storage produzione).

Wraps SQLAlchemy async to persist ``Oggetto`` and state history on PostgreSQL.
Falls back to ``SpatialStore`` when ``DATABASE_URL`` is not configured.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from aethermap.ai.models import Oggetto, Stato
from aethermap.data.store import SpatialStore, WorldStore


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PostgresStore:
    """Persist AetherMap objects on PostgreSQL via SQLAlchemy async."""

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory
        self._spatial = SpatialStore()

    async def add(self, obj: Oggetto) -> None:
        self._spatial.add(obj)
        async with self._session_factory() as session:
            from sqlalchemy import select

            from bike_analyzer.backend.db.models import AetherMapObjectModel

            data = obj.model_dump(mode="json")
            pos = obj.posizione
            record = AetherMapObjectModel(
                id=obj.id,
                tipo=obj.tipo,
                lat=pos.lat,
                lon=pos.lon,
                alt=getattr(pos, "alt", 0.0) or 0.0,
                s2=getattr(pos, "s2", None),
                h3=getattr(pos, "h3", None),
                cube_face=getattr(pos, "cube_face", None),
                cube_u=getattr(pos, "cube_u", None),
                cube_v=getattr(pos, "cube_v", None),
                data=data,
            )
            await session.merge(record)
            await session.commit()

    async def add_state(self, obj_id: str, stato: Stato) -> None:
        async with self._session_factory() as session:
            from bike_analyzer.backend.db.models import AetherMapStateHistoryModel

            record = AetherMapStateHistoryModel(
                object_id=obj_id,
                campi=stato.campi,
                t=stato.t,
                confidence=stato.confidence,
            )
            session.add(record)
            await session.commit()

    async def prune_state_history(self, max_age_days: int = 30) -> int:
        """Remove state history entries older than ``max_age_days``.

        Returns the number of rows deleted.
        """
        cutoff = datetime.now(UTC).timestamp() - max_age_days * 86400
        async with self._session_factory() as session:
            from datetime import datetime as dt

            from bike_analyzer.backend.db.models import AetherMapStateHistoryModel

            cutoff_dt = dt.fromtimestamp(cutoff, tz=UTC)
            stmt = __import__("sqlalchemy").delete(AetherMapStateHistoryModel).where(
                AetherMapStateHistoryModel.t < cutoff_dt
            )
            result = await session.execute(stmt)
            await session.commit()
            return int(result.rowcount)

    def get(self, oid: str) -> Oggetto | None:
        return self._spatial.get(oid)

    def all(self) -> Iterable[Oggetto]:
        return self._spatial.all()

    def query_s2(self, s2: str) -> list[Oggetto]:
        return self._spatial.query_s2(s2)

    def query_h3(self, h3: str) -> list[Oggetto]:
        return self._spatial.query_h3(h3)

    def query_radius(self, lat: float, lon: float, radius_m: float) -> list[Oggetto]:
        return self._spatial.query_radius(lat, lon, radius_m)


class PersistentWorldStore(WorldStore):
    """WorldStore backed by PostgreSQL when available, else in-memory."""

    def __init__(self, session_factory: Any | None = None) -> None:
        if session_factory is not None:
            self._pg = PostgresStore(session_factory)
            self.store = SpatialStore()
        else:
            self._pg = None
            self.store = SpatialStore()
        super().__init__(store=self.store)

    async def add(self, obj: Oggetto) -> None:
        await super().add(obj)
        if self._pg is not None:
            await self._pg.add(obj)

    async def add_state(self, obj_id: str, stato: Stato) -> None:
        if self._pg is not None:
            await self._pg.add_state(obj_id, stato)


def get_postgres_session_factory() -> Any | None:
    """Return the BikeMaster async session factory if PostgreSQL is configured.

    Returns ``None`` when ``DATABASE_URL`` is not set, allowing the caller
    to fall back to the in-memory ``SpatialStore``.
    """
    try:
        from bike_analyzer.backend.db.async_db import get_session_factory

        return get_session_factory()
    except Exception:
        return None
