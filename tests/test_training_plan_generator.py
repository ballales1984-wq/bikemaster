"""Tests for training plan generator to improve coverage."""

from __future__ import annotations

from datetime import UTC, datetime

from bike_analyzer.backend.analytics.training_plan_generator import (
    WorkoutDay,
    _local_monthly_plan,
    _local_weekly_plan,
    _llm_plan_prompt,
    _plan_summary,
    generate_monthly_plan,
    generate_weekly_plan,
)
from bike_analyzer.backend.models.models import AthleteProfile, Ride


class TestPlanSummary:
    def test_empty_rides(self):
        result = _plan_summary(AthleteProfile(name="Test", experience_level="Beginner"), [])
        assert result["total_rides"] == 0
        assert result["recent_rides"] == 0
        assert result["avg_distance_km"] == 0
        assert result["avg_duration_min"] == 0

    def test_with_rides(self):
        rides = [
            Ride(distance_km=20.0, duration_minutes=60.0),
            Ride(distance_km=25.0, duration_minutes=75.0),
            Ride(distance_km=30.0, duration_minutes=90.0),
            Ride(distance_km=35.0, duration_minutes=105.0),
            Ride(distance_km=40.0, duration_minutes=120.0),
        ]
        result = _plan_summary(AthleteProfile(name="Test", experience_level="Beginner"), rides)
        assert result["total_rides"] == 5
        assert result["recent_rides"] == 4
        assert result["avg_distance_km"] == 32.5
        assert result["avg_duration_min"] == 97.5


class TestLocalWeeklyPlan:
    def test_returns_seven_days(self):
        athlete = AthleteProfile(name="Test", experience_level="Beginner")
        start = datetime(2024, 6, 1, tzinfo=UTC)
        plan = _local_weekly_plan(athlete, [], start)
        assert len(plan) == 7

    def test_beginner_zones(self):
        athlete = AthleteProfile(name="Test", experience_level="Beginner")
        start = datetime(2024, 6, 1, tzinfo=UTC)
        plan = _local_weekly_plan(athlete, [], start)
        valid_zones = {"Z2", "Z3", "Z1-Z2", "Z5", "Z2-Z3"}
        assert all(d.target_zone in valid_zones for d in plan)

    def test_advanced_zones(self):
        athlete = AthleteProfile(name="Test", experience_level="Advanced")
        start = datetime(2024, 6, 1, tzinfo=UTC)
        plan = _local_weekly_plan(athlete, [], start)
        assert len(plan) == 7

    def test_dates_are_consecutive(self):
        athlete = AthleteProfile(name="Test", experience_level="Beginner")
        start = datetime(2024, 6, 1, tzinfo=UTC)
        plan = _local_weekly_plan(athlete, [], start)
        for i, day in enumerate(plan):
            expected = (start + __import__("datetime").timedelta(days=i)).strftime("%Y-%m-%d")
            assert day.date == expected


class TestLocalMonthlyPlan:
    def test_base_phase_few_rides(self):
        athlete = AthleteProfile(name="Test", experience_level="Beginner")
        start = datetime(2024, 6, 1, tzinfo=UTC)
        plan = _local_monthly_plan(athlete, [], start)
        assert len(plan) == 20

    def test_peak_phase_long_rides(self):
        athlete = AthleteProfile(name="Test", experience_level="Elite")
        rides = [Ride(distance_km=50.0, duration_minutes=200.0) for _ in range(10)]
        start = datetime(2024, 6, 1, tzinfo=UTC)
        plan = _local_monthly_plan(athlete, rides, start)
        assert len(plan) == 20

    def test_build_phase_default(self):
        athlete = AthleteProfile(name="Test", experience_level="Intermediate")
        rides = [Ride(distance_km=30.0, duration_minutes=90.0) for _ in range(15)]
        start = datetime(2024, 6, 1, tzinfo=UTC)
        plan = _local_monthly_plan(athlete, rides, start)
        assert len(plan) == 20


class TestGenerateWeeklyPlan:
    def test_local_mode_fallback(self, monkeypatch):
        monkeypatch.setenv("AI_COACH_MODE", "local")
        athlete = AthleteProfile(name="Test", experience_level="Beginner")
        result = generate_weekly_plan(athlete, start_date="2024-06-01")
        assert "plan_name" in result
        assert "days" in result
        assert len(result["days"]) == 7

    def test_with_rides(self, monkeypatch):
        monkeypatch.setenv("AI_COACH_MODE", "local")
        athlete = AthleteProfile(name="Test", experience_level="Beginner")
        rides = [Ride(distance_km=30.0, duration_minutes=90.0)]
        result = generate_weekly_plan(athlete, rides=rides, start_date="2024-06-01")
        assert len(result["days"]) == 7
        assert result["start_date"] == "2024-06-01"


class TestGenerateMonthlyPlan:
    def test_local_mode_fallback(self, monkeypatch):
        monkeypatch.setenv("AI_COACH_MODE", "local")
        athlete = AthleteProfile(name="Test", experience_level="Beginner")
        result = generate_monthly_plan(athlete, start_date="2024-06-01")
        assert "plan_name" in result
        assert "days" in result
        assert len(result["days"]) == 20


class TestLlmPlanPrompt:
    def test_prompt_contains_athlete_info(self):
        athlete = AthleteProfile(name="Marco", experience_level="Beginner", ftp_watts=200, weight_kg=70.0)
        start = datetime(2024, 6, 1, tzinfo=UTC)
        prompt = _llm_plan_prompt(athlete, [], "weekly", start)
        assert "Marco" in prompt
        assert "Beginner" in prompt
        assert "200W" in prompt

    def test_prompt_weekly_end_date(self):
        athlete = AthleteProfile(name="Test", experience_level="Beginner")
        start = datetime(2024, 6, 1, tzinfo=UTC)
        prompt = _llm_plan_prompt(athlete, [], "weekly", start)
        assert "2024-06-08" in prompt

    def test_prompt_monthly_end_date(self):
        athlete = AthleteProfile(name="Test", experience_level="Beginner")
        start = datetime(2024, 6, 1, tzinfo=UTC)
        prompt = _llm_plan_prompt(athlete, [], "monthly", start)
        assert "2024-06-29" in prompt


class TestGenerateWeeklyPlanNonLocal:
    def test_falls_back_to_local_when_llm_fails(self, monkeypatch):
        monkeypatch.setenv("AI_COACH_MODE", "groq")
        athlete = AthleteProfile(name="Test", experience_level="Beginner")
        result = generate_weekly_plan(athlete, start_date="2024-06-01")
        assert "plan_name" in result
        assert len(result["days"]) == 7


class TestGenerateMonthlyPlanNonLocal:
    def test_falls_back_to_local_when_llm_fails(self, monkeypatch):
        monkeypatch.setenv("AI_COACH_MODE", "groq")
        athlete = AthleteProfile(name="Test", experience_level="Beginner")
        result = generate_monthly_plan(athlete, start_date="2024-06-01")
        assert "plan_name" in result
        assert len(result["days"]) == 20
