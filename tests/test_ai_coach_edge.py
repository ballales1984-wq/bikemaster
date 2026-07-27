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


def test_generate_training_advice_local_mode(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    result = coach.generate_training_advice(_athlete(), _rides())
    assert isinstance(result, str)
    assert result


def test_generate_training_advice_invalid_athlete(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    bad = AthleteProfile(name="", weight_kg=0.0)
    result = coach.generate_training_advice(bad, [])
    assert "profile" in result.lower()


def test_generate_workout_recommendations_local_mode(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    result = coach.generate_workout_recommendations(_athlete(), _rides())
    assert isinstance(result, str)
    assert result


def test_generate_training_advice_with_athlete_id(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    monkeypatch.setattr(coach, "calculate_summary", lambda rides: {"total_rides": 1, "avg_distance_km": 30})
    monkeypatch.setattr(coach, "calculate_performance_score", lambda ride: 7)
    monkeypatch.setattr(coach, "calculate_recovery_score", lambda ride: 6)
    monkeypatch.setattr(coach, "_build_rag_context", lambda *a, **k: "")
    result = coach.generate_training_advice(_athlete(), _rides(), athlete_id=1)
    assert isinstance(result, str)
    assert result


def test_generate_recovery_advice_with_athlete_id(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    monkeypatch.setattr(coach, "calculate_summary", lambda rides: {"total_rides": 1})
    monkeypatch.setattr(coach, "calculate_recovery_score", lambda ride: 4)
    monkeypatch.setattr(coach, "_build_rag_context", lambda *a, **k: "")
    result = coach.generate_recovery_recommendations(_athlete(), _rides(), athlete_id=1)
    assert isinstance(result, str)
    assert result


def test_analyze_historical_trend():
    rides = [
        Ride(date="2024-01-01", distance_km=30, duration_minutes=90, avg_speed_kmh=20.0),
        Ride(date="2024-01-08", distance_km=35, duration_minutes=95, avg_speed_kmh=22.0),
    ]
    result = coach.analyze_historical_trend(rides)
    assert isinstance(result, str)
    assert result


def test_analyze_historical_trend_insufficient_data():
    result = coach.analyze_historical_trend([Ride(date="2024-01-01", distance_km=30, duration_minutes=90, avg_speed_kmh=20.0)])
    assert "Insufficient data" in result


def test_get_fitness_state_explanation_no_session():
    result = coach.get_fitness_state_explanation(1, session_factory=None)
    assert result == ""


def test_chat_with_tools_local_mode(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    result = coach.chat_with_tools([{"role": "user", "content": "hi"}])
    assert result["content"] == "Local mode: tool calling is not available."


def test_chat_with_tools_no_provider(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "groq")
    monkeypatch.setattr(coach, "get_ai_coach_client", lambda: (_ for _ in ()).throw(ValueError("no key")))
    result = coach.chat_with_tools([{"role": "user", "content": "hi"}])
    assert result["content"] == "No LLM provider configured."


def test_chat_with_tools_unknown_tool(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_testkey1234567890")

    class _FakeToolCall:
        def __init__(self):
            self.id = "c1"
            self.type = "function"
            self.function = type("F", (), {"name": "unknown_tool", "arguments": "{}"})()

    class _FakeMsgWithContent:
        tool_calls = [_FakeToolCall()]
        content = None

    class _FakeMsgNoContent:
        tool_calls = None
        content = "final content"

    class _FakeChoice:
        def __init__(self, message):
            self.message = message

    class _FakeCompletions:
        def __init__(self):
            self._first = True

        def create(self, *args, **kwargs):
            if self._first:
                self._first = False
                return type("R", (), {"choices": [_FakeChoice(_FakeMsgWithContent())]})()
            return type("R", (), {"choices": [_FakeChoice(_FakeMsgNoContent())]})()

    class _FakeChat:
        def __init__(self):
            self.completions = _FakeCompletions()

    class _FakeClient:
        def __init__(self):
            self.chat = _FakeChat()

    monkeypatch.setattr(coach, "get_ai_coach_client", lambda: (_FakeClient(), "groq"))
    result = coach.chat_with_tools([{"role": "user", "content": "hi"}])
    assert isinstance(result, dict)
    assert "content" in result


def test_fallback_training_advice_with_kb(monkeypatch):
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [{"text": "kb text", "topic": "t"}])
    monkeypatch.setattr(coach, "format_context_for_llm", lambda results: "kb context")
    result = coach._generate_fallback_training_advice(_athlete(), _rides())
    assert "Progressive" in result
    assert "kb context" in result


def test_fallback_recovery_advice_with_kb_practical_tips(monkeypatch):
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [{"text": "kb text", "topic": "t"}])
    monkeypatch.setattr(coach, "format_context_for_llm", lambda results: "kb context")
    result = coach._generate_fallback_recovery_advice(_athlete(), _rides(), recovery_score=8.0)
    assert "Practical tips" in result
    assert "kb context" in result


def test_fallback_recovery_advice_without_kb_low_score(monkeypatch):
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    monkeypatch.setattr(coach, "format_context_for_llm", lambda results: "")
    result = coach._generate_fallback_recovery_advice(_athlete(), _rides(), recovery_score=2.0)
    assert "Stretching" in result


def test_fallback_recovery_advice_without_kb_high_score(monkeypatch):
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    monkeypatch.setattr(coach, "format_context_for_llm", lambda results: "")
    result = coach._generate_fallback_recovery_advice(_athlete(), _rides(), recovery_score=8.0)
    assert "Nutrition" in result


def test_generate_training_plan_with_fitness_state(monkeypatch):
    low_tsb = {"tsb": -20}
    high_tsb = {"tsb": 15}
    plan_low = coach.generate_training_plan(_athlete(), days=5, fitness_state=low_tsb)
    assert len(plan_low["workouts"]) > 0
    plan_high = coach.generate_training_plan(_athlete(), days=5, fitness_state=high_tsb)
    assert len(plan_high["workouts"]) > 0


def test_ai_coach_full_with_gps_points(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    monkeypatch.setattr(coach, "analyze_historical_trends", lambda rides: "trend")
    monkeypatch.setattr(coach, "get_fitness_state_explanation", lambda athlete_id: "")
    rides = [
        Ride(
            date="2024-01-01",
            distance_km=30,
            duration_minutes=90,
            avg_speed_kmh=20.0,
            gps_points=[{"lat": 45.0, "lon": 9.0, "timestamp": "2024-01-01T08:00:00"}],
        )
    ]
    result = coach.ai_coach_full(_athlete(), rides, athlete_id=1)
    assert "training_advice" in result
    assert "recovery_advice" in result
    assert "training_scores" in result


def test_build_rag_context_returns_string():
    ctx = coach._build_rag_context(_athlete(), _rides(), "training")
    assert isinstance(ctx, str)


def test_build_athlete_context_format():
    ctx = coach._build_athlete_context(_athlete())
    assert "Test" in ctx
    assert "Beginner" in ctx


def test_system_prompt_non_empty():
    prompt = coach._system_prompt()
    assert isinstance(prompt, str)
    assert prompt


def test_rules_section_non_empty():
    rules = coach._rules_section()
    assert isinstance(rules, str)
    assert rules


def test_generate_training_advice_retry_then_fallback(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_testkey1234567890")
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    monkeypatch.setattr(coach, "calculate_summary", lambda rides: {"total_rides": 1})
    monkeypatch.setattr(coach, "calculate_performance_score", lambda ride: 7)
    monkeypatch.setattr(coach, "calculate_recovery_score", lambda ride: 6)

    call_count = 0

    def _raise(*a, **k):
        nonlocal call_count
        call_count += 1
        raise RuntimeError("connection refused")

    monkeypatch.setattr(coach, "get_ai_coach_client", lambda: (object(), "groq"))
    monkeypatch.setattr(coach, "chat_with_tools", _raise)
    coach._BANNED_PROVIDERS.clear()
    result = coach.generate_training_advice(_athlete(), _rides())
    assert result.startswith(coach._FALLBACK_PREFIX)
    assert call_count == 3
