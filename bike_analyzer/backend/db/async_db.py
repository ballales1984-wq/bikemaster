"""Async DB adapter.

Provides the async SQLAlchemy engine, session factory and table initialization
used by the optional cloud sync (PostgreSQL) code paths. When ``DATABASE_URL`` is
not set the application falls back to the synchronous SQLite layer in
``db/database.py`` and this module raises if its session factory is requested.

The async URL scheme is derived from ``DATABASE_URL`` so both PostgreSQL
(``postgresql+asyncpg://``, cloud sync) and SQLite (``sqlite+aiosqlite://``,
local dev / tests) are supported.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from ..settings import get_settings
from .models import (
    AthleteModel,
    Base,
    CalendarEventModel,
    ChatHistoryModel,
    FitnessStateModel,
    GarminToken,
    KnowledgeChunkModel,
    MetricModel,
    PlannedWorkoutModel,
    POIModel,
    RideModel,
    RoadIncident,
    RouteSafetyScore,
    SessionModel,
    StravaToken,
    SyncConflict,
    SyncEntityState,
    SyncSetting,
    TrainingGoalModel,
    TrainingStressDayModel,
    UserModel,
    WeatherCache,
)

logger = logging.getLogger(__name__)

_s = get_settings()

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker | None = None

# Core tables required at startup. ``knowledge_chunks`` (PGVector) is created
# best-effort and is not required for the app to boot.
_CORE_TABLES = [
    UserModel.__table__,
    AthleteModel.__table__,
    RideModel.__table__,
    FitnessStateModel.__table__,
    TrainingStressDayModel.__table__,
    MetricModel.__table__,
    POIModel.__table__,
    ChatHistoryModel.__table__,
    CalendarEventModel.__table__,
    TrainingGoalModel.__table__,
    PlannedWorkoutModel.__table__,
    RoadIncident.__table__,
    RouteSafetyScore.__table__,
    StravaToken.__table__,
    GarminToken.__table__,
    SyncEntityState.__table__,
    SyncSetting.__table__,
    SyncConflict.__table__,
    SessionModel.__table__,
    WeatherCache.__table__,
]


# Query parameters that asyncpg does not support (libpq-specific).
_ASYNC_UNSUPPORTED_PARAMS = {"channel_binding", "sslmode"}


def _make_async_url(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("postgresql://"):
        raw = "postgresql+asyncpg://" + raw[len("postgresql://"):]
    elif raw.startswith("postgres://"):
        raw = "postgresql+asyncpg://" + raw[len("postgres://"):]
    elif raw.startswith("sqlite://"):
        raw = "sqlite+aiosqlite://" + raw[len("sqlite://"):]
    elif "://" not in raw:
        return "sqlite+aiosqlite:///" + raw

    parsed = urlparse(raw)
    if parsed.scheme.startswith("postgresql+asyncpg") and parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        filtered = {k: v for k, v in params.items() if k not in _ASYNC_UNSUPPORTED_PARAMS}
        if filtered != params:
            new_query = urlencode(filtered, doseq=True)
            raw = urlunparse(parsed._replace(query=new_query))
    return raw


def _get_engine() -> AsyncEngine | None:
    global _engine
    if _engine is not None:
        return _engine
    # Strip first: a value with surrounding whitespace (e.g. a pasted
    # connection string with a trailing newline/space) is truthy and would
    # otherwise slip past the `if not url` guard and crash create_async_engine.
    # Read DATABASE_URL fresh from the environment (falling back to the cached
    # settings) so the engine reflects the current configuration even when the
    # settings singleton was constructed before DATABASE_URL was set.
    url = (os.environ.get("DATABASE_URL") or _s.database_url or "").strip()
    if not url:
        logger.warning(
            "DATABASE_URL not set or empty; async DB disabled "
            "(falling back to synchronous SQLite layer)."
        )
        return None
    try:
        _engine = create_async_engine(_make_async_url(url), echo=False, pool_pre_ping=True)
    except Exception as exc:  # noqa: BLE001
        # Never let a malformed DATABASE_URL take down startup. Log the
        # scheme only (never the full URL, which embeds the password) and
        # fall back to SQLite; get_session_factory() will surface a clear
        # RuntimeError if the async path is actually requested.
        scheme = url.split("://", 1)[0] if "://" in url else url[:12]
        logger.error(
            "Failed to build async engine from DATABASE_URL (scheme=%r); "
            "async DB disabled (falling back to SQLite): %s",
            scheme,
            exc,
        )
        return None
    return _engine


def get_session_factory() -> async_sessionmaker:
    """Return the async session factory, creating the engine lazily.

    Raises RuntimeError if DATABASE_URL is not configured.
    """
    global _session_factory
    if _session_factory is None:
        engine = _get_engine()
        if engine is None:
            raise RuntimeError("DATABASE_URL not configured; async DB unavailable")
        _session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return _session_factory


async def init_async_db() -> None:
    """Create the async tables. Safe to call multiple times."""
    engine = _get_engine()
    if engine is None:
        return
    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:  # noqa: BLE001
            logger.debug("pgvector extension unavailable; vector search disabled")
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(sync_conn, tables=_CORE_TABLES)
        )
    # knowledge_chunks is optional (PGVector); create it best-effort.
    try:
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(
                    sync_conn, tables=[KnowledgeChunkModel.__table__]
                )
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not create knowledge_chunks table (PGVector disabled): %s", exc)


def _ride_row_to_dict(row: RideModel) -> dict[str, Any]:
    gps = None
    if row.gps_points:
        try:
            gps = json.loads(row.gps_points)
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
        "external_source": row.external_source,
        "external_id": row.external_id,
        "title": row.title,
        "tenant_id": row.tenant_id,
    }


async def get_rides_by_athlete_async(
    athlete_id: int, tenant_id: int | None = None, limit: int = 90
) -> list[dict]:
    """Load historical rides for the analytics engine (replaces the old stub)."""
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(RideModel)
            .where(RideModel.athlete_id == athlete_id)
            .order_by(RideModel.date.desc())
            .limit(limit)
        )
        if tenant_id is not None:
            stmt = stmt.where(RideModel.tenant_id == tenant_id)
        rows = (await session.execute(stmt)).scalars().all()
        return [_ride_row_to_dict(r) for r in rows]


__all__ = [
    "get_session_factory",
    "init_async_db",
    "get_rides_by_athlete_async",
]
