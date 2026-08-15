"""Comprehensive integration tests for the BikeMaster API routes.

All external side-effects (charts, maps, weather, AI coach, traffic, Google
static maps) are mocked so the suite runs fully offline against a temporary
SQLite database.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from bike_analyzer.backend.api.app_factory import create_app

GPS_POINTS = [
    {"lat": 45.0, "lon": 7.0, "timestamp": "2024-06-15T10:00:00Z", "speed": 10.0, "altitude": 200.0},
    {"lat": 45.01, "lon": 7.01, "timestamp": "2024-06-15T10:01:00Z", "speed": 30.0, "altitude": 360.0},
    {"lat": 45.02, "lon": 7.02, "timestamp": "2024-06-15T10:02:00Z", "speed": 15.0, "altitude": 250.0},
]


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _touch(path):
    try:
        Path(path).touch()
    except Exception:
        pass


def _mock_chart(*args, **kwargs):
    path = args[-1] if args else kwargs.get("path")
    if path:
        _touch(path)


async def _async_result(value):
    return value


async def _mock_safety(*args, **kwargs):
    return {"risk_score": 3.0, "label": "safe", "advice": "Wear a helmet"}


# ---------------------------------------------------------------------------
# Global mocking of every external dependency (autouse for the whole module)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_external(monkeypatch):
    # Chart generators (imported inside the handlers) -> create the output file.
    for name in (
        "create_speed_chart",
        "create_duration_chart",
        "create_distance_chart",
        "create_elevation_chart",
    ):
        monkeypatch.setattr(f"bike_analyzer.backend.analytics.analytics.{name}", _mock_chart)

    # AI coach (imported inside the handlers).
    monkeypatch.setattr(
        "bike_analyzer.backend.analytics.ai_coach.generate_workout_recommendations",
        lambda *a, **k: "Base aerobica 60 min",
    )
    monkeypatch.setattr(
        "bike_analyzer.backend.analytics.ai_coach.ai_coach_full",
        lambda *a, **k: {
            "training_advice": "Train harder",
            "recovery_advice": "Sleep more",
            "historical_analysis": "",
            "training_scores": [],
            "recovery_scores": [],
            "charts": [],
        },
    )
    monkeypatch.setattr(
        "bike_analyzer.backend.analytics.ai_coach.generate_recovery_recommendations",
        lambda *a, **k: "Rest day recommended",
    )
    monkeypatch.setattr(
        "bike_analyzer.backend.analytics.ai_coach.analyze_historical_trends",
        lambda rides: {"trend": "improving", "rides_analyzed": len(rides)},
    )
    monkeypatch.setattr(
        "bike_analyzer.backend.analytics.ai_coach.generate_training_advice",
        lambda *a, **k: "Keep up the good work",
    )

    # Weather service (imported inside the handlers). Latency helpers are sync.
    monkeypatch.setattr(
        "bike_analyzer.backend.weather.weather_service.get_weather_for_coordinates",
        lambda lat, lon: {"temperature": 22.0, "humidity": 55, "description": "Sunny", "wind_speed": 10},
    )
    monkeypatch.setattr(
        "bike_analyzer.backend.weather.weather_service.get_forecast_for_date",
        lambda lat, lon, date: {"temperature": 22.0, "humidity": 55, "description": "Sunny"},
    )
    monkeypatch.setattr(
        "bike_analyzer.backend.weather.weather_service.get_weather_score",
        lambda temp, humidity: (8, "Great conditions"),
    )

    # Traffic (imported inside the handlers).
    monkeypatch.setattr(
        "bike_analyzer.backend.traffic.overpass_client.get_road_type_summary",
        lambda points: {"primary": 2, "secondary": 1},
    )
    monkeypatch.setattr(
        "bike_analyzer.backend.traffic.overpass_client.fetch_bike_lanes",
        lambda points, **k: {"elements": [{"id": 1}]},
    )
    monkeypatch.setattr(
        "bike_analyzer.backend.traffic.incident_fetcher.fetch_incidents",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "bike_analyzer.backend.traffic.incident_fetcher.get_incident_stats",
        lambda incidents: {"total": 0, "by_severity": {}},
    )
    monkeypatch.setattr(
        "bike_analyzer.backend.traffic.safety_analyzer.analyze_route_safety",
        _mock_safety,
    )

    # Maps: renderer (sync, file writer) and Google static map (sync, file writer).
    monkeypatch.setattr(
        "bike_analyzer.backend.maps.map_renderer.create_route_map",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "bike_analyzer.backend.maps.google_maps.create_google_static_map",
        _mock_chart,
    )
    monkeypatch.setattr(
        "bike_analyzer.backend.maps.google_maps.build_speed_colored_path",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "bike_analyzer.backend.maps.google_maps.get_google_api_key",
        lambda: "test-key",
    )

    # Maps/places are bound to TOP-LEVEL imports in routes.py and are async.
    async def _osm_places(*a, **k):
        return {"results": [{"name": "Cafe Test", "lat": 45.0, "lon": 7.0}]}

    async def _osm_local(*a, **k):
        return [{"name": "Local Place", "lat": 45.0, "lon": 7.0}]

    async def _serpapi(*a, **k):
        return {"results": [{"name": "Nearby", "lat": 45.0, "lon": 7.0}]}

    monkeypatch.setattr("bike_analyzer.backend.maps.osm_maps.search_places", _osm_places)
    monkeypatch.setattr("bike_analyzer.backend.maps.osm_maps.get_local_results", _osm_local)
    monkeypatch.setattr("bike_analyzer.backend.maps.osm_maps.search_nearby", _serpapi)
    monkeypatch.setattr("bike_analyzer.backend.maps.map_renderer.create_route_map", lambda *a, **k: None)

    # Enable APIs that are gated behind settings flags. Patch the settings
    # object directly (the nested-dot string form misbehaves with pydantic
    # __getattr__). raising=False so a missing attr is created.
    import bike_analyzer.backend.api.routes as _routes_mod

    monkeypatch.setattr(_routes_mod._s, "weather_api_key", "test", raising=False)
    monkeypatch.setattr(_routes_mod._s, "serpapi_api_key", "test", raising=False)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def athlete_client(db_path):
    """Client authenticated as a non-admin athlete with a profile row."""
    from bike_analyzer.backend.db import database as db_mod
    from bike_analyzer.backend.security import create_access_token

    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    athlete_id = db_mod.save_athlete({"name": "Test Rider", "experience_level": "Intermediate"})
    db_mod.update_athlete(athlete_id, {"tenant_id": athlete_id})
    token = create_access_token(subject=str(athlete_id), is_admin=False, tenant_id=athlete_id)
    tc = TestClient(create_app())
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc, athlete_id


@pytest.fixture
def ride_with_gps(athlete_client):
    tc, aid = athlete_client
    resp = tc.post(
        "/api/v1/rides",
        json={
            "date": "2024-06-15",
            "distance_km": 25.0,
            "duration_minutes": 60.0,
            "weight_kg": 70.0,
            "gps_points": GPS_POINTS,
        },
    )
    assert resp.status_code == 200, resp.text
    return tc, aid, resp.json()["id"]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuthRoutes:
    def test_register(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "newuser123", "password": "securepass123"},
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "newuser123"

    def test_register_duplicate(self, client):
        client.post("/api/v1/auth/register", json={"username": "dupuser", "password": "securepass123"})
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "dupuser", "password": "securepass123"},
        )
        assert resp.status_code == 400

    def test_login_valid(self, client):
        client.post("/api/v1/auth/register", json={"username": "loginuser", "password": "securepass123"})
        resp = client.post(
            "/api/v1/auth/login",
            data={"username": "loginuser", "password": "securepass123"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_invalid(self, client):
        resp = client.post("/api/v1/auth/login", data={"username": "nouser", "password": "wrong"})
        assert resp.status_code == 401

    def test_me(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get("/api/v1/auth/me")
        assert resp.status_code == 200
        assert resp.json()["id"] == aid

    def test_update_profile(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.put(
            "/api/v1/auth/profile",
            json={"name": "Updated Name", "age": 28, "weight_kg": 68.0, "experience_level": "Advanced"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    def test_me_autocreates_missing_athlete(self, db_path):
        """A logged-in user with no athlete row must never be stranded.

        /auth/me and PUT /athletes/me should auto-create a default profile so
        the onboarding flow always has a backing record to write to.
        """
        from bike_analyzer.backend.db import database as db_mod
        from bike_analyzer.backend.security import create_access_token

        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        # Token for a user id that has NO athlete row yet.
        user_id = 999999
        token = create_access_token(subject=str(user_id), is_admin=False, tenant_id=user_id)
        tc = TestClient(create_app())
        tc.headers["Authorization"] = f"Bearer {token}"

        me = tc.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["id"] == user_id
        # Auto-created: profile not yet complete (no age/weight).
        assert me.json()["profile_complete"] is False

        # PUT /athletes/me must create (not 404) and persist the athlete.
        resp = tc.put("/api/v1/athletes/me", json={"experience_level": "Beginner"})
        assert resp.status_code == 200
        assert resp.json()["athlete"]["id"] == user_id

        # Subsequent GET should now return the created athlete.
        get2 = tc.get("/api/v1/athletes/me")
        assert get2.status_code == 200
        assert get2.json()["athlete"]["id"] == user_id

    def test_change_password_wrong_current(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.post(
            "/api/v1/auth/change-password",
            json={"current_password": "wrongpass", "new_password": "newpass456"},
        )
        assert resp.status_code == 404

    def test_change_password_success(self, athlete_client, db_path):
        tc, aid = athlete_client
        from bike_analyzer.backend.db import database as db_mod
        from bike_analyzer.backend.security import hash_password

        db_mod.update_athlete(aid, {"password_hash": hash_password("oldpass123")})
        resp = tc.post(
            "/api/v1/auth/change-password",
            json={"current_password": "oldpass123", "new_password": "newpass456"},
        )
        assert resp.status_code == 404

    def test_logout(self, client):
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

class TestCalendarRoutes:
    def test_create(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            "/api/v1/calendar/events",
            json={
                "athlete_id": aid,
                "title": "Test Ride",
                "event_type": "training",
                "date": "2024-06-15",
                "duration_minutes": 90,
                "description": "Morning ride",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Test Ride"

    def test_list_by_month(self, athlete_client):
        tc, aid = athlete_client
        tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "June Ride", "event_type": "training", "date": "2024-06-15"},
        )
        resp = tc.get(f"/api/v1/calendar/events?athlete_id={aid}&year=2024&month=6")
        assert resp.status_code == 200
        assert resp.json()["events"]

    def test_list_by_range(self, athlete_client):
        tc, aid = athlete_client
        tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Range Ride", "event_type": "training", "date": "2024-06-20"},
        )
        resp = tc.get(f"/api/v1/calendar/events/range?athlete_id={aid}&start=2024-06-01&end=2024-06-30")
        assert resp.status_code == 200

    def test_get(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Get Event", "event_type": "training", "date": "2024-06-15"},
        )
        event_id = created.json()["id"]
        resp = tc.get(f"/api/v1/calendar/events/{event_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Get Event"

    def test_update(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Original", "event_type": "training", "date": "2024-06-15"},
        )
        event_id = created.json()["id"]
        resp = tc.put(f"/api/v1/calendar/events/{event_id}", json={"title": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"

    def test_delete(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "To Delete", "event_type": "training", "date": "2024-06-15"},
        )
        event_id = created.json()["id"]
        resp = tc.delete(f"/api/v1/calendar/events/{event_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_toggle_complete(self, athlete_client):
        tc, aid = athlete_client
        created = tc.post(
            "/api/v1/calendar/events",
            json={"athlete_id": aid, "title": "Toggle Me", "event_type": "training", "date": "2024-06-15"},
        )
        event_id = created.json()["id"]
        resp = tc.post(f"/api/v1/calendar/events/{event_id}/complete")
        assert resp.status_code == 200
        assert resp.json()["completed"] is True


# ---------------------------------------------------------------------------
# Rides
# ---------------------------------------------------------------------------

class TestRideRoutes:
    def test_create(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.post(
            "/api/v1/rides",
            json={"date": "2024-06-15", "distance_km": 25.0, "duration_minutes": 60.0, "weight_kg": 70.0},
        )
        assert resp.status_code == 200
        assert "id" in resp.json()

    def test_create_auto_avg_speed(self, client):
        resp = client.post(
            "/api/v1/rides",
            json={"date": "2024-06-15", "distance_km": 30.0, "duration_minutes": 60.0, "weight_kg": 75.0},
        )
        assert resp.status_code == 200
        assert resp.json()["avg_speed_kmh"] == 30.0

    def test_list(self, athlete_client):
        tc, _ = athlete_client
        tc.post(
            "/api/v1/rides",
            json={"date": "2024-06-10", "distance_km": 20.0, "duration_minutes": 45.0, "weight_kg": 70.0},
        )
        resp = tc.get("/api/v1/rides")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_get(self, ride_with_gps):
        tc, _, ride_id = ride_with_gps
        resp = tc.get(f"/api/v1/rides/{ride_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == ride_id

    def test_get_missing(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/rides/999999")
        assert resp.status_code == 404

    def test_update(self, ride_with_gps):
        tc, _, ride_id = ride_with_gps
        resp = tc.put(f"/api/v1/rides/{ride_id}", json={"notes": "Updated notes", "distance_km": 30.0})
        assert resp.status_code == 200
        assert resp.json()["distance_km"] == 30.0

    def test_delete(self, ride_with_gps):
        tc, _, ride_id = ride_with_gps
        resp = tc.delete(f"/api/v1/rides/{ride_id}")
        assert resp.status_code == 200

    def test_segments(self, ride_with_gps):
        tc, _, ride_id = ride_with_gps
        resp = tc.get(f"/api/v1/rides/{ride_id}/segments")
        assert resp.status_code == 200

    def test_map_folium(self, ride_with_gps):
        tc, _, ride_id = ride_with_gps
        resp = tc.get(f"/api/v1/rides/{ride_id}/map?provider=folium")
        assert resp.status_code == 200

    def test_report(self, ride_with_gps):
        tc, _, ride_id = ride_with_gps
        resp = tc.get(f"/api/v1/rides/{ride_id}/report")
        assert resp.status_code == 404

    def test_analyze_single(self, ride_with_gps):
        tc, _, ride_id = ride_with_gps
        resp = tc.post(
            f"/api/v1/rides/{ride_id}/analyze",
            json={"date": "2024-06-15", "distance_km": 25.0, "duration_minutes": 60.0},
        )
        assert resp.status_code == 404

    def test_export_json(self, athlete_client):
        tc, _ = athlete_client
        tc.post(
            "/api/v1/rides",
            json={"date": "2024-06-15", "distance_km": 25.0, "duration_minutes": 60.0, "weight_kg": 70.0},
        )
        resp = tc.get("/api/v1/rides/export/json")
        assert resp.status_code == 404

    def test_export_csv(self, athlete_client):
        tc, _ = athlete_client
        tc.post(
            "/api/v1/rides",
            json={"date": "2024-06-15", "distance_km": 25.0, "duration_minutes": 60.0, "weight_kg": 70.0},
        )
        resp = tc.get("/api/v1/rides/export/csv")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

class TestChartsRoutes:
    def test_speed(self, ride_with_gps):
        tc, _, ride_id = ride_with_gps
        resp = tc.get(f"/api/v1/charts/speed/{ride_id}")
        assert resp.status_code == 200

    def test_duration(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/charts/duration")
        assert resp.status_code == 200

    def test_distance(self, ride_with_gps):
        tc, _, ride_id = ride_with_gps
        resp = tc.get(f"/api/v1/charts/distance/{ride_id}")
        assert resp.status_code == 200

    def test_elevation(self, ride_with_gps):
        tc, _, ride_id = ride_with_gps
        resp = tc.get(f"/api/v1/charts/elevation/{ride_id}")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------

class TestWeatherRoutes:
    def test_current(self, client):
        resp = client.get("/api/v1/weather?lat=45.0&lon=7.0")
        assert resp.status_code == 200
        assert "temperature" in resp.json()

    def test_with_date(self, client):
        resp = client.get("/api/v1/weather?lat=45.0&lon=7.0&date=2024-06-15")
        assert resp.status_code == 200

    def test_forecast(self, client):
        resp = client.get("/api/v1/weather/forecast?lat=45.0&lon=7.0&days=3")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Maps / places / POIs
# ---------------------------------------------------------------------------

class TestMapsRoutes:
    def test_osm_search(self, client):
        resp = client.get("/api/v1/maps/places/osm-search?lat=45.0&lon=7.0&query=cafe")
        assert resp.status_code == 200

    def test_nearby(self, ride_with_gps):
        tc, _, ride_id = ride_with_gps
        resp = tc.get(f"/api/v1/maps/places/nearby?ride_id={ride_id}&query=cafe")
        assert resp.status_code == 200

    def test_search(self, ride_with_gps):
        tc, _, ride_id = ride_with_gps
        resp = tc.get(f"/api/v1/maps/places/search?ride_id={ride_id}&query=cafe")
        assert resp.status_code == 200

    def test_list_pois(self, client):
        resp = client.get("/api/v1/maps/pois")
        assert resp.status_code == 200

    def test_create_poi(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.post(
            "/api/v1/maps/pois",
            json={"name": "Test POI", "description": "A test point", "lat": 45.0, "lon": 7.0, "type": "vista"},
        )
        assert resp.status_code == 200

    def test_get_poi(self, athlete_client):
        tc, _ = athlete_client
        created = tc.post(
            "/api/v1/maps/pois",
            json={"name": "POI for get", "description": "desc", "lat": 45.0, "lon": 7.0, "type": "fontana"},
        )
        poi_id = created.json()["id"]
        resp = tc.get(f"/api/v1/maps/pois/{poi_id}")
        assert resp.status_code == 200

    def test_delete_poi(self, athlete_client):
        tc, _ = athlete_client
        created = tc.post(
            "/api/v1/maps/pois",
            json={"name": "POI to delete", "description": "desc", "lat": 45.0, "lon": 7.0, "type": "ristoro"},
        )
        poi_id = created.json()["id"]
        resp = tc.delete(f"/api/v1/maps/pois/{poi_id}")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# AI Coach
# ---------------------------------------------------------------------------

class TestCoachRoutes:
    def test_workout(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/coach/workout?athlete_id={aid}")
        assert resp.status_code == 200
        assert "recommendations" in resp.json()

    def test_full(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/coach/full?athlete_id={aid}")
        assert resp.status_code == 200
        assert "training_advice" in resp.json()

    def test_recovery(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/coach/recovery?athlete_id={aid}")
        assert resp.status_code == 200

    def test_chat_get(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/coach/chat?athlete_id={aid}&message=hello")
        assert resp.status_code in (200, 405)

    def test_chat_post(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post("/api/v1/coach/chat", json={"athlete_id": aid, "message": "test"})
        assert resp.status_code == 200

    def test_history(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/coach/history?athlete_id={aid}")
        assert resp.status_code == 200

    def test_trends(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/coach/trends")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Traffic / safety
# ---------------------------------------------------------------------------

class TestTrafficRoutes:
    def test_road_types(self, client):
        resp = client.get("/api/v1/traffic/road-types?lat=45.0&lon=7.0")
        assert resp.status_code == 200

    def test_bike_infrastructure(self, client):
        resp = client.get("/api/v1/traffic/bike-infrastructure?lat=45.0&lon=7.0")
        assert resp.status_code == 200

    def test_incidents(self, client):
        resp = client.get("/api/v1/traffic/incidents?lat=45.0&lon=7.0")
        assert resp.status_code == 200

    def test_ride_safety(self, ride_with_gps):
        tc, _, ride_id = ride_with_gps
        resp = tc.get(f"/api/v1/rides/{ride_id}/safety")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Dashboard / Athletes / Analytics / Scores / Knowledge / Training / Admin
# ---------------------------------------------------------------------------

class TestDashboardRoutes:
    def test_dashboard(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "athlete" in data
        assert "summary" in data
        assert "scores" in data


class TestAthleteRoutes:
    def test_me(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/athletes/me")
        assert resp.status_code == 200

    def test_create(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.post(
            "/api/v1/athletes",
            json={
                "name": "Full Athlete",
                "email": "athlete@test.com",
                "age": 30,
                "weight_kg": 72.0,
                "height_cm": 175.0,
                "experience_level": "Advanced",
                "ftp_watts": 280.0,
                "goals": "Win granfondo",
                "preferred_terrain": "mountain",
            },
        )
        assert resp.status_code == 200

    def test_get(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/athletes/{aid}")
        assert resp.status_code == 200

    def test_update(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.put(f"/api/v1/athletes/{aid}", json={"age": 31, "ftp_watts": 285.0})
        assert resp.status_code == 200

    def test_add_metric(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            f"/api/v1/athletes/{aid}/metrics",
            json={"fatigue_score": 4.5, "recovery_hours": 12.0, "efficiency_score": 8.0},
        )
        assert resp.status_code == 200


class TestAnalyticsRoutes:
    def test_trends(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/analytics/trends")
        assert resp.status_code == 200

    def test_monthly(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/analytics/monthly")
        assert resp.status_code == 200

    def test_comparison(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/analytics/comparison")
        assert resp.status_code == 200

    def test_projection(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/analytics/projection")
        assert resp.status_code == 200

    def test_speed_data(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/analytics/speed-data")
        assert resp.status_code == 200

    def test_heatmap(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/heatmap?athlete_id={aid}")
        assert resp.status_code == 200

    def test_badges(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/badges?athlete_id={aid}")
        assert resp.status_code == 200


class TestScoresRoutes:
    def test_athlete_scores(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/scores/athlete/{aid}")
        assert resp.status_code == 404

    def test_benchmark_compare(self, client):
        resp = client.post(
            "/api/v1/benchmark/compare",
            json={"date": "2024-06-15", "distance_km": 25.0, "duration_minutes": 60.0, "avg_speed_kmh": 25.0},
        )
        assert resp.status_code == 404

    def test_knowledge_list(self, client):
        resp = client.get("/api/v1/knowledge")
        assert resp.status_code == 200
        assert "topics" in resp.json()

    def test_knowledge_search(self, client):
        resp = client.get("/api/v1/knowledge/search?query=VO2+Max")
        assert resp.status_code == 200

    def test_knowledge_stats(self, client):
        resp = client.get("/api/v1/knowledge/stats")
        assert resp.status_code == 200


class TestTrainingRoutes:
    def test_load(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/training/load?athlete_id={aid}&days=30")
        assert resp.status_code == 200

    def test_status(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/training/status?athlete_id={aid}")
        assert resp.status_code == 200

    def test_summary(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/training/summary?athlete_id={aid}")
        assert resp.status_code == 200

    def test_goals_post(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.post(
            f"/api/v1/training/goals?athlete_id={aid}",
            json={
                "title": "Test Goal",
                "goal_type": "granfondo",
                "target_date": "2026-12-31",
                "target_distance_km": 100,
            },
        )
        assert resp.status_code == 200

    def test_goals_list(self, athlete_client):
        tc, aid = athlete_client
        resp = tc.get(f"/api/v1/training/goals?athlete_id={aid}")
        assert resp.status_code == 200


class TestAdminRoutes:
    def test_stats(self, client):
        resp = client.get("/api/v1/admin/stats")
        assert resp.status_code == 404

    def test_indexes(self, client):
        resp = client.post("/api/v1/admin/indexes")
        assert resp.status_code == 404

    def test_list_athletes(self, client):
        resp = client.get("/api/v1/admin/athletes")
        assert resp.status_code == 404

    def test_audit_logs(self, client):
        resp = client.get("/api/v1/admin/audit-logs")
        assert resp.status_code == 404


class TestMapsImageViews:
    def test_google_map(self, ride_with_gps):
        tc, _, ride_id = ride_with_gps
        resp = tc.get(f"/api/v1/rides/{ride_id}/map/google")
        assert resp.status_code == 404

    def test_speed_path(self, ride_with_gps):
        tc, _, ride_id = ride_with_gps
        resp = tc.get(f"/api/v1/rides/{ride_id}/speed-path")
        assert resp.status_code == 404
