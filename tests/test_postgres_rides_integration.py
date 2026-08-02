"""Integration tests for the PostgreSQL rides/metrics/stress dispatch layer.

These tests run against a *real* PostgreSQL instance (local Docker container)
when reachable; they are skipped otherwise. They verify the end-to-end pg code
path — ``database.py`` dispatch guards + ``postgres_rides`` implementations —
including schema bootstrapping, round-trip persistence, upserts and the
``recalculate_training_stress_for_athlete`` pipeline.

The connection string used is::

    postgresql://postgres:postgres@localhost:5432/bikemaster
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import psycopg2
import pytest

import bike_analyzer.backend.db.database as db
from bike_analyzer.backend.db import postgres_rides as pr

PG_URL = "postgresql://postgres:postgres@localhost:5432/bikemaster"

_TABLES = ["rides", "metrics", "training_stress_days"]


def _pg_reachable() -> bool:
    try:
        conn = psycopg2.connect(PG_URL)
        conn.close()
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.fixture(autouse=True)
def _pg_env(monkeypatch):
    """Point the dispatch layer at the local PostgreSQL for the duration of each test."""
    if not _pg_reachable():
        pytest.skip("PostgreSQL not reachable at localhost:5432")
    monkeypatch.setenv("DATABASE_URL", PG_URL)
    yield


@pytest.fixture()
def clean_pg(_pg_env):
    """Drop + recreate the rides/metrics/stress tables for a deterministic state."""
    conn = psycopg2.connect(PG_URL)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for t in _TABLES:
                cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    finally:
        conn.close()

    # First call bootstraps the schema via _ensure_tables (best-effort).
    db.save_ride(
        {
            "athlete_id": 1,
            "date": "1970-01-01",
            "distance_km": 0,
            "duration_minutes": 0,
            "weight_kg": 70,
            "calories": 0,
            "activity_type": "ride",
        }
    )

    conn = psycopg2.connect(PG_URL)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for t in _TABLES:
                cur.execute(f"DELETE FROM {t}")
    finally:
        conn.close()
    yield

    conn = psycopg2.connect(PG_URL)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for t in _TABLES:
                cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    finally:
        conn.close()


def _ride(ride_id, **over):
    return {
        "athlete_id": 1,
        "tenant_id": 0,
        "date": "2026-08-01T06:00:00+00:00",
        "distance_km": 40.0,
        "duration_minutes": 120.0,
        "avg_speed_kmh": 20.0,
        "weight_kg": 72.0,
        "calories": 800.0,
        "heart_rate_avg": 150.0,
        "elevation_gain_m": 200.0,
        "gps_points": [{"lat": 45.0, "lng": 9.0}],
        "external_source": None,
        "external_id": None,
        "title": "Morning ride",
        "activity_type": "ride",
        "is_official": True,
        "source": "manual",
        **over,
    }


class TestRidesIntegration:
    def test_save_and_get_ride_roundtrip(self, clean_pg):
        ride = _ride(None)
        rid = db.save_ride(ride)
        assert rid > 0

        fetched = db.get_ride(rid, tenant_id=0)
        assert fetched["id"] == rid
        assert fetched["athlete_id"] == 1
        assert fetched["distance_km"] == 40.0
        assert fetched["weight_kg"] == 72.0
        assert fetched["is_official"] is True
        assert fetched["gps_points"] == [{"lat": 45.0, "lng": 9.0}]
        assert fetched["tenant_id"] == 0

    def test_save_ride_dedup_by_external_identity(self, clean_pg):
        r = _ride(None, external_source="strava", external_id="abc123")
        rid1 = db.save_ride(r)
        rid2 = db.save_ride(r)
        assert rid1 == rid2

    def test_get_rides_by_athlete_orders_oldest_first(self, clean_pg):
        db.save_ride(_ride(None, date="2026-08-02T06:00:00+00:00"))
        db.save_ride(_ride(None, date="2026-08-01T06:00:00+00:00"))
        rides = db.get_rides_by_athlete(1, tenant_id=0)
        assert len(rides) == 2
        assert rides[0]["date"] <= rides[1]["date"]

    def test_get_all_rides_filters_by_athlete(self, clean_pg):
        db.save_ride(_ride(None))
        db.save_ride(_ride(None, athlete_id=2))
        assert len(db.get_all_rides(athlete_id=1, tenant_id=0)) == 1
        assert len(db.get_all_rides(athlete_id=2, tenant_id=0)) == 1

    def test_update_ride(self, clean_pg):
        rid = db.save_ride(_ride(None))
        ok = db.update_ride(rid, {"distance_km": 99.0}, tenant_id=0)
        assert ok is True
        fetched = db.get_ride(rid, tenant_id=0)
        assert fetched["distance_km"] == 99.0

    def test_update_ride_wrong_tenant_no_effect(self, clean_pg):
        rid = db.save_ride(_ride(None))
        ok = db.update_ride(rid, {"distance_km": 99.0}, tenant_id=999)
        assert ok is False
        fetched = db.get_ride(rid, tenant_id=0)
        assert fetched["distance_km"] == 40.0

    def test_delete_ride(self, clean_pg):
        rid = db.save_ride(_ride(None))
        assert db.delete_ride(rid, tenant_id=0) is True
        assert db.get_ride(rid, tenant_id=0) is None

    def test_delete_ride_wrong_tenant_no_effect(self, clean_pg):
        rid = db.save_ride(_ride(None))
        assert db.delete_ride(rid, tenant_id=999) is False
        assert db.get_ride(rid, tenant_id=0) is not None


class TestMetricIntegration:
    def test_save_metric_roundtrip(self, clean_pg):
        rid = db.save_ride(_ride(None))
        mid = db.save_metric(
            {"athlete_id": 1, "ride_id": rid, "fatigue_score": 7.5,
             "recovery_hours": 48.0, "calories_per_km": 20.0,
             "efficiency_score": 9.0, "tenant_id": 0},
            tenant_id=0,
        )
        assert mid > 0

        conn = psycopg2.connect(PG_URL)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT fatigue_score, recovery_hours FROM metrics WHERE id = %s", (mid,))
                row = cur.fetchone()
        finally:
            conn.close()
        assert row[0] == 7.5
        assert row[1] == 48.0


class TestTrainingStressIntegration:
    def test_upsert_and_get_training_stress(self, clean_pg):
        db.upsert_training_stress_day(1, "2026-08-01", 50.0, 45.0, 40.0, -5.0, tenant_id=0)
        db.upsert_training_stress_day(1, "2026-08-02", 60.0, 50.0, 42.0, -8.0, tenant_id=0)

        days = db.get_training_stress_days(1, limit=90, tenant_id=0)
        assert len(days) == 2
        assert days[0]["date"] == "2026-08-02"
        assert days[0]["tss"] == 60.0

        latest = db.get_latest_training_stress(1, tenant_id=0)
        assert latest["date"] == "2026-08-02"
        assert latest["tsb"] == -8.0

    def test_upsert_training_stress_is_idempotent(self, clean_pg):
        db.upsert_training_stress_day(1, "2026-08-01", 50.0, 45.0, 40.0, -5.0, tenant_id=0)
        db.upsert_training_stress_day(1, "2026-08-01", 55.0, 48.0, 44.0, -4.0, tenant_id=0)
        days = db.get_training_stress_days(1, limit=90, tenant_id=0)
        assert len(days) == 1
        assert days[0]["tss"] == 55.0

    def test_get_training_stress_empty_for_unknown_athlete(self, clean_pg):
        assert db.get_training_stress_days(999, tenant_id=0) == []
        assert db.get_latest_training_stress(999, tenant_id=0) is None

    def test_recalculate_training_stress_end_to_end(self, clean_pg):
        """Exercise the full pipeline: rides -> PG -> TSS/EWMA -> stress days -> PG."""
        db.save_ride(
            _ride(None, date="2026-08-01T06:00:00+00:00",
                   distance_km=40.0, duration_minutes=120.0, avg_speed_kmh=20.0,
                   weight_kg=72.0, heart_rate_avg=150.0, elevation_gain_m=200.0)
        )
        db.save_ride(
            _ride(None, date="2026-08-02T06:00:00+00:00",
                   distance_km=50.0, duration_minutes=150.0, avg_speed_kmh=20.0,
                   weight_kg=72.0, heart_rate_avg=155.0, elevation_gain_m=250.0)
        )
        db.save_ride(
            _ride(None, date="2026-08-03T06:00:00+00:00",
                   distance_km=30.0, duration_minutes=90.0, avg_speed_kmh=20.0,
                   weight_kg=72.0, heart_rate_avg=145.0, elevation_gain_m=150.0)
        )

        db.recalculate_training_stress_for_athlete(1, ftp=250.0, tenant_id=0)

        days = db.get_training_stress_days(1, limit=90, tenant_id=0)
        assert len(days) == 3
        dates = [d["date"] for d in days]
        assert "2026-08-01" in dates
        assert "2026-08-02" in dates
        assert "2026-08-03" in dates
        for d in days:
            assert d["tss"] is not None
            assert d["atl"] is not None
            assert d["ctl"] is not None
            assert d["tsb"] is not None
