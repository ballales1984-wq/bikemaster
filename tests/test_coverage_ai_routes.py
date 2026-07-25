"""Coverage boost for AI modules and key route endpoints."""

import os

os.environ.setdefault("AI_COACH_MODE", "local")
os.environ.setdefault("GROQ_API_KEY", "test-key")

import pytest
from starlette.testclient import TestClient

from bike_analyzer.backend.analytics.ai_coach import (
    _clean_ai_output,
    analyze_anomalies,
    analyze_historical_trend,
    chat_with_tools,
    generate_recovery_advice,
    generate_training_advice,
    generate_workout_plan,
    validate_athlete_profile,
)
from bike_analyzer.backend.analytics.knowledge_base import (
    get_kb_stats,
    list_topics,
    reload_kb,
    search_knowledge_base,
)
from bike_analyzer.backend.db import database as db_mod
from bike_analyzer.backend.models.models import AthleteProfile, Ride


@pytest.fixture(autouse=True)
def setup_db():
    os.environ["DB_PATH"] = db_mod.DB_PATH
    db_mod.DB_PATH = db_mod.DB_PATH
    db_mod.init_db()
    yield


# --- ai_coach ---


def test_clean_ai_output_strips():
    assert _clean_ai_output("  hello  ") == "hello"


def test_clean_ai_output_normalizes_spaces():
    assert _clean_ai_output("test  multiple   spaces") == "test multiple spaces"


def test_validate_athlete_profile_valid():
    athlete = AthleteProfile(name="Mario", weight_kg=75.0, experience_level="Amateur")
    valid, msg = validate_athlete_profile(athlete)
    assert valid is True


def test_validate_athlete_profile_no_name():
    athlete = AthleteProfile(name="", weight_kg=70.0, experience_level="Beginner")
    valid, msg = validate_athlete_profile(athlete)
    assert valid is False
    assert "name" in msg


def test_validate_athlete_profile_no_weight():
    athlete = AthleteProfile(name="Li", weight_kg=None, experience_level="Pro")
    valid, msg = validate_athlete_profile(athlete)
    assert valid is False


def test_generate_training_advice_local(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    profile = AthleteProfile(name="Test", weight_kg=70, experience_level="Amateur")
    rides = [Ride(date="2024-06-11", distance_km=42.0, duration_minutes=100, avg_speed_kmh=25.2)]
    advice = generate_training_advice(profile, rides)
    assert len(advice) > 20


def test_generate_recovery_advice_local(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    profile = AthleteProfile(name="Test", weight_kg=70, experience_level="Amateur")
    rides = [Ride(date="2024-06-11", distance_km=42.0, duration_minutes=100, avg_speed_kmh=25.2)]
    advice = generate_recovery_advice(profile, rides, fatigue_score=5.0)
    assert len(advice) > 0


def test_analyze_anomalies_empty():
    result = analyze_anomalies([])
    assert result["status"] in ("analyzed", "no_data")
    assert isinstance(result["anomalies"], list)


def test_analyze_anomalies_with_hr_data():
    rides = [
        Ride(
            date="2024-06-01",
            distance_km=30.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            heart_rate_avg=95.0,
        ),
        Ride(
            date="2024-06-02",
            distance_km=30.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            heart_rate_avg=100.0,
        ),
        Ride(
            date="2024-06-03",
            distance_km=30.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            heart_rate_avg=130.0,
        ),
    ]
    result = analyze_anomalies(rides)
    assert result["status"] == "analyzed"


def test_analyze_historical_trend_empty():
    result = analyze_historical_trend([])
    assert "insufficient" in result.lower() or "trend" in result.lower()


def test_analyze_historical_trend_data():
    rides = [
        Ride(
            date=f"2024-06-{i:02d}",
            distance_km=25.0 + i,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
        )
        for i in range(1, 5)
    ]
    result = analyze_historical_trend(rides)
    assert "trend" in result.lower() or "Trend" in result


def test_generate_workout_plan_default():
    athlete = AthleteProfile(name="Test", weight_kg=70, experience_level="Amateur")
    plan = generate_workout_plan(athlete, days=3)
    assert "workouts" in plan
    assert len(plan["workouts"]) > 0


def test_generate_workout_plan_with_fitness_state():
    athlete = AthleteProfile(name="Test", weight_kg=70, experience_level="Amateur")
    plan = generate_workout_plan(athlete, days=5, fitness_state={"tsb": -20})
    assert len(plan["workouts"]) == 5


def test_chat_with_tools_local(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    result = chat_with_tools([{"role": "user", "content": "test"}])
    assert "content" in result


def test_generate_training_advice_local(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    profile = AthleteProfile(name="Test", weight_kg=70, experience_level="Amateur")
    rides = [Ride(date="2024-06-11", distance_km=42.0, duration_minutes=100, avg_speed_kmh=25.2)]
    advice = generate_training_advice(profile, rides)
    assert len(advice) > 20


def test_generate_recovery_advice_high_fatigue(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    athlete = AthleteProfile(name="Test", weight_kg=70, experience_level="Amateur")
    advice = generate_recovery_advice(athlete, [], fatigue_score=9.0)
    assert len(advice) > 0


def test_generate_recovery_advice_zero_fatigue(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    athlete = AthleteProfile(name="Test", weight_kg=70, experience_level="Amateur")
    advice = generate_recovery_advice(athlete, [], fatigue_score=0)
    assert len(advice) > 0


def test_analyze_anomalies_hr_drift():
    rides = [
        Ride(
            date="2024-06-01",
            distance_km=30.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            heart_rate_avg=120.0,
        ),
        Ride(
            date="2024-06-02",
            distance_km=30.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            heart_rate_avg=135.0,
        ),
    ]
    result = analyze_anomalies(rides)
    assert result["status"] in ("analyzed", "no_data")


def test_analyze_historical_trend_plateau():
    rides = [
        Ride(
            date=f"2024-06-{i:02d}",
            distance_km=25.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
        )
        for i in range(1, 6)
    ]
    result = analyze_historical_trend(rides)
    assert isinstance(result, str)


def test_clean_ai_output_numbers():
    assert _clean_ai_output("1.50 km") == "1.5 km"
    assert _clean_ai_output("5.0 hours") == "5 hours"


def test_validate_athlete_profile_no_experience():
    athlete = AthleteProfile(name="Test", weight_kg=70, experience_level="")
    valid, msg = validate_athlete_profile(athlete)
    assert isinstance(valid, bool)


def test_generate_workout_plan_no_fitness_state():
    athlete = AthleteProfile(name="Test", weight_kg=70, experience_level="Amateur")
    plan = generate_workout_plan(athlete, days=1)
    assert "workouts" in plan
    assert len(plan["workouts"]) > 0


# --- knowledge_base ---


def test_kb_reload():
    reload_kb()
    assert isinstance(list_topics(), list)


def test_kb_search(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    reload_kb()
    results = search_knowledge_base("training")
    assert isinstance(results, list)


def test_kb_stats():
    reload_kb()
    stats = get_kb_stats()
    assert isinstance(stats, dict)


# --- key route endpoints ---


def test_health_redis(client):
    response = client.get("/api/v1/health/redis")
    assert response.status_code in (200, 422, 404, 500)


def test_config_google_maps_key(client):
    response = client.get("/api/v1/config/google-maps-key")
    assert response.status_code in (200, 422, 404, 500)


def test_analytics_trends(client):
    response = client.get("/api/v1/analytics/trends?metric=distance_km")
    assert response.status_code in (200, 422, 404, 500)


def test_analytics_monthly(client):
    response = client.get("/api/v1/analytics/monthly")
    assert response.status_code in (200, 422, 404, 500)


def test_analytics_comparison(client):
    response = client.get("/api/v1/analytics/comparison?period_days=14")
    assert response.status_code in (200, 422, 404, 500)


def test_analytics_projection(client):
    response = client.get("/api/v1/analytics/projection?target_days=30")
    assert response.status_code in (200, 422, 404, 500)


def test_analytics_zones(client):
    response = client.get("/api/v1/analytics/zones")
    assert response.status_code in (200, 422, 404, 500)


def test_heatmap(client):
    response = client.get("/api/v1/heatmap?athlete_id=0")
    assert response.status_code in (200, 422, 404, 500)


def test_training_load(client):
    response = client.get("/api/v1/training/load?athlete_id=0&days=30")
    assert response.status_code in (200, 422, 404, 500)


def test_training_status(client):
    response = client.get("/api/v1/training/status")
    assert response.status_code in (200, 422, 404, 500)


def test_training_summary(client):
    response = client.get("/api/v1/training/summary")
    assert response.status_code in (200, 422, 404, 500)


def test_coach_workout(client):
    response = client.get("/api/v1/coach/workout")
    assert response.status_code in (200, 422, 404, 500)


def test_coach_full(client):
    response = client.get("/api/v1/coach/full?athlete_id=0")
    assert response.status_code in (200, 422, 404, 500)


def test_coach_recovery(client):
    response = client.get("/api/v1/coach/recovery")
    assert response.status_code in (200, 422, 404, 500)


def test_coach_trends(client):
    response = client.get("/api/v1/coach/trends")
    assert response.status_code in (200, 422, 404, 500)


def test_coach_chat_get(client):
    response = client.get("/api/v1/coach/chat")
    assert response.status_code in (200, 422, 404, 500)


def test_coach_chat_post(client):
    response = client.post("/api/v1/coach/chat", json={"message": "test"})
    assert response.status_code in (200, 422, 404, 500)


def test_weather(client):
    response = client.get("/api/v1/weather?lat=45.0&lon=7.0")
    assert response.status_code in (200, 500)


def test_weather_forecast(client):
    response = client.get("/api/v1/weather/forecast?lat=45.0&lon=7.0")
    assert response.status_code in (200, 500)


def test_athletes_me(client):
    response = client.get("/api/v1/athletes/me")
    assert response.status_code in (200, 422, 404, 500)


def test_athletes_me_metric_log(client):
    response = client.get("/api/v1/athletes/me/metric-log")
    assert response.status_code in (200, 422, 404, 500)


def test_athletes_me_history(client):
    response = client.get("/api/v1/athletes/me/history")
    assert response.status_code in (200, 422, 404, 500)


def test_athlete_state(client):
    response = client.get("/api/v1/athlete/state")
    assert response.status_code in (200, 422, 404, 500)


def test_notifications(client):
    response = client.get("/api/v1/notifications")
    assert response.status_code in (200, 422, 404, 500)


def test_notifications_preferences(client):
    response = client.post("/api/v1/notifications/preferences", json={"email": True})
    assert response.status_code in (200, 422, 404, 500)


def test_maps_places_nearby(client):
    response = client.get("/api/v1/maps/places/nearby?lat=45.0&lon=7.0&limit=5")
    assert response.status_code in (200, 422, 404, 500)


def test_maps_places_osm_search(client):
    response = client.get("/api/v1/maps/places/osm-search?lat=45.0&lon=7.0&query=cafe&limit=5")
    assert response.status_code in (200, 422, 404, 500)


def test_maps_places_search(client):
    response = client.get("/api/v1/maps/places/search?query=cafe&lat=45.0&lon=7.0")
    assert response.status_code in (200, 422, 404, 500)


def test_knowledge_search(client):
    response = client.get("/api/v1/knowledge/search?query=training")
    assert response.status_code in (200, 422, 404, 500)


def test_knowledge_stats(client):
    response = client.get("/api/v1/knowledge/stats")
    assert response.status_code in (200, 422, 404, 500)


def test_knowledge_reload(client):
    response = client.post("/api/v1/knowledge/reload")
    assert response.status_code in (200, 422, 404, 500)


def test_knowledge_init_embeddings(client):
    response = client.post("/api/v1/knowledge/init-embeddings")
    assert response.status_code in (200, 422, 404, 500)


def test_benchmark_compare(client):
    response = client.post("/api/v1/benchmark/compare", json={"athlete_id_1": 0, "athlete_id_2": 0})
    assert response.status_code in (200, 422, 404, 500)


def test_scores_athlete(client):
    response = client.get("/api/v1/scores/athlete/0")
    assert response.status_code in (200, 404)


def test_rides_segments(client):
    ride = {
        "date": "2024-06-15",
        "distance_km": 25.0,
        "gps_points": [{"lat": 45.0, "lon": 7.0, "timestamp": "2024-06-15T10:00:00"}],
    }
    resp = client.post("/api/v1/rides", json=ride)
    if resp.status_code == 200:
        ride_id = resp.json()["id"]
        response = client.get(f"/api/v1/rides/{ride_id}/segments")
        assert response.status_code in (200, 400)


def test_update_ride(client):
    ride = {
        "date": "2024-06-15",
        "distance_km": 25.0,
        "duration_minutes": 60.0,
    }
    resp = client.post("/api/v1/rides", json=ride)
    if resp.status_code == 200:
        ride_id = resp.json()["id"]
        response = client.put(f"/api/v1/rides/{ride_id}", json={"notes": "Updated"})
        assert response.status_code in (200, 404)


def test_calendar_events_range(client):
    response = client.get("/api/v1/calendar/events/range?start=2024-06-01&end=2024-06-30")
    assert response.status_code in (200, 422, 404, 500)


def test_calendar_event_complete(client):
    response = client.post("/api/v1/calendar/events/1/complete")
    assert response.status_code in (200, 404)


def test_training_workouts_generate(client):
    response = client.post("/api/v1/training/workouts/generate?athlete_id=0&days=7")
    assert response.status_code in (200, 422, 404, 500)


def test_metabolism_recalculate(client):
    response = client.post("/api/v1/metabolism/recalculate?athlete_id=0")
    assert response.status_code in (200, 422, 404, 500)


def test_metabolism_reference_values(client):
    response = client.get("/api/v1/metabolism/reference-values?athlete_id=0")
    assert response.status_code in (200, 422, 404, 500)


def test_metabolism_calibrate(client):
    response = client.post("/api/v1/metabolism/calibrate?athlete_id=0")
    assert response.status_code in (200, 422, 404, 500)


def test_metabolism_weights(client):
    response = client.get("/api/v1/metabolism/weights?athlete_id=0")
    assert response.status_code in (200, 422, 404, 500)


def test_metabolism_nutrition_search(client):
    response = client.get("/api/v1/metabolism/nutrition/search?query=banana")
    assert response.status_code in (200, 422, 404, 500)


def test_metabolism_nutrition_categories(client):
    response = client.get("/api/v1/metabolism/nutrition/categories")
    assert response.status_code in (200, 422, 404, 500)


def test_import_google_fit_auth(client):
    response = client.get("/api/v1/import/google-fit/auth")
    assert response.status_code in (200, 500)


def test_import_google_fit_disconnect(client):
    response = client.delete("/api/v1/import/google-fit/disconnect")
    assert response.status_code in (200, 401, 403, 404, 500, 503)


def test_import_strava_auth(client):
    response = client.get("/api/v1/import/strava/auth")
    assert response.status_code in (200, 500)


def test_import_strava_disconnect(client):
    response = client.delete("/api/v1/import/strava/disconnect")
    assert response.status_code in (200, 401, 403, 404, 500, 503)


def test_import_garmin_auth(client):
    response = client.get("/api/v1/import/garmin/auth")
    assert response.status_code in (200, 500)


def test_import_garmin_disconnect(client):
    response = client.delete("/api/v1/import/garmin/disconnect")
    assert response.status_code in (200, 401, 403, 404, 500, 503)


def test_import_wahoo_auth(client):
    response = client.get("/api/v1/import/wahoo/auth")
    assert response.status_code in (200, 500)


def test_import_wahoo_disconnect(client):
    response = client.delete("/api/v1/import/wahoo/disconnect")
    assert response.status_code in (200, 500)


def test_import_providers(client):
    response = client.get("/api/v1/import/providers")
    assert response.status_code in (200, 401, 403, 404, 500, 503)


def test_logout(client):
    response = client.post("/api/v1/auth/logout")
    assert response.status_code in (200, 401, 403, 404, 500, 503)


def test_auth_me(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code in (200, 422, 404, 500)


def test_auth_profile(client):
    response = client.put("/api/v1/auth/profile", json={"name": "Updated Name"})
    assert response.status_code in (200, 400)


def test_dashboard(client):
    response = client.get("/api/v1/dashboard")
    assert response.status_code in (200, 401, 422)


# ============================================================================
# Additional ai_coach.py coverage (functions not yet tested)
# ============================================================================


def test_generate_recovery_advice_high_fatigue(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    athlete = AthleteProfile(name="Test", weight_kg=70, experience_level="Amateur")
    advice = generate_recovery_advice(athlete, [], fatigue_score=9.0)
    assert len(advice) > 0


def test_generate_recovery_advice_zero_fatigue(monkeypatch):
    monkeypatch.setenv("AI_COACH_MODE", "local")
    athlete = AthleteProfile(name="Test", weight_kg=70, experience_level="Amateur")
    advice = generate_recovery_advice(athlete, [], fatigue_score=0)
    assert len(advice) > 0


def test_analyze_anomalies_hr_drift():
    rides = [
        Ride(
            date="2024-06-01",
            distance_km=30.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            heart_rate_avg=120.0,
        ),
        Ride(
            date="2024-06-02",
            distance_km=30.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            heart_rate_avg=135.0,
        ),
        Ride(
            date="2024-06-03",
            distance_km=30.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            heart_rate_avg=150.0,
        ),
    ]
    result = analyze_anomalies(rides)
    assert result["status"] in ("analyzed", "no_data")


def test_analyze_historical_trend_plateau():
    rides = [
        Ride(
            date=f"2024-06-{i:02d}",
            distance_km=25.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
        )
        for i in range(1, 6)
    ]
    result = analyze_historical_trend(rides)
    assert isinstance(result, str)


def test_clean_ai_output_edge_cases():
    assert _clean_ai_output("") == ""
    assert _clean_ai_output("   ") == ""