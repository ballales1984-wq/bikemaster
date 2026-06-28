"""Tests for AthleteRepository coverage gaps."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bike_analyzer.backend.analytics.repositories.athlete_repository import (
    AthleteRepository,
)


def _make_async_session():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


def _make_factory():
    factory = MagicMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=_make_async_session())
    cm.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = cm
    return factory


class TestAthleteRepository:
    def test_constructor_defaults(self):
        repo = AthleteRepository()
        assert repo._session_factory is None
        assert repo._sync_conn is None

    @pytest.mark.asyncio
    async def test_save_async(self):
        factory = _make_factory()
        session = factory.return_value.__aenter__.return_value
        result_mock = MagicMock()
        result_mock.scalar_one.return_value = 42
        session.execute.return_value = result_mock

        repo = AthleteRepository(session_factory=factory)
        athlete_id = await repo.save({"name": "Test Rider", "age": 30, "weight_kg": 70.0})
        assert athlete_id == 42

    @pytest.mark.asyncio
    async def test_get_by_id_async_found(self):
        factory = _make_factory()
        session = factory.return_value.__aenter__.return_value
        mappings_mock = MagicMock()
        mappings_mock.first.return_value = {"id": 1, "name": "Test Rider"}
        result_mock = MagicMock()
        result_mock.mappings.return_value = mappings_mock
        session.execute.return_value = result_mock

        repo = AthleteRepository(session_factory=factory)
        result = await repo.get_by_id(1)
        assert result["id"] == 1
        assert result["name"] == "Test Rider"

    @pytest.mark.asyncio
    async def test_get_by_id_async_not_found(self):
        factory = _make_factory()
        session = factory.return_value.__aenter__.return_value
        mappings_mock = MagicMock()
        mappings_mock.first.return_value = None
        result_mock = MagicMock()
        result_mock.mappings.return_value = mappings_mock
        session.execute.return_value = result_mock

        repo = AthleteRepository(session_factory=factory)
        result = await repo.get_by_id(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_name_async(self):
        factory = _make_factory()
        session = factory.return_value.__aenter__.return_value
        mappings_mock = MagicMock()
        mappings_mock.first.return_value = {"id": 1, "name": "Test Rider"}
        result_mock = MagicMock()
        result_mock.mappings.return_value = mappings_mock
        session.execute.return_value = result_mock

        repo = AthleteRepository(session_factory=factory)
        result = await repo.get_by_name("Test Rider")
        assert result["name"] == "Test Rider"

    @pytest.mark.asyncio
    async def test_list_all_async(self):
        factory = _make_factory()
        session = factory.return_value.__aenter__.return_value
        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [
            {"id": 1, "name": "Rider A"},
            {"id": 2, "name": "Rider B"},
        ]
        session.execute.return_value = result_mock

        repo = AthleteRepository(session_factory=factory)
        result = await repo.list_all()
        assert len(result) == 2
