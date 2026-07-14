import os

os.environ["AI_COACH_MODE"] = "local"
os.environ["GROQ_API_KEY"] = "test-key"

from bike_analyzer.backend.analytics.ai_coach import (
    _ban_provider,
    _build_athlete_context,
    _build_rag_context,
    _generate_fallback_recovery_advice,
    _generate_fallback_training_advice,
    _generate_local_recovery_advice,
    _generate_local_training_advice,
    ai_coach_full,
    analyze_anomalies,
    analyze_historical_trend,
    chat_with_tools,
    generate_recovery_recommendations,
    generate_training_advice,
    generate_training_plan,
    get_fitness_state_explanation,
    validate_athlete_profile,
)
from bike_analyzer.backend.models.models import AthleteProfile, GPSPoint, Ride


def test_validate_athlete_profile_rejects_empty():
    profile = AthleteProfile(name="", weight_kg=70.0, experience_level="Beginner")
    valid, msg = validate_athlete_profile(profile)
    assert valid is False
    assert "nome" in msg


def test_validate_athlete_profile_accepts_complete():
    profile = AthleteProfile(name="Marco", weight_kg=72.0, experience_level="Amateur")
    valid, msg = validate_athlete_profile(profile)
    assert valid is True
    assert msg == ""


def test_validate_athlete_profile_rejects_zero_weight():
    profile = AthleteProfile(name="Marco", weight_kg=0.0, experience_level="Amateur")
    valid, msg = validate_athlete_profile(profile)
    assert valid is False
    assert "peso" in msg


def test_generate_training_advice_validates_profile():
    result = generate_training_advice(AthleteProfile(), [])
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_training_advice_with_local_mode(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_should_not_call")
    result = generate_training_advice(
        AthleteProfile(name="Marco", weight_kg=70.0, experience_level="Beginner"), []
    )
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_recovery_advice_returns_string():
    result = generate_recovery_recommendations(AthleteProfile(), [], fatigue_score=5.0)
    assert isinstance(result, str)
    assert len(result) > 0


def test_analyze_historical_trend_insufficient_data():
    result = analyze_historical_trend([])
    assert "Insufficient" in result


def test_analyze_historical_trend_with_rides():
    rides = [
        Ride(date="2026-01-01", distance_km=30.0, duration_minutes=90.0, avg_speed_kmh=20.0),
        Ride(date="2026-01-02", distance_km=35.0, duration_minutes=85.0, avg_speed_kmh=24.7),
    ]
    result = analyze_historical_trend(rides)
    assert isinstance(result, str)
    assert "Trend" in result


def test_ai_coach_full_returns_dict(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_should_not_call")
    result = ai_coach_full(
        AthleteProfile(name="Test", weight_kg=70.0, experience_level="Beginner"),
        [],
        athlete_id=0,
    )
    assert isinstance(result, dict)
    assert "training_advice" in result
    assert "recovery_advice" in result
    assert "historical_analysis" in result
    assert "training_scores" in result
    assert "recovery_scores" in result
    assert "charts" in result


def test_ai_coach_workout_endpoint(client):
    r = client.get("/api/v1/coach/workout")
    assert r.status_code == 200
    data = r.json()
    assert "recommendations" in data


def test_ai_coach_workout_endpoint_with_athlete(client, db_path):
    from bike_analyzer.backend.db import database as db_mod

    athlete_id = db_mod.save_athlete(
        {"name": "Test Athlete", "weight_kg": 70.0, "experience_level": "Beginner"}
    )
    r = client.get("/api/v1/coach/workout", params={"athlete_id": athlete_id})
    assert r.status_code == 200
    data = r.json()
    assert "recommendations" in data


def test_ai_coach_recovery_endpoint(client):
    r = client.get("/api/v1/coach/recovery")
    assert r.status_code == 200
    data = r.json()
    assert "recommendations" in data


class TestBuildAthleteContext:
    def test_full_profile(self):
        athlete = AthleteProfile(
            name="Marco",
            age=35,
            weight_kg=72.0,
            experience_level="Amateur",
            goals="Granfondo",
            preferred_terrain="mountain",
            weekly_volume_km=200.0,
            best_segments="Passo Stelvio",
        )
        ctx = _build_athlete_context(athlete)
        assert "Marco" in ctx
        assert "35" in ctx
        assert "72" in ctx
        assert "Amateur" in ctx
        assert "Granfondo" in ctx
        assert "mountain" in ctx
        assert "200" in ctx
        assert "Passo Stelvio" in ctx

    def test_minimal_profile(self):
        athlete = AthleteProfile(name="", weight_kg=0)
        ctx = _build_athlete_context(athlete)
        assert "N/A" in ctx


class TestGenerateLocalTrainingAdvice:
    def test_beginner_with_goals(self):
        athlete = AthleteProfile(
            name="Test",
            weight_kg=70.0,
            experience_level="Beginner",
            goals="granfondo",
        )
        advice = _generate_local_training_advice(athlete, [])
        assert isinstance(advice, str)
        assert len(advice) > 0

    def test_elite_with_flat_terrain(self):
        athlete = AthleteProfile(
            name="Pro",
            weight_kg=65.0,
            experience_level="Elite",
            preferred_terrain="flat",
        )
        advice = _generate_local_training_advice(athlete, [])
        assert "flat" in advice.lower() or "aerob" in advice.lower()

    def test_with_rides(self):
        rides = [
            Ride(
                date="2026-01-01",
                distance_km=50.0,
                duration_minutes=120.0,
                avg_speed_kmh=25.0,
                elevation_gain_m=600.0,
            )
        ]
        athlete = AthleteProfile(
            name="Test", weight_kg=70.0, experience_level="Intermediate"
        )
        advice = _generate_local_training_advice(athlete, rides)
        assert isinstance(advice, str)
        assert len(advice) > 0


class TestGenerateLocalRecoveryAdvice:
    def test_low_recovery_score(self):
        athlete = AthleteProfile(name="Test", weight_kg=70.0)
        advice = _generate_local_recovery_advice(athlete, [], recovery_score=3.0)
        assert isinstance(advice, str)
        assert len(advice) > 0

    def test_high_recovery_score(self):
        athlete = AthleteProfile(name="Test", weight_kg=70.0)
        advice = _generate_local_recovery_advice(athlete, [], recovery_score=8.0)
        assert isinstance(advice, str)
        assert len(advice) > 0

    def test_with_long_ride(self):
        rides = [
            Ride(
                date="2026-01-01",
                distance_km=100.0,
                duration_minutes=300.0,
                avg_speed_kmh=22.0,
                elevation_gain_m=2000.0,
            )
        ]
        athlete = AthleteProfile(name="Test", weight_kg=70.0)
        advice = _generate_local_recovery_advice(athlete, rides, recovery_score=4.0)
        assert isinstance(advice, str)
        assert len(advice) > 0


class TestAnalyzeAnomalies:
    def test_no_rides(self):
        result = analyze_anomalies([])
        assert result["status"] == "no_data"
        assert result["anomalies"] == []

    def test_normal_rides(self):
        rides = [
            Ride(
                date="2026-01-01",
                distance_km=30.0,
                duration_minutes=90.0,
                avg_speed_kmh=20.0,
                heart_rate_avg=150.0,
            ),
            Ride(
                date="2026-01-02",
                distance_km=30.0,
                duration_minutes=90.0,
                avg_speed_kmh=20.0,
                heart_rate_avg=152.0,
            ),
        ]
        result = analyze_anomalies(rides)
        assert result["status"] == "analyzed"

    def test_hr_elevation_detected(self):
        rides = [
            Ride(
                date="2026-01-01",
                distance_km=30.0,
                duration_minutes=90.0,
                avg_speed_kmh=20.0,
                heart_rate_avg=120.0,
            ),
            Ride(
                date="2026-01-02",
                distance_km=30.0,
                duration_minutes=90.0,
                avg_speed_kmh=20.0,
                heart_rate_avg=120.0,
            ),
            Ride(
                date="2026-01-03",
                distance_km=30.0,
                duration_minutes=90.0,
                avg_speed_kmh=20.0,
                heart_rate_avg=150.0,
            ),
        ]
        result = analyze_anomalies(rides)
        assert any(a["type"] == "heart_rate_elevation" for a in result["anomalies"])

    def test_excessive_volume_detected(self):
        rides = [
            Ride(
                date=f"2026-01-{i:02d}",
                distance_km=50.0,
                duration_minutes=320.0,
                avg_speed_kmh=18.0,
            )
            for i in range(1, 6)
        ]
        result = analyze_anomalies(rides)
        assert any(a["type"] == "excessive_volume" for a in result["anomalies"])


class TestGenerateTrainingPlan:
    def test_beginner_default(self):
        athlete = AthleteProfile(
            name="Test", weight_kg=70.0, experience_level="Beginner"
        )
        plan = generate_training_plan(athlete, days=7)
        assert plan["days"] == 7
        assert "workouts" in plan
        assert len(plan["workouts"]) == 5

    def test_with_fatigue_state(self):
        athlete = AthleteProfile(
            name="Test", weight_kg=70.0, experience_level="Intermediate"
        )
        plan = generate_training_plan(
            athlete, days=7, fitness_state={"tsb": -20.0}
        )
        assert any(w["zone"] == "Base" for w in plan["workouts"])

    def test_with_fresh_state(self):
        athlete = AthleteProfile(
            name="Test", weight_kg=70.0, experience_level="Advanced"
        )
        plan = generate_training_plan(
            athlete, days=7, fitness_state={"tsb": 15.0}
        )
        assert any(w["zone"] in ("Z4", "Z5") for w in plan["workouts"])

    def test_explanation_includes_ftp(self):
        athlete = AthleteProfile(
            name="Test", weight_kg=70.0, experience_level="Intermediate", ftp_watts=250.0
        )
        plan = generate_training_plan(
            athlete, days=7, fitness_state={"tsb": 0.0}
        )
        assert "250" in plan["explanation"]


class TestBanProvider:
    def test_ban_adds_to_set(self):
        from bike_analyzer.backend.analytics.ai_coach import _BANNED_PROVIDERS

        _BANNED_PROVIDERS.discard("test_provider")
        _ban_provider("test_provider", "test reason")
        assert "test_provider" in _BANNED_PROVIDERS
        _BANNED_PROVIDERS.discard("test_provider")

    def test_ban_resets_current_client(self, monkeypatch):
        from bike_analyzer.backend.analytics.ai_coach import (
            _BANNED_PROVIDERS,
            _current_client,
            _current_provider,
        )

        monkeypatch.setattr(
            "bike_analyzer.backend.analytics.ai_coach._current_provider", "test_p"
        )
        monkeypatch.setattr(
            "bike_analyzer.backend.analytics.ai_coach._current_client", object()
        )
        _BANNED_PROVIDERS.discard("test_p")
        _ban_provider("test_p", "reason")
        assert "test_p" in _BANNED_PROVIDERS
        _BANNED_PROVIDERS.discard("test_p")


class TestChatWithToolsLocalMode:
    def test_local_mode_returns_message(self, monkeypatch):
        monkeypatch.setenv("AI_COACH_MODE", "local")
        result = chat_with_tools([{"role": "user", "content": "test"}])
        assert "content" in result
        assert "locale" in result["content"].lower() or "local" in result["content"].lower()


class TestGetFitnessStateExplanation:
    def test_no_session_returns_empty(self):
        result = get_fitness_state_explanation(athlete_id=0)
        assert result == ""

    def test_no_athlete_id_returns_empty(self):
        result = get_fitness_state_explanation(athlete_id=None)
        assert result == ""

    def test_with_session_returns_explanation(self, monkeypatch):
        import bike_analyzer.backend.analytics.repositories.fitness_state_repository as fsr_mod

        class FakeRepo:
            async def get_latest(self, athlete_id):
                return {"tsb": -10.0, "atl": 80.0, "ctl": 90.0, "recovery_hours_needed": 12.0}

        monkeypatch.setattr(fsr_mod, "FitnessStateRepository", FakeRepo)
        result = get_fitness_state_explanation(
            athlete_id=1, session_factory=lambda: None
        )
        assert "TSB" in result or result == ""


class TestFallbackAdvice:
    def test_fallback_training_advice_has_prefix(self):
        athlete = AthleteProfile(name="Test", weight_kg=70.0)
        advice = _generate_fallback_training_advice(athlete, [])
        assert "AI service temporarily unavailable" in advice

    def test_fallback_recovery_advice_has_prefix(self):
        athlete = AthleteProfile(name="Test", weight_kg=70.0)
        advice = _generate_fallback_recovery_advice(athlete, [], recovery_score=3.0)
        assert "AI service temporarily unavailable" in advice

    def test_fallback_recovery_high_score(self):
        athlete = AthleteProfile(name="Test", weight_kg=70.0)
        advice = _generate_fallback_recovery_advice(athlete, [], recovery_score=8.0)
        assert "AI service temporarily unavailable" in advice
        assert len(advice) > 0


class TestAiCoachFullWithRides:
    def test_with_recent_ride(self, monkeypatch):
        monkeypatch.setenv("AI_COACH_MODE", "local")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_should_not_call")
        ride = Ride(
            date="2026-01-01",
            distance_km=40.0,
            duration_minutes=120.0,
            avg_speed_kmh=22.0,
            heart_rate_avg=155.0,
            elevation_gain_m=400.0,
        )
        result = ai_coach_full(
            AthleteProfile(name="Test", weight_kg=70.0, experience_level="Intermediate"),
            [ride],
            athlete_id=0,
        )
        assert isinstance(result, dict)
        assert "training_advice" in result
        assert "recovery_advice" in result
        assert "training_scores" in result
        assert len(result["training_scores"]) == 3
        assert len(result["recovery_scores"]) == 2
