"""Tests for granfondo training plan generator."""
from bike_analyzer.backend.analytics.granfondo_planner import (
    calculate_granfondo_workouts_from_goal,
    generate_granfondo_plan,
)


def test_generate_granfondo_plan_basic():
    plan = generate_granfondo_plan("2024-06-01", target_weeks=4, ftp=250.0)
    assert len(plan) == 13  # 4 weeks * 3 workouts + 1 event
    assert plan[-1]["workout_type"] == "race"
    assert plan[-1]["title"] == "Granfondo"


def test_generate_granfondo_plan_dates():
    plan = generate_granfondo_plan("2024-06-01", target_weeks=2)
    assert plan[0]["date"] == "2024-06-01"
    assert plan[1]["date"] == "2024-06-02"
    assert plan[2]["date"] == "2024-06-03"


def test_generate_granfondo_plan_tapering():
    plan = generate_granfondo_plan("2024-06-01", target_weeks=4)
    first_week = [w for w in plan if w["date"].startswith("2024-06-01") or w["date"].startswith("2024-06-03") or w["date"].startswith("2024-06-05")]
    last_week_workouts = [w for i, w in enumerate(plan) if i >= len(plan) - 4]
    assert len(last_week_workouts) == 4


def test_calculate_granfondo_workouts_from_goal():
    goal = {"id": 1, "start_date": "2024-06-01", "weeks": 4, "ftp": 250.0}
    plan = calculate_granfondo_workouts_from_goal(goal)
    assert len(plan) == 13
    assert all("goal_id" in w for w in plan)
    assert all(w["goal_id"] == 1 for w in plan)


def test_calculate_granfondo_workouts_defaults():
    plan = calculate_granfondo_workouts_from_goal({})
    assert len(plan) > 0
