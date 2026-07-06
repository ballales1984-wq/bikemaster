import os

os.environ["AI_COACH_MODE"] = "local"

import pytest
from datetime import datetime, timezone

from bike_analyzer.backend.analytics.training_plan_generator import (
    WorkoutDay,
    generate_monthly_plan,
    generate_weekly_plan,
)
from bike_analyzer.backend.models.models import AthleteProfile, Ride


def _athlete(overrides=None):
    data = {
        "name": "Test Rider",
        "age": 30,
        "weight_kg": 70.0,
        "experience_level": "Intermediate",
        "ftp_watts": 250.0,
        "weekly_volume_km": 150.0,
        "annual_hours": 200.0,
        "years_active": 5,
        "weekly_sessions": 4,
        "monthly_hours": 40.0,
        "goals": "granfondo",
        "preferred_terrain": "mountain",
    }
    if overrides:
        data.update(overrides)
    return AthleteProfile(**data)


def _ride(overrides=None):
    data = {
        "id": 1,
        "date": "2024-06-01T10:00:00Z",
        "distance_km": 25.0,
        "duration_minutes": 60.0,
        "avg_speed_kmh": 25.0,
        "elevation_gain_m": 200.0,
        "calories": 600.0,
    }
    if overrides:
        data.update(overrides)
    return Ride(**data)


def test_weekly_plan_returns_7_days():
    athlete = _athlete()
    rides = [_ride({"id": i}) for i in range(5)]
    start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    plan = generate_weekly_plan(athlete, rides, start_date=start)
    assert plan["plan_name"] == "Piano settimanale"
    assert len(plan["days"]) == 7
    assert plan["start_date"] == start
    assert plan["end_date"] == (datetime.fromisoformat(start) + __import__("datetime").timedelta(days=7)).strftime("%Y-%m-%d")
    for day in plan["days"]:
        assert "date" in day
        assert "title" in day
        assert "workout_type" in day
        assert "duration_minutes" in day
        assert "target_zone" in day
        assert "description" in day


def test_weekly_plan_includes_recovery_days():
    athlete = _athlete()
    start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    plan = generate_weekly_plan(athlete, [], start_date=start)
    types = [d["workout_type"] for d in plan["days"]]
    assert "recovery" in types


def test_monthly_plan_returns_20_days():
    athlete = _athlete()
    rides = [_ride({"id": i}) for i in range(20)]
    start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    plan = generate_monthly_plan(athlete, rides, start_date=start)
    assert plan["plan_name"] == "Piano mensile"
    assert len(plan["days"]) == 20
    for day in plan["days"]:
        assert day["duration_minutes"] >= 30


def test_empty_rides_returns_local_plan():
    athlete = _athlete()
    start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    plan = generate_weekly_plan(athlete, [], start_date=start)
    assert len(plan["days"]) == 7
    assert plan["summary"] != ""


def test_beginner_gets_shorter_workouts():
    athlete = _athlete({"experience_level": "Beginner", "ftp_watts": 180})
    rides = [_ride()]
    start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    plan = generate_weekly_plan(athlete, rides, start_date=start)
    assert all(d["duration_minutes"] >= 30 for d in plan["days"])
    recovery_days = [d for d in plan["days"] if d["workout_type"] == "recovery"]
    assert len(recovery_days) >= 1


def test_workout_day_dataclass():
    day = WorkoutDay(
        date="2024-06-01",
        title="Endurance base",
        workout_type="endurance",
        duration_minutes=75,
        target_zone="Z2",
        description="Fondo lento",
    )
    assert day.workout_type == "endurance"
    assert day.target_zone == "Z2"
