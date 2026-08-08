"""Tests for the PostgreSQL/SQLite dispatch mechanism in database.py."""

from __future__ import annotations

import importlib
import inspect
import os
from pathlib import Path
from unittest import mock

import pytest

import bike_analyzer.backend.db.database as db
from bike_analyzer.backend.db.database import (
    _INITIAL_DB_PATH,
    delete_itinerary,
    delete_ride,
    delete_stage,
    get_all_rides,
    get_athlete,
    get_athlete_by_email,
    get_athlete_history,
    get_athlete_metric_log,
    get_athletes_by_user,
    get_athlete_count_by_user,
    get_itinerary,
    get_latest_training_stress,
    get_ride,
    get_rides_by_athlete,
    get_stage,
    get_training_stress_days,
    list_itineraries,
    list_stages,
    log_athlete_metric,
    reorder_stages,
    save_athlete,
    save_athlete_snapshot,
    save_itinerary,
    save_metric,
    save_ride,
    save_stage,
    update_athlete,
    update_itinerary,
    update_ride,
    update_stage,
    upsert_training_stress_day,
)
from bike_analyzer.backend.db.postgres_athlete import has_postgres


@pytest.fixture
def _isolate_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_file)
    db.DB_PATH = db_file
    db._INITIAL_DB_PATH = db_file
    db.init_db()
    yield db
    db.DB_PATH = _INITIAL_DB_PATH
    db._INITIAL_DB_PATH = _INITIAL_DB_PATH


class TestHasPostgres:
    def test_has_postgres_false_without_url(self):
        os.environ["DATABASE_URL"] = ""
        assert has_postgres() is False

    def test_has_postgres_true_with_url(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        assert has_postgres() is True


class TestDispatchGuard:
    _MIGRATED_FUNCTIONS = [
        save_ride,
        get_ride,
        get_rides_by_athlete,
        get_all_rides,
        delete_ride,
        update_ride,
        save_metric,
        upsert_training_stress_day,
        get_training_stress_days,
        get_latest_training_stress,
        get_athlete,
        save_athlete,
        update_athlete,
        get_athlete_by_email,
        get_athlete_history,
        save_athlete_snapshot,
        get_athletes_by_user,
        get_athlete_count_by_user,
        log_athlete_metric,
        get_athlete_metric_log,
        save_itinerary,
        get_itinerary,
        list_itineraries,
        update_itinerary,
        delete_itinerary,
        save_stage,
        list_stages,
        get_stage,
        update_stage,
        delete_stage,
        reorder_stages,
    ]

    def test_dispatch_guard_present(self):
        for func in self._MIGRATED_FUNCTIONS:
            src = inspect.getsource(func)
            assert "has_postgres" in src, f"{func.__name__} missing has_postgres dispatch guard"


class TestSqliteRoundTrip:
    def test_sqlite_round_trip_after_dispatch(self, _isolate_db):
        athlete_id = db.save_athlete(
            {"name": "Test Rider", "age": 30, "weight_kg": 70.0, "tenant_id": 0},
            tenant_id=0,
        )
        assert athlete_id > 0

        ride_id = db.save_ride(
            {"athlete_id": athlete_id, "date": "2024-06-15", "distance_km": 35.0, "tenant_id": 0},
        )
        assert ride_id > 0

        athlete = db.get_athlete(athlete_id)
        assert athlete is not None
        assert athlete["name"] == "Test Rider"

        ride = db.get_ride(ride_id)
        assert ride is not None
        assert ride["distance_km"] == 35.0


class TestPostgresDispatch:
    def test_postgres_dispatch_called(self, monkeypatch):
        mock_pg_save_ride = mock.MagicMock(return_value=42)
        monkeypatch.setattr(
            "bike_analyzer.backend.db.postgres_rides.has_postgres",
            mock.MagicMock(return_value=True),
        )
        monkeypatch.setattr(
            "bike_analyzer.backend.db.postgres_rides.save_ride",
            mock_pg_save_ride,
        )

        db_file = str(Path(os.environ.get("TEMP", "/tmp")) / "bikemaster_test_dbs" / "dispatch_test.db")
        os.environ["DB_PATH"] = db_file
        db.DB_PATH = db_file
        db._INITIAL_DB_PATH = db_file
        db.init_db()

        ride_id = db.save_ride(
            {"athlete_id": 1, "date": "2024-06-15", "distance_km": 10.0, "tenant_id": 0},
        )
        assert ride_id == 42
        mock_pg_save_ride.assert_called_once()


class TestPostgresModules:
    def test_postgres_modules_importable(self):
        import bike_analyzer.backend.db.postgres_athlete
        import bike_analyzer.backend.db.postgres_rides
        import bike_analyzer.backend.db.postgres_itineraries
        import bike_analyzer.backend.db.postgres_db
