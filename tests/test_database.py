"""Tests for synchronous SQLite database layer (database.py)."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime

import pytest

import bike_analyzer.backend.db.database as db
from bike_analyzer.backend.db.database import (
    _INITIAL_DB_PATH,
    _ensure_external_identity_index,
    _row_to_athlete,
    _row_to_ride,
    delete_calendar_event,
    delete_poi,
    delete_ride,
    get_all_athletes,
    get_all_rides,
    get_athlete,
    get_athlete_by_email,
    get_athlete_by_name,
    get_athlete_by_query,
    get_calendar_event,
    get_chat_history,
    get_db_connection,
    get_events_by_athlete,
    get_events_by_date_range,
    get_events_by_month,
    get_latest_training_stress,
    get_nearby_pois,
    get_poi,
    get_ride,
    get_rides_by_athlete,
    get_route_safety_score,
    get_training_stress_days,
    get_user_by_id,
    get_user_by_username,
    get_weather_cache,
    init_db,
    list_pois,
    prune_chat_history,
    recalculate_training_stress_for_athlete,
    rotate_backups,
    save_athlete,
    save_calendar_event,
    save_chat_message,
    save_metric,
    save_poi,
    save_ride,
    save_road_incident,
    save_route_safety_score,
    save_user,
    save_weather_cache,
    update_athlete,
    update_calendar_event,
    update_ride,
    upsert_training_stress_day,
)


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_file)
    import importlib

    importlib.reload(db)
    db.DB_PATH = db_file
    db._INITIAL_DB_PATH = db_file
    init_db()
    yield db
    db.DB_PATH = _INITIAL_DB_PATH
    db._INITIAL_DB_PATH = _INITIAL_DB_PATH


def _make_athlete(db_mod, athlete_id=1, name="Rider", tenant_id=0):
    return db_mod.save_athlete(
        {"name": name, "age": 30, "weight_kg": 70.0, "tenant_id": tenant_id},
        athlete_id=athlete_id,
        tenant_id=tenant_id,
    )


class TestInitDb:
    def test_creates_core_tables(self):
        with get_db_connection() as conn:
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
        for expected in ("users", "rides", "athletes", "chat_history",
                         "calendar_events", "weather_cache", "training_stress_days",
                         "metrics", "training_goals", "planned_workouts",
                         "road_incidents", "route_safety_scores", "pois", "fitness_states"):
            assert expected in tables

    def test_idempotent_on_second_call(self):
        init_db()
        init_db()


class TestGetDbConnection:
    def test_returns_row_factory_rows(self):
        with get_db_connection() as conn:
            row = conn.execute("SELECT 1 AS n").fetchone()
        assert row["n"] == 1

    def test_commits_on_success(self):
        with get_db_connection() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY)")
            conn.execute("INSERT INTO t (id) VALUES (42)")
        with get_db_connection() as conn:
            val = conn.execute("SELECT id FROM t WHERE id=42").fetchone()[0]
        assert val == 42

    def test_rolls_back_on_exception(self):
        with pytest.raises(RuntimeError):
            with get_db_connection() as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS t2 (id INTEGER PRIMARY KEY)")
                conn.execute("INSERT INTO t2 (id) VALUES (1)")
                raise RuntimeError("boom")
        with get_db_connection() as conn:
            rows = conn.execute("SELECT COUNT(*) FROM t2").fetchone()[0]
        assert rows == 0


class TestRowConverters:
    def test_row_to_ride_with_all_columns(self):
        with get_db_connection() as conn:
            conn.execute(
                """INSERT INTO rides (athlete_id, date, distance_km, duration_minutes,
                   avg_speed_kmh, weight_kg, calories, heart_rate_avg, elevation_gain_m,
                   gps_points, external_source, external_id, title, activity_type,
                   is_official, source, tenant_id, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (1, "2024-06-15", 35.0, 90.0, 23.3, 70.0, 450.0, 145.0, 250.0,
                 json.dumps([{"lat": 45.0}]), "strava", "123", "Ride", "ride",
                 1, "manual", 0, datetime.now(UTC).isoformat()),
            )
            row = conn.execute("SELECT * FROM rides WHERE id=1").fetchone()
        d = _row_to_ride(row)
        assert d["distance_km"] == 35.0
        assert d["external_source"] == "strava"
        assert d["external_id"] == "123"
        assert d["title"] == "Ride"
        assert d["tenant_id"] == 0

    def test_row_to_athlete_with_all_columns(self):
        with get_db_connection() as conn:
            conn.execute(
                """INSERT INTO athletes (name, email, age, weight_kg, tenant_id)
                   VALUES (?,?,?,?,?)""",
                ("Test", "t@test.it", 30, 70.0, 1),
            )
            row = conn.execute("SELECT * FROM athletes WHERE id=1").fetchone()
        d = _row_to_athlete(row)
        assert d["name"] == "Test"
        assert d["email"] == "t@test.it"
        assert d["tenant_id"] == 1


class TestRideCrud:
    def test_save_ride_returns_id(self):
        _make_athlete(db)
        ride_id = save_ride({
            "athlete_id": 1,
            "date": "2024-06-15",
            "distance_km": 35.0,
            "duration_minutes": 90.0,
            "tenant_id": 0,
        })
        assert ride_id > 0

    def test_save_ride_skips_duplicate_external_identity(self):
        _make_athlete(db)
        rid = save_ride({
            "athlete_id": 1,
            "date": "2024-06-15",
            "external_source": "strava",
            "external_id": "abc",
            "tenant_id": 0,
        })
        rid2 = save_ride({
            "athlete_id": 1,
            "date": "2024-06-16",
            "external_source": "strava",
            "external_id": "abc",
            "tenant_id": 0,
        })
        assert rid == rid2

    def test_get_ride_roundtrip(self):
        _make_athlete(db)
        rid = save_ride({"athlete_id": 1, "date": "2024-06-15", "distance_km": 10.0, "tenant_id": 0})
        r = get_ride(rid)
        assert r["distance_km"] == 10.0

    def test_get_ride_tenant_isolation(self):
        _make_athlete(db, athlete_id=10, tenant_id=5)
        _make_athlete(db, athlete_id=11, tenant_id=99)
        rid = save_ride({"athlete_id": 10, "date": "2024-06-15", "tenant_id": 5})
        r = get_ride(rid, tenant_id=5)
        assert r is not None
        r2 = get_ride(rid, tenant_id=99)
        assert r2 is None

    def test_get_rides_by_athlete(self):
        _make_athlete(db, athlete_id=1)
        _make_athlete(db, athlete_id=2)
        save_ride({"athlete_id": 1, "date": "2024-06-15", "tenant_id": 0})
        save_ride({"athlete_id": 2, "date": "2024-06-16", "tenant_id": 0})
        rides = get_rides_by_athlete(1, tenant_id=0)
        assert len(rides) == 1

    def test_get_all_rides(self):
        _make_athlete(db, athlete_id=1)
        _make_athlete(db, athlete_id=2)
        save_ride({"athlete_id": 1, "date": "2024-06-15", "tenant_id": 0})
        save_ride({"athlete_id": 2, "date": "2024-06-16", "tenant_id": 0})
        all_r = get_all_rides()
        assert len(all_r) == 2

    def test_get_all_rides_filter_by_athlete_and_tenant(self):
        _make_athlete(db, athlete_id=10, tenant_id=1)
        _make_athlete(db, athlete_id=20, tenant_id=2)
        save_ride({"athlete_id": 10, "date": "2024-06-15", "tenant_id": 1})
        save_ride({"athlete_id": 20, "date": "2024-06-16", "tenant_id": 2})
        rides = get_all_rides(athlete_id=20, tenant_id=2)
        assert len(rides) == 1

    def test_update_ride(self):
        _make_athlete(db)
        rid = save_ride({"athlete_id": 1, "date": "2024-06-15", "distance_km": 10.0, "tenant_id": 0})
        ok = update_ride(rid, {"date": "2024-06-15", "distance_km": 20.0}, tenant_id=0)
        assert ok is True
        r = get_ride(rid)
        assert r["distance_km"] == 20.0

    def test_delete_ride(self):
        _make_athlete(db)
        rid = save_ride({"athlete_id": 1, "date": "2024-06-15", "tenant_id": 0})
        ok = delete_ride(rid)
        assert ok is True
        assert get_ride(rid) is None

    def test_ensure_external_identity_index(self):
        with get_db_connection() as conn:
            _ensure_external_identity_index(conn)
            idx = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='uq_rides_external_identity'"
            ).fetchone()
        assert idx is not None


class TestAthleteCrud:
    def test_save_athlete_returns_id(self):
        aid = save_athlete({"name": "Rider", "age": 30})
        assert aid > 0

    def test_save_athlete_with_tenant(self):
        aid = save_athlete({"name": "Rider", "tenant_id": 5}, tenant_id=5)
        assert aid > 0

    def test_get_athlete(self):
        _make_athlete(db, athlete_id=1, name="Rider", tenant_id=0)
        a = get_athlete(1)
        assert a["name"] == "Rider"

    def test_get_athlete_by_name(self):
        _make_athlete(db, athlete_id=1, name="UniqueName", tenant_id=0)
        a = get_athlete_by_name("UniqueName")
        assert a["name"] == "UniqueName"

    def test_get_athlete_by_email(self):
        _make_athlete(db, athlete_id=1, name="X", tenant_id=0)
        with get_db_connection() as conn:
            conn.execute("UPDATE athletes SET email=? WHERE id=?", ("x@test.it", 1))
            conn.commit()
        a = get_athlete_by_email("x@test.it")
        assert a["email"] == "x@test.it"

    def test_get_athlete_by_query_alias(self):
        _make_athlete(db, athlete_id=1, name="Alias", tenant_id=0)
        a = get_athlete_by_query(name="Alias")
        assert a["name"] == "Alias"

    def test_get_all_athletes(self):
        _make_athlete(db, athlete_id=1, name="A1", tenant_id=0)
        _make_athlete(db, athlete_id=2, name="A2", tenant_id=0)
        athletes = get_all_athletes()
        assert len(athletes) == 2

    def test_update_athlete(self):
        _make_athlete(db, athlete_id=1, name="Old", tenant_id=0)
        ok = update_athlete(1, {"name": "New"})
        assert ok is True
        a = get_athlete(1)
        assert a["name"] == "New"

    def test_update_athlete_missing_returns_false(self):
        assert update_athlete(9999, {"name": "X"}) is False


class TestMetricsAndStress:
    def test_save_and_get_training_stress(self):
        _make_athlete(db, athlete_id=1, tenant_id=0)
        upsert_training_stress_day(1, "2024-06-15", 100.0, 50.0, 80.0, 30.0, tenant_id=0)
        days = get_training_stress_days(1, tenant_id=0)
        assert len(days) == 1
        assert days[0]["tss"] == 100.0
        latest = get_latest_training_stress(1, tenant_id=0)
        assert latest["ctl"] == 80.0

    def test_recalculate_training_stress(self):
        _make_athlete(db, athlete_id=1, tenant_id=0)
        save_ride({"athlete_id": 1, "date": "2024-06-15", "distance_km": 50.0,
                   "duration_minutes": 120.0, "avg_speed_kmh": 25.0, "tenant_id": 0})
        recalculate_training_stress_for_athlete(1, ftp=250.0, tenant_id=0)
        days = get_training_stress_days(1, tenant_id=0)
        assert len(days) >= 1

    def test_save_metric(self):
        _make_athlete(db, athlete_id=1, tenant_id=0)
        save_ride({"athlete_id": 1, "date": "2024-06-15", "tenant_id": 0})
        rides = get_rides_by_athlete(1, tenant_id=0)
        mid = save_metric({"athlete_id": 1, "ride_id": rides[0]["id"],
                           "fatigue_score": 0.7, "calories_per_km": 30.0}, tenant_id=0)
        assert mid > 0


class TestCalendarEvents:
    def test_save_and_get_event(self):
        _make_athlete(db, athlete_id=1, tenant_id=0)
        eid = save_calendar_event({"athlete_id": 1, "title": "Ride", "date": "2024-06-15"}, tenant_id=0)
        e = get_calendar_event(eid)
        assert e["title"] == "Ride"

    def test_get_events_by_athlete(self):
        _make_athlete(db, athlete_id=1, tenant_id=0)
        _make_athlete(db, athlete_id=2, tenant_id=0)
        save_calendar_event({"athlete_id": 1, "title": "E1", "date": "2024-06-15"}, tenant_id=0)
        save_calendar_event({"athlete_id": 2, "title": "E2", "date": "2024-06-16"}, tenant_id=0)
        events = get_events_by_athlete(1, tenant_id=0)
        assert len(events) == 1

    def test_get_events_by_date_range(self):
        _make_athlete(db, athlete_id=1, tenant_id=0)
        save_calendar_event({"athlete_id": 1, "title": "E1", "date": "2024-06-10"}, tenant_id=0)
        save_calendar_event({"athlete_id": 1, "title": "E2", "date": "2024-06-20"}, tenant_id=0)
        events = get_events_by_date_range(1, "2024-06-01", "2024-06-15", tenant_id=0)
        assert len(events) == 1

    def test_get_events_by_month(self):
        _make_athlete(db, athlete_id=1, tenant_id=0)
        save_calendar_event({"athlete_id": 1, "title": "E", "date": "2024-06-15"}, tenant_id=0)
        events = get_events_by_month(1, 2024, 6, tenant_id=0)
        assert len(events) == 1

    def test_update_calendar_event(self):
        _make_athlete(db, athlete_id=1, tenant_id=0)
        eid = save_calendar_event({"athlete_id": 1, "title": "Old", "date": "2024-06-15"}, tenant_id=0)
        ok = update_calendar_event(eid, {"title": "New"})
        assert ok is True
        assert get_calendar_event(eid)["title"] == "New"

    def test_delete_calendar_event(self):
        _make_athlete(db, athlete_id=1, tenant_id=0)
        eid = save_calendar_event({"athlete_id": 1, "title": "Del", "date": "2024-06-15"}, tenant_id=0)
        ok = delete_calendar_event(eid)
        assert ok is True
        assert get_calendar_event(eid) is None


class TestChatHistory:
    def test_save_and_get_chat(self):
        _make_athlete(db, athlete_id=1, tenant_id=0)
        cid = save_chat_message(1, "user", "hello", tenant_id=0)
        assert cid > 0
        history = get_chat_history(1, tenant_id=0)
        assert len(history) == 1
        assert history[0]["role"] == "user"

    def test_prune_chat_history(self):
        _make_athlete(db, athlete_id=1, tenant_id=0)
        old_ts = (datetime.now(UTC) - __import__("datetime").timedelta(days=100)).isoformat()
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO chat_history (athlete_id, role, content, created_at, tenant_id) VALUES (?,?,?,?,?)",
                (1, "user", "old", old_ts, 0),
            )
            conn.commit()
        prune_chat_history(1, retention_days=90, tenant_id=0)
        history = get_chat_history(1, tenant_id=0)
        assert len(history) == 0


class TestWeatherCache:
    def test_save_and_get_weather_cache(self):
        wid = save_weather_cache(45.0, 7.0, "2024-06-15",
                                  {"temperature": 25.0, "humidity": 60.0, "description": "sunny"})
        assert wid > 0
        cached = get_weather_cache(45.0, 7.0, "2024-06-15")
        assert cached["temperature"] == 25.0
        assert cached["description"] == "sunny"


class TestPOIs:
    def test_save_and_get_poi(self):
        pid = save_poi({"name": "Fountain", "description": "Water", "lat": 45.0, "lon": 7.0, "type": "water"})
        assert pid > 0
        poi = get_poi(pid)
        assert poi["name"] == "Fountain"

    def test_get_nearby_pois(self):
        save_poi({"name": "Near", "description": "", "lat": 45.001, "lon": 7.001, "type": "poi"})
        save_poi({"name": "Far", "description": "", "lat": 46.0, "lon": 8.0, "type": "poi"})
        nearby = get_nearby_pois(45.0, 7.0, radius_km=5.0)
        names = [p["name"] for p in nearby]
        assert "Near" in names
        assert "Far" not in names

    def test_list_pois(self):
        save_poi({"name": "P1", "description": "", "lat": 1.0, "lon": 1.0, "type": "poi"})
        save_poi({"name": "P2", "description": "", "lat": 2.0, "lon": 2.0, "type": "poi"})
        pois = list_pois()
        assert len(pois) == 2

    def test_delete_poi(self):
        pid = save_poi({"name": "Del", "description": "", "lat": 1.0, "lon": 1.0, "type": "poi"})
        ok = delete_poi(pid)
        assert ok is True
        assert get_poi(pid) is None


class TestRoadIncidents:
    def test_save_road_incident(self):
        iid = save_road_incident({
            "source_id": "inc1",
            "lat": 45.0,
            "lon": 7.0,
            "incident_date": "2024-06-15",
            "severity": "high",
        })
        assert iid > 0


class TestRouteSafety:
    def test_save_and_get_route_safety(self):
        _make_athlete(db, athlete_id=1, tenant_id=0)
        rid = save_ride({"athlete_id": 1, "date": "2024-06-15", "tenant_id": 0})
        sid = save_route_safety_score({
            "ride_id": rid,
            "athlete_id": 1,
            "risk_score": 0.3,
            "label": "safe",
            "advice": "ok",
            "incident_count": 0,
            "route_length_km": 30.0,
        }, tenant_id=0)
        assert sid > 0
        score = get_route_safety_score(rid, tenant_id=0)
        assert score["label"] == "safe"


class TestUsers:
    def test_save_and_get_user(self):
        uid = save_user({"username": "alice", "email": "a@test.it", "is_admin": False})
        assert uid > 0
        u = get_user_by_username("alice")
        assert u["email"] == "a@test.it"
        u2 = get_user_by_id(uid)
        assert u2["username"] == "alice"


class TestBackups:
    def test_backup_and_rotate(self, tmp_path):
        backup_dir = str(tmp_path / "backups")
        os.makedirs(backup_dir, exist_ok=True)
        for i in range(12):
            with open(os.path.join(backup_dir, f"rides_backup_{i:06d}.db"), "w") as f:
                f.write("x")
        removed = rotate_backups(max_backups=5)
        assert len(removed) == 7
        remaining = os.listdir(backup_dir)
        assert len(remaining) == 5
