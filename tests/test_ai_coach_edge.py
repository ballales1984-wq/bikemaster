"""Edge-case and GROQ-path coverage for the AI Coach."""

from __future__ import annotations

import pytest

import bike_analyzer.backend.analytics.ai_coach as coach
from bike_analyzer.backend.models.models import AthleteProfile, Ride


def _athlete():
    return AthleteProfile(name="Test", weight_kg=70.0, experience_level="Beginner")


def _rides():
    return [Ride(date="2024-01-01", distance_km=30, duration_minutes=90, avg_speed_kmh=20.0)]


def test_clean_ai_output_formats_numbers():
    assert coach._clean_ai_output("Score 3.0 and 4.50 km") == "Score 3 and 4.5 km"
    assert "  " not in coach._clean_ai_output("too   many    spaces")


def test_is_recoverable_provider_error():
    assert coach._is_recoverable_provider_error(RuntimeError("connection refused"))
    assert not coach._is_recoverable_provider_error(ValueError("bad"))
    assert not coach._is_recoverable_provider_error(RuntimeError("auth error"))


def test_groq_recovery_advice_success(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_testkey1234567890")
    monkeypatch.setattr(coach, "get_ai_coach_client", lambda: (object(), "groq"))
    monkeypatch.setattr(coach, "_chat_completion_text", lambda *a, **k: "Consiglio: riposa e idratati.")
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    result = coach.generate_recovery_recommendations(_athlete(), _rides())
    assert "Consiglio" in result
    assert not result.startswith(coach._FALLBACK_PREFIX)


def test_groq_recovery_advice_fallback_on_api_error(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_testkey1234567890")
    monkeypatch.setattr(coach, "get_ai_coach_client", lambda: (object(), "groq"))

    def _raise(*a, **k):
        raise RuntimeError("connection error")

    monkeypatch.setattr(coach, "_chat_completion_text", _raise)
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    try:
        result = coach.generate_recovery_recommendations(_athlete(), _rides())
    finally:
        coach._BANNED_PROVIDERS.discard("groq")
    assert result.startswith(coach._FALLBACK_PREFIX)


def test_groq_recovery_advice_client_raises_value_error(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_testkey1234567890")
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])

    def _raise_value():
        raise ValueError("no valid key")

    monkeypatch.setattr(coach, "get_ai_coach_client", _raise_value)
    result = coach.generate_recovery_recommendations(_athlete(), _rides())
    assert result.startswith(coach._FALLBACK_PREFIX)


def test_groq_workout_advice_success(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_testkey1234567890")
    monkeypatch.setattr(coach, "get_ai_coach_client", lambda: (object(), "groq"))
    monkeypatch.setattr(
        coach, "chat_with_tools", lambda *a, **k: {"content": "Piani di allenamento: fai Zone 2."}
    )
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    result = coach.generate_workout_recommendations(_athlete(), _rides())
    assert "Zone 2" in result
    assert not result.startswith(coach._FALLBACK_PREFIX)


def test_athlete_profile_invalid_short_circuits(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_testkey1234567890")
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    bad = AthleteProfile(name="", weight_kg=0.0)
    result = coach.generate_recovery_recommendations(bad, [])
    assert "profile" in result.lower()
