"""Tests for PostgreSQL dispatch on rides / metrics / training stress days."""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest

from bike_analyzer.backend.db.dispatch import pg_dispatch
from bike_analyzer.backend.db.repositories import (
    ride_repository,
    training_stress_repository,
)
from bike_analyzer.backend.db import database


def _dispatch_targets(module):
    return {
        name
        for name in dir(module)
        if hasattr(getattr(module, name), "_pg_module")
        and getattr(module, name)._pg_module == "bike_analyzer.backend.db.postgres_rides"
    }


def test_ride_repository_functions_have_postgres_dispatch():
    expected = {
        "save_ride",
        "get_ride",
        "get_rides_by_athlete",
        "get_all_rides",
        "delete_ride",
        "update_ride",
    }
    assert expected.issubset(_dispatch_targets(ride_repository))


def test_training_stress_repository_functions_have_postgres_dispatch():
    expected = {
        "upsert_training_stress_day",
        "get_training_stress_days",
        "get_latest_training_stress",
    }
    assert expected.issubset(_dispatch_targets(training_stress_repository))


def test_database_save_metric_has_postgres_dispatch():
    assert hasattr(database.save_metric, "_pg_module")
    assert database.save_metric._pg_module == "bike_analyzer.backend.db.postgres_rides"


def test_database_get_metrics_by_athlete_has_postgres_dispatch():
    assert hasattr(database.get_metrics_by_athlete, "_pg_module")
    assert database.get_metrics_by_athlete._pg_module == "bike_analyzer.backend.db.postgres_rides"


def test_dispatch_calls_postgres_when_enabled():
    fake_pg = MagicMock()
    fake_pg.save_metric.return_value = 42

    with patch("bike_analyzer.backend.db.dispatch.is_postgres", return_value=True), patch(
        "importlib.import_module", return_value=fake_pg
    ) as mock_import:
        result = database.save_metric({"athlete_id": 1})
        assert result == 42
        fake_pg.save_metric.assert_called_once()
        mock_import.assert_called_once_with("bike_analyzer.backend.db.postgres_rides")


def test_dispatch_falls_back_to_sqlite_when_disabled():
    fake_conn = MagicMock()
    fake_cur = MagicMock()
    fake_conn.cursor.return_value = fake_cur
    fake_conn.__enter__ = MagicMock(return_value=fake_conn)
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_cur.lastrowid = 7

    with patch("bike_analyzer.backend.db.dispatch.is_postgres", return_value=False), patch(
        "bike_analyzer.backend.db.database.get_db_connection",
        return_value=fake_conn,
    ):
        result = database.save_metric({"athlete_id": 1})
        assert result == 7
        fake_cur.execute.assert_called_once()


def test_postgres_save_ride_calls_ensure_tables():
    fake_conn = MagicMock()
    fake_cur = MagicMock()
    fake_conn.cursor.return_value = fake_cur
    fake_cur.__enter__ = MagicMock(return_value=fake_cur)
    fake_cur.__exit__ = MagicMock(return_value=False)
    fake_cur.fetchone.return_value = {"id": 5}

    mod = importlib.import_module("bike_analyzer.backend.db.postgres_rides")
    with patch("bike_analyzer.backend.db.dispatch.is_postgres", return_value=True), patch.object(
        mod, "_ensure_tables"
    ) as mock_ensure, patch.object(mod, "_connect", return_value=fake_conn), patch.object(
        mod, "_safe_close"
    ):
        result = mod.save_ride({"date": "2024-01-01", "distance_km": 10})
        assert result == 5
        mock_ensure.assert_called_once_with(fake_conn)


def test_postgres_upsert_training_stress_day_is_idempotent():
    fake_conn = MagicMock()
    fake_cur = MagicMock()
    fake_conn.cursor.return_value = fake_cur
    fake_cur.__enter__ = MagicMock(return_value=fake_cur)
    fake_cur.__exit__ = MagicMock(return_value=False)

    mod = importlib.import_module("bike_analyzer.backend.db.postgres_rides")
    with patch("bike_analyzer.backend.db.dispatch.is_postgres", return_value=True), patch.object(
        mod, "_ensure_tables"
    ), patch.object(mod, "_connect", return_value=fake_conn), patch.object(mod, "_safe_close"):
        mod.upsert_training_stress_day(
            athlete_id=1, date="2024-01-01", tss=50.0, atl=40.0, ctl=60.0, tsb=20.0
        )
        assert fake_conn.commit.called


def test_postgres_get_training_stress_days_returns_desc():
    fake_conn = MagicMock()
    fake_cur = MagicMock()
    fake_conn.cursor.return_value = fake_cur
    fake_cur.__enter__ = MagicMock(return_value=fake_cur)
    fake_cur.__exit__ = MagicMock(return_value=False)
    fake_cur.fetchall.return_value = [
        {"date": "2024-01-02", "tss": 60, "atl": 45, "ctl": 65, "tsb": 20},
        {"date": "2024-01-01", "tss": 50, "atl": 40, "ctl": 60, "tsb": 20},
    ]

    mod = importlib.import_module("bike_analyzer.backend.db.postgres_rides")
    with patch("bike_analyzer.backend.db.dispatch.is_postgres", return_value=True), patch.object(
        mod, "_ensure_tables"
    ), patch.object(mod, "_connect", return_value=fake_conn), patch.object(mod, "_safe_close"):
        rows = mod.get_training_stress_days(athlete_id=1, limit=10)
        assert fake_cur.execute.called
        assert len(rows) == 2
        assert rows[0]["date"] == "2024-01-02"
        assert rows[1]["date"] == "2024-01-01"


def test_postgres_save_metric_returns_id():
    fake_conn = MagicMock()
    fake_cur = MagicMock()
    fake_conn.cursor.return_value = fake_cur
    fake_cur.__enter__ = MagicMock(return_value=fake_cur)
    fake_cur.__exit__ = MagicMock(return_value=False)
    fake_cur.fetchone.return_value = {"id": 99}

    mod = importlib.import_module("bike_analyzer.backend.db.postgres_rides")
    with patch("bike_analyzer.backend.db.dispatch.is_postgres", return_value=True), patch.object(
        mod, "_ensure_tables"
    ), patch.object(mod, "_connect", return_value=fake_conn), patch.object(mod, "_safe_close"):
        result = mod.save_metric(
            {"athlete_id": 1, "ride_id": 10, "fatigue_score": 3.5, "recovery_hours": 12.0}
        )
        assert result == 99
        assert fake_conn.commit.called
