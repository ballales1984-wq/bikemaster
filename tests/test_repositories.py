"""Tests for analytics repositories."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bike_analyzer.backend.analytics.repositories.athlete_repository import AthleteRepository
from bike_analyzer.backend.analytics.repositories.fitness_state_repository import FitnessStateRepository
from bike_analyzer.backend.analytics.repositories.ride_repository import RideRepository
from bike_analyzer.backend.analytics.repositories.training_stress_repository import TrainingStressRepository


class TestAthleteRepository:
    def test_init_default(self):
        repo = AthleteRepository()
        assert repo._sync_conn is None

    def test_init_with_sync_conn(self):
        conn = MagicMock()
        repo = AthleteRepository(sync_conn=conn)
        assert repo._sync_conn is conn

    def test_init_with_session_factory(self):
        factory = MagicMock()
        repo = AthleteRepository(session_factory=factory)
        assert repo._session_factory is factory

    def test_save_sync_via_conn(self):
        conn = MagicMock()
        conn.save_athlete.return_value = 1
        repo = AthleteRepository(sync_conn=conn)
        import asyncio
        result = asyncio.run(repo.save({"name": "Test"}, athlete_id=1))
        assert result == 1

    def test_get_by_id_sync_via_conn(self):
        conn = MagicMock()
        conn.get_athlete.return_value = {"id": 1, "name": "Test"}
        repo = AthleteRepository(sync_conn=conn)
        import asyncio
        result = asyncio.run(repo.get_by_id(1))
        assert result == {"id": 1, "name": "Test"}

    def test_get_by_name_sync_via_conn(self):
        conn = MagicMock()
        conn.get_athlete_by_name.return_value = {"id": 1, "name": "Test"}
        repo = AthleteRepository(sync_conn=conn)
        import asyncio
        result = asyncio.run(repo.get_by_name("Test"))
        assert result["name"] == "Test"

    def test_list_all_sync_via_conn(self):
        conn = MagicMock()
        conn.get_all_athletes.return_value = [{"id": 1}, {"id": 2}]
        repo = AthleteRepository(sync_conn=conn)
        import asyncio
        result = asyncio.run(repo.list_all())
        assert len(result) == 2


class TestRideRepository:
    def test_init_default(self):
        repo = RideRepository()
        assert repo._sync_conn is None

    def test_save_sync_via_conn(self):
        conn = MagicMock()
        conn.save_ride.return_value = 1
        repo = RideRepository(sync_conn=conn)
        import asyncio
        result = asyncio.run(repo.save({"distance_km": 25.0}))
        assert result == 1

    def test_get_by_id_sync_via_conn(self):
        conn = MagicMock()
        conn.get_ride.return_value = {"id": 1, "distance_km": 25.0}
        repo = RideRepository(sync_conn=conn)
        import asyncio
        result = asyncio.run(repo.get_by_id(1))
        assert result["distance_km"] == 25.0

    def test_list_all_sync_via_conn(self):
        conn = MagicMock()
        conn.get_all_rides.return_value = [{"id": 1}, {"id": 2}]
        repo = RideRepository(sync_conn=conn)
        import asyncio
        result = asyncio.run(repo.list_all())
        assert len(result) == 2


class TestFitnessStateRepository:
    def test_requires_session_factory(self):
        repo = FitnessStateRepository()
        import asyncio
        with pytest.raises(RuntimeError, match="Async session factory required"):
            asyncio.run(repo.save({"athlete_id": 1}))

    def test_save_async(self):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 1
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        factory = MagicMock(return_value=mock_session)
        repo = FitnessStateRepository(session_factory=factory)
        import asyncio
        result = asyncio.run(repo.save({"athlete_id": 1, "fitness": 85.0}))
        assert result == 1


class TestTrainingStressRepository:
    def test_init_default(self):
        repo = TrainingStressRepository()
        assert repo._session_factory is None

    def test_table_property(self):
        repo = TrainingStressRepository()
        table = repo._table
        assert table is not None
        assert table.name == "training_stress_days"

    def test_upsert_sync_via_conn(self):
        conn = MagicMock()
        repo = TrainingStressRepository(sync_conn=conn)
        import asyncio
        asyncio.run(repo.upsert_day(1, "2024-06-15", 100.0, 80.0, 90.0, 10.0))
        conn.upsert_training_stress_day.assert_called_once_with(1, "2024-06-15", 100.0, 80.0, 90.0, 10.0, 0)

    def test_get_history_sync_via_conn(self):
        conn = MagicMock()
        conn.get_training_stress_days.return_value = [{"date": "2024-06-15", "tss": 100.0}]
        repo = TrainingStressRepository(sync_conn=conn)
        import asyncio
        result = asyncio.run(repo.get_history(1))
        assert len(result) == 1
        assert result[0]["tss"] == 100.0

    def test_get_latest_sync_via_conn(self):
        conn = MagicMock()
        conn.get_latest_training_stress.return_value = {"date": "2024-06-15", "tss": 100.0}
        repo = TrainingStressRepository(sync_conn=conn)
        import asyncio
        result = asyncio.run(repo.get_latest(1))
        assert result["tss"] == 100.0

    def test_row_to_day(self):
        repo = TrainingStressRepository()
        row = {"date": "2024-06-15", "tss": 100.0, "atl": 80.0, "ctl": 90.0, "tsb": 10.0}
        day = repo._row_to_day(row)
        assert day == {"date": "2024-06-15", "tss": 100.0, "atl": 80.0, "ctl": 90.0, "tsb": 10.0}
