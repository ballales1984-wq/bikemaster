"""Test AI Coach (mock mode)."""

import pytest
pytestmark = pytest.mark.slow

import os

os.environ["AI_COACH_MODE"] = "external"
os.environ["GROQ_API_KEY"] = "test-key-for-unit-tests"

from bike_analyzer.backend.analytics.ai_coach import (
    analyze_historical_trend,
    generate_recovery_advice,
    generate_training_advice,
)
from bike_analyzer.backend.models.models import AthleteProfile, Ride


def test_analyze_historical_trend_empty():
    result = analyze_historical_trend([])
    assert "insufficient" in result.lower()


def test_analyze_historical_trend():
    rides = [
        Ride(
            date=f"2024-06-{i:02d}",
            distance_km=25.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            calories=500,
            elevation_gain_m=200,
        )
        for i in range(1, 4)
    ]
    result = analyze_historical_trend(rides)
    assert "Trend:" in result


def test_clean_ai_output():
    from bike_analyzer.backend.analytics.ai_coach import _clean_ai_output

    assert _clean_ai_output("  test  ") == "test"
    assert _clean_ai_output("1.50 km") == "1.5 km"
    assert _clean_ai_output("5.0 hours") == "5 hours"
    assert _clean_ai_output("test  multiple   spaces") == "test multiple spaces"


def test_local_training_advice_does_not_call_model(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_should_not_call")
    profile = AthleteProfile(name="Test", weight_kg=70, experience_level="Beginner")
    rides = [Ride(date="2026-06-11", distance_km=42.0, duration_minutes=100, avg_speed_kmh=25.2)]

    advice = generate_training_advice(profile, rides)

    assert "Progressive" in advice or "Knowledge-based" in advice
    assert "Recovery" in advice
    assert len(advice) > 50


def test_local_recovery_advice_does_not_call_model(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_should_not_call")
    profile = AthleteProfile(name="Test", weight_kg=70, experience_level="Beginner")
    rides = [Ride(date="2026-06-11", distance_km=42.0, duration_minutes=100, avg_speed_kmh=25.2)]

    advice = generate_recovery_advice(profile, rides, fatigue_score=5.0)

    assert "active maintenance" in advice.lower() or "extra recovery" in advice.lower()
    assert "Hydration" in advice or "nutrition" in advice.lower()
    assert "Sleep" in advice
    assert "Biomechanics" not in advice


def test_validate_athlete_profile_complete():

    from bike_analyzer.backend.analytics.ai_coach import validate_athlete_profile

    athlete = AthleteProfile(name="Mario Rossi", weight_kg=75.0, experience_level="Amateur")
    valid, msg = validate_athlete_profile(athlete)
    assert valid is True


def test_validate_athlete_profile_missing_name():
    from bike_analyzer.backend.analytics.ai_coach import validate_athlete_profile

    athlete = AthleteProfile(name="", weight_kg=75.0, experience_level="Amateur")
    valid, msg = validate_athlete_profile(athlete)
    assert valid is False
    assert "name" in msg


def test_training_advice_falls_back_to_local_after_groq_403(monkeypatch):
    import sys
    import types

    import bike_analyzer.backend.analytics.ai_coach as ai_coach

    monkeypatch.setenv("AI_COACH_MODE", "external")

    class FailingCompletions:
        def create(self, **kwargs):
            raise PermissionError("403 Access denied")

    class FailingChat:
        completions = FailingCompletions()

    class FakeGroq:
        def __init__(self, api_key):
            self.api_key = api_key
            self.chat = FailingChat()

    monkeypatch.setenv("AI_COACH_PROVIDER_ORDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setattr(ai_coach, "_BANNED_PROVIDERS", set())
    monkeypatch.setattr(ai_coach, "_current_client", None)
    monkeypatch.setattr(ai_coach, "_current_provider", None)
    monkeypatch.setitem(sys.modules, "groq", types.SimpleNamespace(Groq=FakeGroq))

    profile = AthleteProfile(name="Test", weight_kg=70, experience_level="Beginner")
    advice = ai_coach.generate_training_advice(profile, [])

    assert advice.startswith(ai_coach._FALLBACK_PREFIX)
    assert "groq" in ai_coach._BANNED_PROVIDERS


def test_training_advice_uses_local_fallback_when_all_providers_fail(monkeypatch):
    import sys
    import types

    import bike_analyzer.backend.analytics.ai_coach as ai_coach

    monkeypatch.setenv("AI_COACH_MODE", "external")

    class FailingCompletions:
        def create(self, **kwargs):
            raise PermissionError("403 Access denied")

    class FailingChat:
        completions = FailingCompletions()

    class FakeGroq:
        def __init__(self, api_key):
            self.api_key = api_key
            self.chat = FailingChat()

    monkeypatch.setenv("AI_COACH_PROVIDER_ORDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setattr(ai_coach, "_BANNED_PROVIDERS", set())
    monkeypatch.setattr(ai_coach, "_current_client", None)
    monkeypatch.setattr(ai_coach, "_current_provider", None)
    monkeypatch.setitem(sys.modules, "groq", types.SimpleNamespace(Groq=FakeGroq))

    profile = AthleteProfile(name="Test", weight_kg=70, experience_level="Beginner")
    advice = ai_coach.generate_training_advice(profile, [])

    assert advice.startswith(ai_coach._FALLBACK_PREFIX)
    assert "groq" in ai_coach._BANNED_PROVIDERS


def test_analyze_anomalies_detects_hr_elevation():
    from bike_analyzer.backend.analytics.ai_coach import analyze_anomalies

    # Create significant HR elevation: avg 100, last ride 130 (30% increase)
    rides = [
        Ride(
            date="2024-06-01",
            distance_km=30.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            calories=400,
            elevation_gain_m=100,
            heart_rate_avg=95.0,
        ),
        Ride(
            date="2024-06-02",
            distance_km=30.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            calories=400,
            elevation_gain_m=100,
            heart_rate_avg=100.0,
        ),
        Ride(
            date="2024-06-03",
            distance_km=30.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            calories=400,
            elevation_gain_m=100,
            heart_rate_avg=130.0,
        ),
    ]
    result = analyze_anomalies(rides)
    assert result["status"] == "analyzed"
    assert isinstance(result["anomalies"], list)


def test_chat_with_tools_local_mode(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    from bike_analyzer.backend.analytics.ai_coach import chat_with_tools

    result = chat_with_tools([{"role": "user", "content": "Fammi un piano di allenamento"}])
    assert "content" in result


def test_generate_workout_plan_with_fitness_state():
    from bike_analyzer.backend.analytics.ai_coach import generate_workout_plan

    athlete = AthleteProfile(name="Test", weight_kg=70, experience_level="Amateur")
    fitness_state = {"tsb": -20, "atl": 80, "ctl": 60}

    plan = generate_workout_plan(athlete, days=5, fitness_state=fitness_state)
    assert "workouts" in plan
    assert len(plan["workouts"]) == 5
    assert "Monday" in plan["workouts"][0]["day"]
