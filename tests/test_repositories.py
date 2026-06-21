"""Tests for analytics repository modules."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from bike_analyzer.backend.analytics.repositories.ride_repository import (
    RideRepository,
)
from bike_analyzer.backend.analytics.repositories.training_stress_repository import (
    TrainingStressRepository,
)
from bike_analyzer.backend.db.models import RideModel


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


class TestRideRepository:
    def test_table_property(self):
        repo = RideRepository()
        assert repo._table is RideModel

    def test_constructor_defaults(self):
        repo = RideRepository()
        assert repo._session_factory is None
        assert repo._sync_conn is None

    @pytest.mark.asyncio
    async def test_save_async(self):
        factory = _make_factory()
        session = factory.return_value.__aenter__.return_value
        result_mock = MagicMock()
        result_mock.scalar_one.return_value = 42
        session.execute.return_value = result_mock

        repo = RideRepository(session_factory=factory)
        ride_id = await repo.save({"date": "2024-06-15", "distance_km": 25.0})
        assert ride_id == 42

    @pytest.mark.asyncio
    async def test_get_by_id_async_found(self):
        factory = _make_factory()
        session = factory.return_value.__aenter__.return_value
        mappings_mock = MagicMock()
        mappings_mock.first.return_value = {"id": 1, "gps_points": None}
        result_mock = MagicMock()
        result_mock.mappings.return_value = mappings_mock
        session.execute.return_value = result_mock

        repo = RideRepository(session_factory=factory)
        result = await repo.get_by_id(1)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_get_by_id_async_not_found(self):
        factory = _make_factory()
        session = factory.return_value.__aenter__.return_value
        mappings_mock = MagicMock()
        mappings_mock.first.return_value = None
        result_mock = MagicMock()
        result_mock.mappings.return_value = mappings_mock
        session.execute.return_value = result_mock

        repo = RideRepository(session_factory=factory)
        result = await repo.get_by_id(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_athlete_async(self):
        factory = _make_factory()
        session = factory.return_value.__aenter__.return_value
        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [
            {"id": 1, "date": "2024-06-15"},
        ]
        session.execute.return_value = result_mock

        repo = RideRepository(session_factory=factory)
        result = await repo.get_by_athlete(1)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_all_async(self):
        factory = _make_factory()
        session = factory.return_value.__aenter__.return_value
        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [{"id": 1}]
        session.execute.return_value = result_mock

        repo = RideRepository(session_factory=factory)
        result = await repo.list_all()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_delete_async_true(self):
        factory = _make_factory()
        session = factory.return_value.__aenter__.return_value
        result_mock = MagicMock()
        result_mock.rowcount = 1
        session.execute.return_value = result_mock

        repo = RideRepository(session_factory=factory)
        result = await repo.delete(1)
        assert result is True


class TestTrainingStressRepository:
    def test_constructor_defaults(self):
        repo = TrainingStressRepository()
        assert repo._session_factory is None

    def test_upsert_sync_falls_back(self):
        repo = TrainingStressRepository()
        with pytest.raises(ModuleNotFoundError):
            asyncio.run(repo.upsert_day(1, "2024-06-15", 100.0, 50.0, 60.0, 10.0))

    def test_get_history_sync_falls_back(self):
        repo = TrainingStressRepository()
        with pytest.raises(ModuleNotFoundError):
            asyncio.run(repo.get_history(1))

    def test_get_latest_sync_falls_back(self):
        repo = TrainingStressRepository()
        with pytest.raises(ModuleNotFoundError):
            asyncio.run(repo.get_latest(1))
