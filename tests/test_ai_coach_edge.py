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


def test_build_rag_context_with_goals_terrain_and_ride_hints(monkeypatch):
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    athlete = AthleteProfile(
        name="Test",
        weight_kg=70.0,
        experience_level="Beginner",
        goals="granfondo criterium",
        preferred_terrain="mountain hill climb",
    )
    rides = [
        Ride(
            date="2024-01-01",
            distance_km=30,
            duration_minutes=90,
            avg_speed_kmh=28.0,
            elevation_gain_m=300,
            heart_rate_avg=170,
        )
    ]
    ctx = coach._build_rag_context(athlete, rides, "training")
    assert isinstance(ctx, str)


def test_generate_training_advice_conversation_append_error(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_testkey1234567890")
    monkeypatch.setattr(coach, "get_ai_coach_client", lambda: (object(), "groq"))
    monkeypatch.setattr(
        coach, "chat_with_tools", lambda *a, **k: {"content": "Allenamento:Zone2"}
    )
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])

    class _FakeStore:
        def append(self, *a, **k):
            raise RuntimeError("store down")

    monkeypatch.setitem(coach.__dict__, "_conversation_store", _FakeStore())
    result = coach.generate_training_advice(_athlete(), _rides(), athlete_id=1)
    assert "Allenamento" in result


def test_generate_training_advice_non_recoverable_error_fallback(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_testkey1234567890")
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])

    class _FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(*a, **k):
                    raise TypeError("bad response")

    monkeypatch.setattr(coach, "get_ai_coach_client", lambda: (_FakeClient(), "groq"))
    coach._BANNED_PROVIDERS.clear()
    result = coach.generate_training_advice(_athlete(), _rides())
    assert result.startswith(coach._FALLBACK_PREFIX)


def test_generate_training_advice_with_athlete_id_and_history(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    monkeypatch.setattr(coach, "_build_rag_context", lambda *a, **k: "kb")

    class _FakeStore:
        @staticmethod
        def load(aid):
            return [{"role": "user", "content": "vecchio messaggio"}]

        @staticmethod
        def prune(aid, n):
            return None

    monkeypatch.setitem(coach.__dict__, "_conversation_store", _FakeStore())
    result = coach.generate_training_advice(_athlete(), _rides(), athlete_id=1)
    assert isinstance(result, str)
    assert result


def test_generate_training_advice_date_span_invalid(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    monkeypatch.setattr(coach, "_build_rag_context", lambda *a, **k: "kb")
    bad_rides = [
        Ride(date="not-a-date", distance_km=30, duration_minutes=90, avg_speed_kmh=20.0),
        Ride(date="also-bad", distance_km=35, duration_minutes=95, avg_speed_kmh=22.0),
    ]
    result = coach.generate_training_advice(_athlete(), bad_rides, athlete_id=1)
    assert isinstance(result, str)
    assert result


def test_generate_recovery_advice_with_history(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    monkeypatch.setattr(coach, "_build_rag_context", lambda *a, **k: "kb")

    class _FakeStore:
        @staticmethod
        def load(aid):
            return [{"role": "user", "content": "history"}]

        @staticmethod
        def prune(aid, n):
            return None

    monkeypatch.setitem(coach.__dict__, "_conversation_store", _FakeStore())
    result = coach.generate_recovery_recommendations(_athlete(), _rides(), athlete_id=1)
    assert isinstance(result, str)
    assert result


def test_get_ai_coach_client_invalid_per_user_key(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "groq")

    import bike_analyzer.backend.analytics.ai_coach as coach_mod
    monkeypatch.setattr(coach_mod, "_current_client", None)
    monkeypatch.setattr(coach_mod, "_current_provider", None)

    import bike_analyzer.backend.api.user_keys as uk_mod

    def _fake_get():
        return {"groq": "invalid_key"}

    monkeypatch.setattr(uk_mod, "get_request_user_keys", _fake_get)
    with pytest.raises(ValueError, match="invalid GROQ API key"):
        coach.get_ai_coach_client()


def test_chat_with_tools_json_decode_error(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_testkey1234567890")

    class _FakeToolCall:
        def __init__(self):
            self.id = "c1"
            self.type = "function"
            self.function = type("F", (), {"name": "get_weather", "arguments": "not-json"})()

    class _FakeMsg:
        tool_calls = [_FakeToolCall()]
        content = None

    class _FakeChoice:
        def __init__(self, message):
            self.message = message

    class _FakeCompletions:
        @staticmethod
        def create(*a, **k):
            return type("R", (), {"choices": [_FakeChoice(_FakeMsg())]})()

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeClient:
        chat = _FakeChat()

    monkeypatch.setattr(coach, "get_ai_coach_client", lambda: (_FakeClient(), "groq"))
    result = coach.chat_with_tools([{"role": "user", "content": "hi"}])
    assert isinstance(result, dict)
    assert "content" in result


def test_chat_with_tools_tool_execution_failure(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_testkey1234567890")

    class _FakeToolCall:
        def __init__(self):
            self.id = "c1"
            self.type = "function"
            self.function = type("F", (), {"name": "get_weather", "arguments": "{}"})()

    class _FakeMsg:
        tool_calls = [_FakeToolCall()]
        content = None

    class _FakeChoice:
        def __init__(self, message):
            self.message = message

    class _FakeCompletions:
        @staticmethod
        def create(*a, **k):
            return type("R", (), {"choices": [_FakeChoice(_FakeMsg())]})()

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeClient:
        chat = _FakeChat()

    monkeypatch.setattr(coach, "get_ai_coach_client", lambda: (_FakeClient(), "groq"))
    monkeypatch.setattr(coach, "chat_with_tools", lambda *a, **k: {"content": "final"})
    result = coach.chat_with_tools([{"role": "user", "content": "hi"}])
    assert isinstance(result, dict)


def test_ai_coach_full_with_segments_and_duration_chart(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])
    monkeypatch.setattr(coach, "analyze_historical_trends", lambda rides: "trend")
    monkeypatch.setattr(coach, "get_fitness_state_explanation", lambda athlete_id: "")
    monkeypatch.setattr(coach, "calculate_performance_score", lambda ride: 7)
    monkeypatch.setattr(coach, "calculate_recovery_score", lambda ride: 6)

    import bike_analyzer.backend.analytics.performance as perf_mod
    monkeypatch.setattr(perf_mod, "calculate_endurance_score", lambda rides: 7)
    monkeypatch.setattr(perf_mod, "calculate_efficiency_score", lambda ride: 7)

    monkeypatch.setattr(coach, "create_speed_chart", lambda *a, **k: None)
    monkeypatch.setattr(coach, "create_duration_chart", lambda *a, **k: None)

    monkeypatch.setattr(
        "bike_analyzer.backend.processing.processing.build_segments",
        lambda points: [object()],
    )

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


def test_chat_with_tools_conversation_append(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_testkey1234567890")

    class _FakeMsg:
        content = "final"
        tool_calls = None

    class _FakeChoice:
        def __init__(self, message):
            self.message = message

    class _FakeCompletions:
        @staticmethod
        def create(*a, **k):
            return type("R", (), {"choices": [_FakeChoice(_FakeMsg())]})()

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeClient:
        chat = _FakeChat()

    class _FakeStore:
        @staticmethod
        def append(aid, msg):
            return None

    monkeypatch.setattr(coach, "get_ai_coach_client", lambda: (_FakeClient(), "groq"))
    monkeypatch.setitem(coach.__dict__, "_conversation_store", _FakeStore())
    result = coach.chat_with_tools([{"role": "user", "content": "hi"}], athlete_id=1)
    assert isinstance(result, dict)
    assert "content" in result


def test_generate_local_training_advice_criterium_goal():
    athlete = AthleteProfile(
        name="Test",
        weight_kg=70.0,
        experience_level="Beginner",
        goals="criterium sprint short veloce",
    )
    result = coach._generate_local_training_advice(athlete, [])
    assert isinstance(result, str)
    assert result


def test_generate_local_training_advice_downhill_goal():
    athlete = AthleteProfile(
        name="Test",
        weight_kg=70.0,
        experience_level="Beginner",
        goals="downhill enduro tech technical",
    )
    result = coach._generate_local_training_advice(athlete, [])
    assert isinstance(result, str)
    assert result


def test_kb_session_search_exception(monkeypatch):
    monkeypatch.setattr(coach, "search_knowledge_base", lambda *a, **k: [])

    def _raise_pgvector(*a, **k):
        raise RuntimeError("pgvector down")

    import bike_analyzer.backend.analytics.knowledge_base as kb_mod
    monkeypatch.setattr(kb_mod, "search_knowledge_base_pgvector", _raise_pgvector)
    result = coach._kb("test query", session=object())
    assert isinstance(result, str)
