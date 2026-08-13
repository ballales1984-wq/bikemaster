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

import contextlib
import json
import logging
import os
import threading
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from ..settings import get_settings
from .models import (
    Base,
    KnowledgeChunkModel,
    RideModel,
    UserOAuthCredentials,
)
from .token_crypto import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

_s = get_settings()

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker | None = None
_engine_lock = threading.Lock()
_session_factory_lock = threading.Lock()


# Core tables required at startup. ``knowledge_chunks`` (PGVector) is created
# best-effort and is not required for the app to boot.
_CORE_TABLES = [
    table
    for table in Base.metadata.tables.values()
    if table.name != "knowledge_chunks"
]


# Query parameters that asyncpg does not support (libpq-specific).
_ASYNC_UNSUPPORTED_PARAMS = {"channel_binding"}


def _extract_sslmode(raw_url: str) -> tuple[str, bool]:
    """Extract sslmode from a database URL without mutating the original.

    Returns (url_without_sslmode, ssl_required).
    """
    if "sslmode=" not in raw_url:
        return raw_url, False
    parsed = urlparse(raw_url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    sslmode = (params.get("sslmode") or [""])[0].lower()
    filtered = {k: v for k, v in params.items() if k != "sslmode"}
    ssl_required = sslmode in {"require", "verify-ca", "verify-full"}
    new_query = urlencode(filtered, doseq=True)
    new_url = urlunparse(parsed._replace(query=new_query))
    return new_url, ssl_required


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
    with _engine_lock:
        if _engine is not None:
            return _engine
        url = (os.environ.get("DATABASE_URL") or _s.database_url or "").strip()
        if not url:
            logger.warning(
                "DATABASE_URL not set or empty; async DB disabled "
                "(falling back to synchronous SQLite layer)."
            )
            return None
        try:
            clean_url, ssl_required = _extract_sslmode(url)
            async_url = _make_async_url(clean_url)
            connect_args = {"ssl": True} if ssl_required else {}
            _engine = create_async_engine(async_url, echo=False, pool_pre_ping=True, connect_args=connect_args)
        except Exception as exc:  # noqa: BLE001
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
        with _session_factory_lock:
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


async def get_user_oauth_credentials_async(user_id: int, provider: str) -> dict | None:
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(UserOAuthCredentials).where(
            UserOAuthCredentials.user_id == user_id,
            UserOAuthCredentials.provider == provider,
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        if not row:
            return None
        client_secret = row.client_secret or ""
        if client_secret:
            with contextlib.suppress(Exception):
                client_secret = decrypt_token(client_secret)
        return {
            "id": row.id,
            "user_id": row.user_id,
            "provider": row.provider,
            "client_id": row.client_id,
            "client_secret": client_secret,
            "redirect_uri": row.redirect_uri,
            "scope": row.scope,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


async def get_all_user_oauth_credentials_async(user_id: int) -> list[dict]:
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(UserOAuthCredentials).where(UserOAuthCredentials.user_id == user_id)
        rows = (await session.execute(stmt)).scalars().all()
        result = []
        for r in rows:
            client_secret = r.client_secret or ""
            if client_secret:
                with contextlib.suppress(Exception):
                    client_secret = decrypt_token(client_secret)
            result.append(
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "provider": r.provider,
                    "client_id": r.client_id,
                    "client_secret": client_secret,
                    "redirect_uri": r.redirect_uri,
                    "scope": r.scope,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
            )
        return result


async def save_user_oauth_credentials_async(user_id: int, provider: str, data: dict) -> None:
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(UserOAuthCredentials).where(
            UserOAuthCredentials.user_id == user_id,
            UserOAuthCredentials.provider == provider,
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        now = datetime.now(UTC)
        client_secret = data.get("client_secret", "")
        if client_secret:
            with contextlib.suppress(Exception):
                client_secret = encrypt_token(client_secret)
        if row:
            row.client_id = data.get("client_id")
            row.client_secret = client_secret
            row.redirect_uri = data.get("redirect_uri")
            row.scope = data.get("scope")
            row.updated_at = now
        else:
            session.add(
                UserOAuthCredentials(
                    user_id=user_id,
                    provider=provider,
                    client_id=data.get("client_id"),
                    client_secret=client_secret,
                    redirect_uri=data.get("redirect_uri"),
                    scope=data.get("scope"),
                    created_at=now,
                    updated_at=now,
                )
            )
        await session.commit()


async def delete_user_oauth_credentials_async(user_id: int, provider: str) -> bool:
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(UserOAuthCredentials).where(
            UserOAuthCredentials.user_id == user_id,
            UserOAuthCredentials.provider == provider,
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        if not row:
            return False
        await session.delete(row)
        await session.commit()
        return True


__all__ = [
    "get_session_factory",
    "init_async_db",
    "get_rides_by_athlete_async",
    "get_user_oauth_credentials_async",
    "get_all_user_oauth_credentials_async",
    "save_user_oauth_credentials_async",
    "delete_user_oauth_credentials_async",
]
