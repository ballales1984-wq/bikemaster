"""Tests for granfondo training plan generator."""

from __future__ import annotations

from bike_analyzer.backend.analytics.granfondo_planner import (
    calculate_granfondo_workouts_from_goal,
    generate_granfondo_plan,
)


class TestGenerateGranfondoPlan:
    def test_returns_list_of_dicts(self):
        plan = generate_granfondo_plan("2024-09-01", target_weeks=4)
        assert isinstance(plan, list)
        assert all(isinstance(w, dict) for w in plan)

    def test_includes_event_day(self):
        plan = generate_granfondo_plan("2024-09-01", target_weeks=4)
        titles = [w["title"] for w in plan]
        assert any("Granfondo" in t for t in titles)

    def test_workout_dates_are_strings(self):
        plan = generate_granfondo_plan("2024-09-01", target_weeks=2)
        for w in plan:
            assert isinstance(w["date"], str)
            assert len(w["date"]) == 10

    def test_tapering_reduces_duration(self):
        plan = generate_granfondo_plan("2024-09-01", target_weeks=8)
        regular = [w for w in plan if "Granfondo" not in w["title"]]
        taper = [w for w in plan if "Granfondo" in w["title"]]
        if regular and taper:
            avg_regular = sum(w["duration_minutes"] for w in regular) / len(regular)
            avg_taper = sum(w["duration_minutes"] for w in taper) / len(taper)
            assert avg_taper < avg_regular

    def test_target_intensity_in_range(self):
        plan = generate_granfondo_plan("2024-09-01", target_weeks=4)
        for w in plan:
            assert 0 <= w["target_intensity"] <= 1.0


class TestCalculateGranfondoWorkoutsFromGoal:
    def test_defaults_when_fields_missing(self):
        plan = calculate_granfondo_workouts_from_goal({})
        assert len(plan) > 0

    def test_sets_goal_id_on_workouts(self):
        plan = calculate_granfondo_workouts_from_goal({"id": 42})
        assert all(w.get("goal_id") == 42 for w in plan)

    def test_uses_provided_start_date(self):
        plan = calculate_granfondo_workouts_from_goal({"start_date": "2025-01-01", "weeks": 2})
        dates = [w["date"] for w in plan]
        assert all(d >= "2025-01-01" for d in dates)
