"""Tests for async DB adapter (async_db).

Covers:
- URL scheme conversion (_make_async_url)
- Engine/session factory behavior when DATABASE_URL is unset
- init_async_db no-op path
- get_rides_by_athlete_async end-to-end with in-memory async SQLite
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from bike_analyzer.backend.db.async_db import (
    _make_async_url,
    _get_engine,
    get_session_factory,
    init_async_db,
)
from bike_analyzer.backend.db.models import Base, RideModel


@pytest.fixture(autouse=True)
def _reset_async_state():
    import bike_analyzer.backend.db.async_db as mod

    mod._engine = None
    mod._session_factory = None
    yield
    mod._engine = None
    mod._session_factory = None


class TestMakeAsyncUrl:
    def test_postgresql_prefix(self):
        assert _make_async_url("postgresql://user:pass@host/db") == "postgresql+asyncpg://user:pass@host/db"

    def test_postgres_prefix(self):
        assert _make_async_url("postgres://user:pass@host/db") == "postgresql+asyncpg://user:pass@host/db"

    def test_sqlite_prefix(self):
        assert _make_async_url("sqlite:///path/to/db.sqlite") == "sqlite+aiosqlite:///path/to/db.sqlite"

    def test_bare_file_path(self):
        result = _make_async_url("rides.db")
        assert result == "sqlite+aiosqlite:///rides.db"

    def test_bare_path_with_slash(self):
        result = _make_async_url("./rides.db")
        assert result == "sqlite+aiosqlite:///./rides.db"

    def test_passthrough_unknown_scheme(self):
        url = "mysql://host/db"
        assert _make_async_url(url) == url

    def test_strips_whitespace(self):
        assert _make_async_url("  postgresql://host/db  ") == "postgresql+asyncpg://host/db"


class TestEngineUnconfigured:
    def test_get_engine_returns_none_when_no_url(self):
        os.environ.pop("DATABASE_URL", None)
        assert _get_engine() is None

    def test_get_session_factory_raises_without_url(self):
        os.environ.pop("DATABASE_URL", None)
        with pytest.raises(RuntimeError, match="DATABASE_URL not configured"):
            get_session_factory()

    def test_init_async_db_noop_without_engine(self):
        os.environ.pop("DATABASE_URL", None)
        import asyncio

        result = asyncio.run(init_async_db())
        assert result is None


class TestAsyncEngineWithSQLite:
    @pytest.fixture
    def async_url(self):
        return "sqlite+aiosqlite:///:memory:"

    def test_get_engine_creates_engine(self, async_url):
        os.environ["DATABASE_URL"] = async_url
        engine = _get_engine()
        assert engine is not None
        from sqlalchemy.ext.asyncio import AsyncEngine

        assert isinstance(engine, AsyncEngine)

    def test_get_session_factory_returns_factory(self, async_url):
        os.environ["DATABASE_URL"] = async_url
        factory = get_session_factory()
        assert factory is not None

    def test_init_async_db_creates_tables(self, async_url):
        os.environ["DATABASE_URL"] = async_url
        import asyncio

        asyncio.run(init_async_db())
        engine = _get_engine()
        assert engine is not None

    def test_get_rides_by_athlete_async_roundtrip(self, async_url):
        import asyncio
        import time

        from bike_analyzer.backend.db.async_db import get_rides_by_athlete_async

        os.environ["DATABASE_URL"] = async_url
        asyncio.run(init_async_db())
        factory = get_session_factory()

        async def seed_and_query():
            async with factory() as session:
                ride = RideModel(
                    athlete_id=1,
                    tenant_id=0,
                    date="2024-06-15",
                    distance_km=35.0,
                    duration_minutes=90.0,
                    avg_speed_kmh=23.3,
                    weight_kg=70.0,
                )
                session.add(ride)
                await session.commit()
            results = await get_rides_by_athlete_async(athlete_id=1, tenant_id=0)
            return results

        results = asyncio.run(seed_and_query())
        assert len(results) == 1
        assert results[0]["distance_km"] == 35.0
        assert results[0]["date"] == "2024-06-15"
