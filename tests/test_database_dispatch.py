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
    delete_athlete,
    delete_itinerary,
    delete_ride,
    delete_stage,
    delete_user,
    get_all_rides,
    get_all_users,
    get_athlete,
    get_athlete_by_email,
    get_athlete_count_by_user,
    get_athlete_history,
    get_athlete_metric_log,
    get_athletes_by_user,
    get_itinerary,
    get_latest_training_stress,
    get_metrics_by_athlete,
    get_ride,
    get_rides_by_athlete,
    get_stage,
    get_training_stress_days,
    get_user_by_id,
    get_user_by_username,
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
    save_user,
    update_athlete,
    update_itinerary,
    update_ride,
    update_stage,
    update_user,
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
        get_metrics_by_athlete,
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
        delete_athlete,
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
        save_user,
        get_user_by_username,
        get_user_by_id,
        get_all_users,
        update_user,
        delete_user,
    ]

    def test_dispatch_guard_present(self):
        """Every migrated function must carry the ``@pg_dispatch`` decorator
        (single source of truth) rather than an inline ``has_postgres`` block."""
        from bike_analyzer.backend.db.dispatch import MIGRATED_FUNCTIONS

        migrated_names = set(MIGRATED_FUNCTIONS)
        for func in self._MIGRATED_FUNCTIONS:
            assert getattr(func, "_dispatch_source", None) == "pg_dispatch", (
                f"{func.__name__} is missing the @pg_dispatch decorator"
            )
            assert func.__name__ in migrated_names, (
                f"{func.__name__} not registered in MIGRATED_FUNCTIONS"
            )
        # registry must cover every function that used to carry an inline guard
        assert len(self._MIGRATED_FUNCTIONS) == len(migrated_names) == 39


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

    def test_sqlite_users_round_trip(self, _isolate_db):
        user_id = db.save_user(
            {
                "username": "testuser",
                "email": "test@example.com",
                "password_hash": "hashed",
                "is_admin": True,
                "is_client": False,
                "is_active": True,
            }
        )
        assert user_id > 0

        user = db.get_user_by_username("testuser")
        assert user is not None
        assert user["email"] == "test@example.com"
        assert user["password_hash"] == "hashed"

        user = db.get_user_by_id(user_id)
        assert user is not None
        assert user["username"] == "testuser"

        users = db.get_all_users()
        assert len(users) == 1
        assert users[0]["username"] == "testuser"

        updated = db.update_user(user_id, {"email": "new@example.com", "is_admin": False})
        assert updated is not None
        assert updated["email"] == "new@example.com"
        assert updated["is_admin"] is False

        assert db.delete_user(user_id) is True
        assert db.get_user_by_id(user_id) is None


class TestPostgresDispatch:
    def test_postgres_dispatch_called(self, monkeypatch):
        # The centralized dispatch reads DATABASE_URL at call time (dispatch.is_postgres),
        # so set the env var instead of patching the now-defunct per-module has_postgres.
        from bike_analyzer.backend.db import dispatch

        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        assert dispatch.is_postgres() is True

        mock_pg_save_ride = mock.MagicMock(return_value=42)
        monkeypatch.setattr(
            "bike_analyzer.backend.db.postgres_rides.save_ride",
            mock_pg_save_ride,
        )
        mock_pg_seed_nutrition = mock.MagicMock(return_value=None)
        monkeypatch.setattr(
            "bike_analyzer.backend.db.postgres_nutrition.seed_nutrition_food_items",
            mock_pg_seed_nutrition,
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

    def test_postgres_dispatch_users(self, monkeypatch):
        from bike_analyzer.backend.db import dispatch

        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
        assert dispatch.is_postgres() is True

        mock_pg_save_user = mock.MagicMock(return_value=42)
        monkeypatch.setattr(
            "bike_analyzer.backend.db.postgres_users.save_user",
            mock_pg_save_user,
        )
        mock_pg_seed_nutrition = mock.MagicMock(return_value=None)
        monkeypatch.setattr(
            "bike_analyzer.backend.db.postgres_nutrition.seed_nutrition_food_items",
            mock_pg_seed_nutrition,
        )

        db_file = str(Path(os.environ.get("TEMP", "/tmp")) / "bikemaster_test_dbs" / "dispatch_users.db")
        os.environ["DB_PATH"] = db_file
        db.DB_PATH = db_file
        db._INITIAL_DB_PATH = db_file
        db.init_db()

        user_id = db.save_user({"username": "pguser"})
        assert user_id == 42
        mock_pg_save_user.assert_called_once()

    def test_sqlite_used_when_no_postgres(self, _isolate_db, monkeypatch):
        from bike_analyzer.backend.db import dispatch

        monkeypatch.setenv("DATABASE_URL", "")
        assert dispatch.is_postgres() is False
        # No DATABASE_URL -> falls through to the SQLite implementation
        rid = db.save_ride({"athlete_id": 1, "date": "2024-06-15", "distance_km": 5.0, "tenant_id": 0})
        assert rid > 0


class TestPostgresModules:
    def test_postgres_modules_importable(self):
        import bike_analyzer.backend.db.postgres_athlete
        import bike_analyzer.backend.db.postgres_db
        import bike_analyzer.backend.db.postgres_itineraries
        import bike_analyzer.backend.db.postgres_rides
