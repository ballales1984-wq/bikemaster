"""Test AI Coach (mock mode)."""

import os

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
    rides = [
        Ride(date="2026-06-11", distance_km=42.0, duration_minutes=100, avg_speed_kmh=25.2)
    ]

    advice = generate_training_advice(profile, rides)

    assert "Progressive" in advice or "Knowledge-based" in advice
    assert "Recovery" in advice
    assert len(advice) > 50


def test_local_recovery_advice_does_not_call_model(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_should_not_call")
    profile = AthleteProfile(name="Test", weight_kg=70, experience_level="Beginner")
    rides = [
        Ride(date="2026-06-11", distance_km=42.0, duration_minutes=100, avg_speed_kmh=25.2)
    ]

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
    assert "nome" in msg


def test_training_advice_falls_back_to_openai_after_groq_403(monkeypatch):
    import sys
    import types

    import bike_analyzer.backend.analytics.ai_coach as ai_coach

    class Choice:
        def __init__(self, content):
            self.message = types.SimpleNamespace(content=content)

    class OpenAICompletions:
        def create(self, **kwargs):
            return types.SimpleNamespace(choices=[Choice("OpenAI advice")])

    class OpenAIChat:
        completions = OpenAICompletions()

    class FailingCompletions:
        def create(self, **kwargs):
            raise PermissionError("403 Access denied")

    class FailingChat:
        completions = FailingCompletions()

    class FakeGroq:
        def __init__(self, api_key):
            self.api_key = api_key
            self.chat = FailingChat()

    class FakeOpenAI:
        def __init__(self, api_key):
            self.api_key = api_key
            self.chat = OpenAIChat()

    monkeypatch.setenv("AI_COACH_PROVIDER_ORDER", "groq,openai")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-test")
    monkeypatch.setattr(ai_coach, "_BANNED_PROVIDERS", set())
    monkeypatch.setattr(ai_coach, "_current_client", None)
    monkeypatch.setattr(ai_coach, "_current_provider", None)
    monkeypatch.setitem(sys.modules, "groq", types.SimpleNamespace(Groq=FakeGroq))
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    profile = AthleteProfile(name="Test", weight_kg=70, experience_level="Beginner")
    advice = ai_coach.generate_training_advice(profile, [])

    assert advice == "OpenAI advice"
    assert "groq" in ai_coach._BANNED_PROVIDERS


def test_training_advice_uses_local_fallback_when_all_providers_fail(monkeypatch):
    import sys
    import types

    import bike_analyzer.backend.analytics.ai_coach as ai_coach

    class FailingCompletions:
        def create(self, **kwargs):
            raise PermissionError("403 Access denied")

    class FailingChat:
        completions = FailingCompletions()

    class FakeGroq:
        def __init__(self, api_key):
            self.api_key = api_key
            self.chat = FailingChat()

    class FakeOpenAI:
        def __init__(self, api_key):
            self.api_key = api_key
            self.chat = FailingChat()

    monkeypatch.setenv("AI_COACH_PROVIDER_ORDER", "groq,openai")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-test")
    monkeypatch.setattr(ai_coach, "_BANNED_PROVIDERS", set())
    monkeypatch.setattr(ai_coach, "_current_client", None)
    monkeypatch.setattr(ai_coach, "_current_provider", None)
    monkeypatch.setitem(sys.modules, "groq", types.SimpleNamespace(Groq=FakeGroq))
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))

    profile = AthleteProfile(name="Test", weight_kg=70, experience_level="Beginner")
    advice = ai_coach.generate_training_advice(profile, [])

    assert advice.startswith(ai_coach._FALLBACK_PREFIX)
    assert "groq" in ai_coach._BANNED_PROVIDERS
    assert "openai" in ai_coach._BANNED_PROVIDERS
