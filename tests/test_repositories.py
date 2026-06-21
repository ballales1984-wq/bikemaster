"""Tests for analytics repository modules using real database for coverage."""

import asyncio
import pytest

from bike_analyzer.backend.analytics.repositories.ride_repository import (
    RideRepository,
)
from bike_analyzer.backend.analytics.repositories.athlete_repository import (
    AthleteRepository,
)
from bike_analyzer.backend.analytics.repositories.training_stress_repository import (
    TrainingStressRepository,
)


@pytest.fixture
def db_path(tmp_path):
    p = str(tmp_path / "repo_test.db")
    import os
    os.environ["DB_PATH"] = p
    import bike_analyzer.backend.db.database as db_mod
    db_mod.DB_PATH = p
    db_mod.init_db()
    yield p
    import os as _os
    for suffix in ("", "-wal", "-shm"):
        _os.unlink(p + suffix) if _os.path.exists(p + suffix) else None


class TestRideRepositorySync:
    def test_save_and_get(self, db_path):
        repo = RideRepository()
        ride_id = asyncio.run(repo.save({
            "date": "2024-06-15",
            "distance_km": 25.0,
            "duration_minutes": 60,
        }))
        assert ride_id > 0

        ride = asyncio.run(repo.get_by_id(ride_id))
        assert ride["date"] == "2024-06-15"
        assert ride["distance_km"] == 25.0

    def test_get_by_athlete(self, db_path):
        repo = RideRepository()
        asyncio.run(repo.save({"athlete_id": 1, "date": "2024-06-15", "distance_km": 25.0}))
        rides = asyncio.run(repo.get_by_athlete(1))
        assert len(rides) >= 1

    def test_list_all(self, db_path):
        repo = RideRepository()
        asyncio.run(repo.save({"date": "2024-06-15", "distance_km": 25.0}))
        rides = asyncio.run(repo.list_all())
        assert len(rides) >= 1

    def test_delete(self, db_path):
        repo = RideRepository()
        ride_id = asyncio.run(repo.save({"date": "2024-06-15", "distance_km": 25.0}))
        result = asyncio.run(repo.delete(ride_id))
        assert result is True


class TestAthleteRepositorySync:
    def test_save_and_get(self, db_path):
        repo = AthleteRepository()
        athlete_id = asyncio.run(repo.save({"name": "Test Rider", "age": 30}))
        assert athlete_id > 0

        athlete = asyncio.run(repo.get_by_id(athlete_id))
        assert athlete["name"] == "Test Rider"

    def test_get_by_name(self, db_path):
        repo = AthleteRepository()
        asyncio.run(repo.save({"name": "FindMe", "age": 25}))
        athlete = asyncio.run(repo.get_by_name("FindMe"))
        assert athlete is not None
        assert athlete["name"] == "FindMe"

    def test_list_all(self, db_path):
        repo = AthleteRepository()
        asyncio.run(repo.save({"name": "A1"}))
        asyncio.run(repo.save({"name": "A2"}))
        athletes = asyncio.run(repo.list_all())
        assert len(athletes) >= 2


class TestTrainingStressRepositorySync:
    def test_upsert_and_get(self, db_path):
        repo = TrainingStressRepository()
        asyncio.run(repo.upsert_day(1, "2024-06-15", tss=100.0, atl=50.0, ctl=60.0, tsb=10.0))
        history = asyncio.run(repo.get_history(1, limit=7))
        assert len(history) >= 1

    def test_get_latest(self, db_path):
        repo = TrainingStressRepository()
        asyncio.run(repo.upsert_day(1, "2024-06-15", tss=100.0, atl=50.0, ctl=60.0, tsb=10.0))
        latest = asyncio.run(repo.get_latest(1))
        assert latest is not None
        assert latest["tss"] == 100.0
