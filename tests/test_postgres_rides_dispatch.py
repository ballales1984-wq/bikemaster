"""Tests for the PostgreSQL dispatch layer in db/postgres_rides.py.

These tests exercise the sync PostgreSQL code path *without* a real database by
mocking ``psycopg2`` at the ``_connect`` boundary. They assert that:

* ``has_postgres()`` flips the dispatch on when ``DATABASE_URL`` is set.
* Each ``database.py`` function delegates to its PostgreSQL twin once dispatched.
* The generated SQL (INSERT/UPDATE/SELECT/RETURNING/ON CONFLICT) and return
  shapes match the SQLite implementation, so the two stores stay
  swap-compatible.

No network and no psycopg2 driver are required:
``postgres_rides._connect`` is replaced with a factory returning a
:class:`MagicMock` backed cursor.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

import bike_analyzer.backend.db.database as db
from bike_analyzer.backend.db import postgres_rides as pr


def _pg_url():
    os.environ["DATABASE_URL"] = "postgresql://u:p@db.internal:5432/bikemaster"


def _clear_pg_url():
    os.environ.pop("DATABASE_URL", None)


def _mock_conn():
    conn = MagicMock(name="pg-conn")
    cur = MagicMock(name="pg-cur")
    cm = conn.cursor.return_value
    cm.__enter__.return_value = cur
    cm.__exit__.return_value = False
    return conn, cur


@pytest.fixture(autouse=True)
def _pg_env():
    _pg_url()
    yield
    _clear_pg_url()


# --- rides ---------------------------------------------------------------


def test_save_ride_pg_inserts_and_returns_id(monkeypatch):
    conn, cur = _mock_conn()
    cur.fetchone.return_value = {"id": 42}
    monkeypatch.setattr(pr, "_connect", lambda: conn)

    new_id = db.save_ride(
        {
            "athlete_id": 1,
            "date": "2026-08-01",
            "distance_km": 30.0,
            "duration_minutes": 90,
            "activity_type": "ride",
        }
    )

    assert new_id == 42
    sqls = [str(c.args[0]) for c in cur.execute.call_args_list]
    assert any("INSERT INTO rides" in s and "RETURNING id" in s for s in sqls)


def test_save_ride_pg_dedup_returns_existing(monkeypatch):
    conn, cur = _mock_conn()
    # _find_existing_external_ride finds an id -> early return, no INSERT
    cur.fetchone.return_value = {"id": 7}
    monkeypatch.setattr(pr, "_connect", lambda: conn)

    existing_id = db.save_ride(
        {
            "athlete_id": 1,
            "date": "2026-08-01",
            "external_source": "strava",
            "external_id": "1001",
            "distance_km": 30.0,
        }
    )

    assert existing_id == 7
    sqls = [str(c.args[0]) for c in cur.execute.call_args_list]
    assert any("SELECT id FROM rides WHERE external_source" in s for s in sqls)
    assert not any("INSERT INTO rides" in s for s in sqls)


def test_get_ride_pg_found(monkeypatch):
    conn, cur = _mock_conn()
    cur.fetchone.return_value = {"id": 1, "athlete_id": 1, "date": "2026-08-01",
                                "distance_km": 0, "duration_minutes": 0,
                                "avg_speed_kmh": 0, "weight_kg": 70, "calories": 0,
                                "heart_rate_avg": None, "elevation_gain_m": None,
                                "gps_points": None, "created_at": None,
                                "external_source": None, "external_id": None,
                                "title": None, "tenant_id": 0,
                                "activity_type": "ride", "is_official": True,
                                "source": "manual"}
    monkeypatch.setattr(pr, "_connect", lambda: conn)

    ride = db.get_ride(1, tenant_id=0)
    assert ride is not None
    assert ride["id"] == 1
    assert ride["is_official"] is True
    sent = str(cur.execute.call_args.args[0])
    assert "SELECT * FROM rides WHERE id = %s AND tenant_id = %s" in sent


def test_get_ride_pg_not_found(monkeypatch):
    conn, cur = _mock_conn()
    cur.fetchone.return_value = None
    monkeypatch.setattr(pr, "_connect", lambda: conn)

    assert db.get_ride(999) is None


def test_get_rides_by_athlete_pg(monkeypatch):
    conn, cur = _mock_conn()
    cur.fetchall.return_value = [
        {"id": 1, "athlete_id": 1, "date": "2026-08-01",
         "distance_km": 10, "duration_minutes": 30, "avg_speed_kmh": 20,
         "weight_kg": 70, "calories": 100, "heart_rate_avg": None,
         "elevation_gain_m": None, "gps_points": None, "created_at": None,
         "external_source": None, "external_id": None, "title": None,
         "tenant_id": 0, "activity_type": "ride", "is_official": True,
         "source": "manual"},
    ]
    monkeypatch.setattr(pr, "_connect", lambda: conn)

    rides = db.get_rides_by_athlete(1, tenant_id=0)
    assert len(rides) == 1
    assert rides[0]["id"] == 1
    sent = str(cur.execute.call_args.args[0])
    assert "WHERE athlete_id = %s AND tenant_id = %s" in sent
    assert "ORDER BY date ASC, id ASC" in sent


def test_get_all_rides_pg_filters(monkeypatch):
    conn, cur = _mock_conn()
    cur.fetchall.return_value = []
    monkeypatch.setattr(pr, "_connect", lambda: conn)

    db.get_all_rides(athlete_id=1, tenant_id=0)
    sent = str(cur.execute.call_args.args[0])
    assert "WHERE athlete_id = %s AND tenant_id = %s" in sent


def test_delete_ride_pg(monkeypatch):
    conn, cur = _mock_conn()
    cur.rowcount = 1
    monkeypatch.setattr(pr, "_connect", lambda: conn)

    assert db.delete_ride(5, tenant_id=0) is True
    sent = str(cur.execute.call_args.args[0])
    assert "DELETE FROM rides WHERE id = %s AND tenant_id = %s" in sent


def test_update_ride_pg(monkeypatch):
    conn, cur = _mock_conn()
    cur.rowcount = 1
    monkeypatch.setattr(pr, "_connect", lambda: conn)

    assert db.update_ride(5, {"distance_km": 42.0}, tenant_id=0) is True
    sent = str(cur.execute.call_args.args[0])
    assert "UPDATE rides SET" in sent
    assert "WHERE id = %s AND tenant_id = %s" in sent


# --- metrics -------------------------------------------------------------


def test_save_metric_pg(monkeypatch):
    conn, cur = _mock_conn()
    cur.fetchone.return_value = {"id": 99}
    monkeypatch.setattr(pr, "_connect", lambda: conn)

    metric_id = db.save_metric({"athlete_id": 1, "ride_id": 3, "fatigue_score": 7.5}, tenant_id=0)
    assert metric_id == 99
    sent = str(cur.execute.call_args.args[0])
    assert "INSERT INTO metrics" in sent
    assert "RETURNING id" in sent


def test_get_metrics_by_athlete_pg(monkeypatch):
    conn, cur = _mock_conn()
    cur.fetchall.return_value = [
        {"id": 1, "athlete_id": 1, "ride_id": 3, "fatigue_score": 7.5,
         "recovery_hours": 12.0, "calories_per_km": 30.0, "efficiency_score": 0.85,
         "created_at": "2026-08-01T00:00:00", "tenant_id": 0},
    ]
    monkeypatch.setattr(pr, "_connect", lambda: conn)

    metrics = db.get_metrics_by_athlete(1, tenant_id=0)
    assert len(metrics) == 1
    assert metrics[0]["fatigue_score"] == 7.5
    sent = str(cur.execute.call_args.args[0])
    assert "FROM metrics WHERE athlete_id = %s AND tenant_id = %s" in sent
    assert "ORDER BY created_at ASC" in sent


# --- training stress -----------------------------------------------------


def test_upsert_training_stress_day_pg(monkeypatch):
    conn, cur = _mock_conn()
    monkeypatch.setattr(pr, "_connect", lambda: conn)

    db.upsert_training_stress_day(1, "2026-08-01", 50.0, 45.0, 40.0, -5.0, tenant_id=0)
    sent = str(cur.execute.call_args.args[0])
    assert "INSERT INTO training_stress_days" in sent
    assert "ON CONFLICT(athlete_id, date) DO UPDATE SET" in sent
    params = cur.execute.call_args.args[1]
    assert params[0] == 1 and params[1] == "2026-08-01"


def test_get_training_stress_days_pg(monkeypatch):
    conn, cur = _mock_conn()
    cur.fetchall.return_value = [
        {"date": "2026-08-02", "tss": 50.0, "atl": 45.0, "ctl": 40.0, "tsb": -5.0},
        {"date": "2026-08-01", "tss": 30.0, "atl": 28.0, "ctl": 25.0, "tsb": -3.0},
    ]
    monkeypatch.setattr(pr, "_connect", lambda: conn)

    days = db.get_training_stress_days(1, limit=90, tenant_id=0)
    assert len(days) == 2
    assert days[0]["date"] == "2026-08-02"
    assert days[0]["tsb"] == -5.0
    sent = str(cur.execute.call_args.args[0])
    assert "FROM training_stress_days WHERE athlete_id = %s AND tenant_id = %s" in sent


def test_get_latest_training_stress_pg(monkeypatch):
    conn, cur = _mock_conn()
    cur.fetchone.return_value = {"date": "2026-08-02", "tss": 50.0, "atl": 45.0, "ctl": 40.0, "tsb": -5.0}
    monkeypatch.setattr(pr, "_connect", lambda: conn)

    latest = db.get_latest_training_stress(1, tenant_id=0)
    assert latest is not None
    assert latest["date"] == "2026-08-02"
    sent = str(cur.execute.call_args.args[0])
    assert "ORDER BY date DESC LIMIT 1" in sent


def test_recalculate_training_stress_uses_pg_dispatch(monkeypatch):
    """recalculate calls get_rides_by_athlete + upsert_training_stress_day,
    both of which must be dispatched when DATABASE_URL is set."""
    conn, cur = _mock_conn()
    cur.fetchall.return_value = [
        {"id": 1, "athlete_id": 1, "date": "2026-08-01",
         "distance_km": 20.0, "duration_minutes": 60.0, "avg_speed_kmh": 20.0,
         "weight_kg": 70, "calories": 400, "heart_rate_avg": None,
         "elevation_gain_m": None, "gps_points": None, "created_at": None,
         "external_source": None, "external_id": None, "title": None,
         "tenant_id": 0, "activity_type": "ride", "is_official": True,
         "source": "manual"},
    ]
    monkeypatch.setattr(pr, "_connect", lambda: conn)

    db.recalculate_training_stress_for_athlete(1, ftp=250.0, tenant_id=0)
    sqls = [str(c.args[0]) for c in cur.execute.call_args_list]
    assert any("SELECT * FROM rides WHERE athlete_id = %s" in s for s in sqls)
    assert any("INSERT INTO training_stress_days" in s for s in sqls)
