"""Tests for uncovered analytics/db modules to push coverage above 80%."""

import os
import tempfile
import pytest
from datetime import datetime, timezone, timedelta

from bike_analyzer.backend.models.models import (
    Ride, GPSPoint, AthleteProfile, Segment, CalendarEvent,
    haversine_distance_m
)
from bike_analyzer.backend.analytics import analytics as analytics_mod
from bike_analyzer.backend.analytics.training_load import (
    calculate_rss, calculate_atl_ctl_tsb, get_current_training_status,
    get_7day_fitness_summary, TrainingLoadDay
)
from bike_analyzer.backend.db import database as db_mod


# ============================================================
# analytics.py — export and summary coverage
# ============================================================

class TestAnalyticsExports:
    def test_export_rides_json(self, tmp_path):
        rides = [Ride(date="2024-06-01", distance_km=25.0, duration_minutes=60.0)]
        out = str(tmp_path / "export.json")
        result = analytics_mod.export_rides_json(rides, out)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    def test_export_rides_csv(self, tmp_path):
        rides = [Ride(date="2024-06-01", distance_km=25.0, duration_minutes=60.0)]
        out = str(tmp_path / "export.csv")
        result = analytics_mod.export_rides_csv(rides, out)
        assert os.path.exists(result)
        with open(result) as f:
            content = f.read()
        assert "2024-06-01" in content
        assert "distance_km" in content

    def test_rides_to_csv_output(self):
        rides = [Ride(date="2024-06-01", distance_km=25.0, duration_minutes=60.0,
                      avg_speed_kmh=25.0, calories=500, heart_rate_avg=150, elevation_gain_m=100)]
        result = analytics_mod.rides_to_csv(rides)
        assert "2024-06-01" in result
        assert "500" in result

    def test_rides_to_json_output(self):
        rides = [Ride(date="2024-06-01", distance_km=25.0)]
        result = analytics_mod.rides_to_json(rides)
        assert "2024-06-01" in result

    def test_ride_to_json(self):
        r = Ride(date="2024-06-01", distance_km=25.0)
        result = analytics_mod.ride_to_json(r)
        assert "2024-06-01" in result

    def test_text_report_content(self):
        r = Ride(date="2024-06-01", distance_km=25.0, duration_minutes=60.0,
                 avg_speed_kmh=25.0, calories=500, heart_rate_avg=150, elevation_gain_m=100)
        report = analytics_mod.generate_text_report(r)
        assert "BikeMaster Report" in report
        assert "25" in report


# ============================================================
# training_load.py — status/fitness summary coverage
# ============================================================

class TestTrainingLoadExtended:
    def test_get_7day_fitness_summary_empty(self):
        result = get_7day_fitness_summary([])
        assert result == []

    def test_get_7day_fitness_summary_with_data(self):
        rides = [
            Ride(date=f"2024-06-{i:02d}", distance_km=30.0 + i, duration_minutes=90.0 + i * 5, avg_speed_kmh=25.0)
            for i in range(1, 8)
        ]
        result = get_7day_fitness_summary(rides)
        assert len(result) >= 1
        assert all("date" in d and "atl" in d for d in result)

    def test_get_current_training_status_fatigued(self):
        rides = [
            Ride(date="2024-06-01", distance_km=50.0, duration_minutes=180.0, avg_speed_kmh=28.0, heart_rate_avg=170),
            Ride(date="2024-06-02", distance_km=50.0, duration_minutes=180.0, avg_speed_kmh=28.0, heart_rate_avg=170),
            Ride(date="2024-06-03", distance_km=50.0, duration_minutes=180.0, avg_speed_kmh=28.0, heart_rate_avg=170),
        ]
        result = get_current_training_status(rides)
        assert "tsb" in result
        assert "status" in result
        assert "recommendation" in result

    def test_get_current_training_status_no_data(self):
        result = get_current_training_status([])
        assert result["status"] == "no_data"
        assert result["atl"] == 0.0

    def test_training_load_day_dataclass(self):
        day = TrainingLoadDay(date="2024-06-01", tss=100.0, atl=80.0, ctl=90.0, tsb=10.0)
        assert day.date == "2024-06-01"
        assert day.tsb == 10.0
        assert day.atl == 80.0

    def test_calculate_rss_zero_duration(self):
        ride = Ride(date="2024-06-01", distance_km=0, duration_minutes=0)
        assert calculate_rss(ride) == 0.0

    def test_calculate_atl_ctl_tsb_single_day(self):
        rides = [
            Ride(date="2024-06-01", distance_km=30.0, duration_minutes=90.0, avg_speed_kmh=25.0),
        ]
        result = calculate_atl_ctl_tsb(rides)
        assert len(result) >= 1
        day = result[0]
        assert hasattr(day, 'atl')
        assert hasattr(day, 'ctl')
        assert hasattr(day, 'tsb')


# ============================================================
# database.py — calendar, weather, stress functions
# ============================================================

class TestDatabaseCalendar:
    def test_save_and_get_calendar_event(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_mod, 'DB_PATH', str(tmp_path / "test.db"))
        db_mod.init_db()
        event_id = db_mod.save_calendar_event({
            "athlete_id": 1, "title": "Granfondo",
            "event_type": "race", "date": "2024-09-15", "duration_minutes": 180
        })
        assert event_id > 0
        ev = db_mod.get_calendar_event(event_id)
        assert ev["title"] == "Granfondo"
        assert ev["event_type"] == "race"

    def test_get_events_by_athlete(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_mod, 'DB_PATH', str(tmp_path / "test.db"))
        db_mod.init_db()
        db_mod.save_calendar_event({"athlete_id": 1, "title": "Event A", "date": "2024-06-01"})
        db_mod.save_calendar_event({"athlete_id": 1, "title": "Event B", "date": "2024-06-02"})
        db_mod.save_calendar_event({"athlete_id": 2, "title": "Event C", "date": "2024-06-01"})
        events = db_mod.get_events_by_athlete(1)
        assert len(events) >= 2
        titles = [e["title"] for e in events]
        assert "Event A" in titles

    def test_get_events_by_date_range(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_mod, 'DB_PATH', str(tmp_path / "test.db"))
        db_mod.init_db()
        db_mod.save_calendar_event({"athlete_id": 1, "title": "Mid", "date": "2024-06-15"})
        events = db_mod.get_events_by_date_range(1, "2024-06-01", "2024-06-30")
        assert len(events) == 1
        assert events[0]["title"] == "Mid"

    def test_get_events_by_month(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_mod, 'DB_PATH', str(tmp_path / "test.db"))
        db_mod.init_db()
        db_mod.save_calendar_event({"athlete_id": 1, "title": "June Event", "date": "2024-06-15"})
        events = db_mod.get_events_by_month(1, 2024, 6)
        assert len(events) >= 1

    def test_update_calendar_event(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_mod, 'DB_PATH', str(tmp_path / "test.db"))
        db_mod.init_db()
        event_id = db_mod.save_calendar_event({"athlete_id": 1, "title": "Old", "date": "2024-06-01"})
        result = db_mod.update_calendar_event(event_id, {"title": "Updated", "completed": True})
        assert result is True
        ev = db_mod.get_calendar_event(event_id)
        assert ev["title"] == "Updated"
        assert ev["completed"] is True

    def test_delete_calendar_event(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_mod, 'DB_PATH', str(tmp_path / "test.db"))
        db_mod.init_db()
        event_id = db_mod.save_calendar_event({"athlete_id": 1, "title": "ToDelete", "date": "2024-06-01"})
        result = db_mod.delete_calendar_event(event_id)
        assert result is True
        assert db_mod.get_calendar_event(event_id) is None

    def test_update_nonexistent_calendar_event(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_mod, 'DB_PATH', str(tmp_path / "test.db"))
        db_mod.init_db()
        result = db_mod.update_calendar_event(99999, {"title": "Nope"})
        assert result is False

    def test_delete_nonexistent_calendar_event(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_mod, 'DB_PATH', str(tmp_path / "test.db"))
        db_mod.init_db()
        result = db_mod.delete_calendar_event(99999)
        assert result is False


class TestDatabaseWeather:
    def test_weather_cache_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_mod, 'DB_PATH', str(tmp_path / "test.db"))
        db_mod.init_db()
        weather = {"temperature": 22.5, "humidity": 65, "description": "sunny"}
        wid = db_mod.save_weather_cache(45.0, 9.0, "2024-06-15", weather)
        assert wid > 0
        cached = db_mod.get_weather_cache(45.0, 9.0, "2024-06-15")
        assert cached is not None
        assert cached["temperature"] == 22.5
        assert cached["description"] == "sunny"

    def test_weather_cache_miss(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_mod, 'DB_PATH', str(tmp_path / "test.db"))
        db_mod.init_db()
        cached = db_mod.get_weather_cache(99.0, 99.0, "2099-01-01")
        assert cached is None


class TestDatabaseTrainingStress:
    def test_upsert_and_get_training_stress(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_mod, 'DB_PATH', str(tmp_path / "test.db"))
        db_mod.init_db()
        db_mod.upsert_training_stress_day(1, "2024-06-15", 150.0, 120.0, 100.0, 20.0)
        db_mod.upsert_training_stress_day(1, "2024-06-15", 180.0, 130.0, 110.0, 20.0)
        days = db_mod.get_training_stress_days(1, limit=10)
        assert len(days) >= 1
        assert days[0]["date"] == "2024-06-15"

    def test_get_latest_training_stress(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_mod, 'DB_PATH', str(tmp_path / "test.db"))
        db_mod.init_db()
        db_mod.upsert_training_stress_day(1, "2024-06-01", 100.0, 80.0, 70.0, 10.0)
        db_mod.upsert_training_stress_day(1, "2024-06-15", 150.0, 100.0, 90.0, 10.0)
        latest = db_mod.get_latest_training_stress(1)
        assert latest is not None
        assert latest["date"] == "2024-06-15"

    def test_get_training_stress_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_mod, 'DB_PATH', str(tmp_path / "test.db"))
        db_mod.init_db()
        result = db_mod.get_training_stress_days(99999)
        assert result == []

    def test_recalculate_training_stress(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_mod, 'DB_PATH', str(tmp_path / "test.db"))
        db_mod.init_db()
        save_ride_fn = db_mod.save_ride
        save_ride_fn({
            "date": "2024-06-01 10:00:00", "distance_km": 30.0,
            "duration_minutes": 90.0, "avg_speed_kmh": 20.0,
            "heart_rate_avg": 150, "athlete_id": 1
        })
        db_mod.recalculate_training_stress_for_athlete(1, ftp=250.0)
        days = db_mod.get_training_stress_days(1)
        assert len(days) >= 1
