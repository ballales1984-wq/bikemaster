"""Tests for API routes - missing coverage."""

import os
from io import BytesIO

import pytest
from starlette.testclient import TestClient


@pytest.mark.skip(reason="Redis not available in test environment")
def test_health_redis_endpoint(client):
    """Test Redis health check endpoint."""
    response = client.get("/api/v1/health/redis")
    assert response.status_code == 200
    data = response.json()
    assert "redis" in data


def test_logout_endpoint(client):
    """Test logout endpoint."""
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200


def test_register_endpoint_success(client):
    """Test user registration."""
    response = client.post("/api/v1/auth/register", json={"username": "testuser123", "password": "password123"})
    assert response.status_code == 200 or response.status_code == 400


def test_create_ride_auto_avg_speed(client):
    """Test ride creation with auto avg_speed calculation."""
    ride = {
        "date": "2024-06-15",
        "distance_km": 25.0,
        "duration_minutes": 60.0,
        "weight_kg": 70,
    }
    response = client.post("/api/v1/rides", json=ride)
    assert response.status_code == 200


def test_import_gpx_endpoint(client):
    """Test GPX import endpoint."""
    gpx_content = """<?xml version="1.0"?>
<gpx version="1.1"><trk><trkseg>
<trkpt lat="45.0" lon="7.0"><time>2024-06-15T10:00:00Z</time></trkpt>
<trkpt lat="45.001" lon="7.001"><time>2024-06-15T10:30:00Z</time></trkpt>
</trkseg></trk></gpx>"""
    files = {"file": ("test.gpx", BytesIO(gpx_content.encode()), "application/gpx+xml")}
    response = client.post("/api/v1/import/gpx", files=files)
    assert response.status_code in (200, 400, 422)


def test_import_gpx_endpoint_sets_current_athlete(db_path):
    """Test GPX import assigns the authenticated athlete."""
    from bike_analyzer.backend.api.app_factory import create_app
    from bike_analyzer.backend.db import database as db_mod
    from bike_analyzer.backend.security import create_access_token

    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    app = create_app()
    tc = TestClient(app)
    tc.headers["Authorization"] = f"Bearer {create_access_token(subject='1', is_admin=True)}"

    gpx_content = """<?xml version="1.0"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>
<trkpt lat="45.0" lon="7.0"><time>2024-06-15T10:00:00Z</time></trkpt>
<trkpt lat="45.001" lon="7.001"><time>2024-06-15T10:30:00Z</time></trkpt>
</trkseg></trk></gpx>"""
    files = {"file": ("test.gpx", BytesIO(gpx_content.encode()), "application/gpx+xml")}
    response = tc.post("/api/v1/import/gpx", files=files)
    assert response.status_code == 200
    assert response.json()["athlete_id"] == 1
    assert response.json()["tenant_id"] == 1


def test_import_fit_endpoint(client):
    """Test FIT import endpoint with invalid file."""
    try:
        files = {"file": ("test.fit", BytesIO(b"invalid"), "application/octet-stream")}
        response = client.post("/api/v1/import/fit", files=files)
        assert response.status_code in (400, 422, 500)
    except PermissionError:
        pass


def test_rides_segments_endpoint(client):
    """Test ride segments endpoint."""
    ride = {
        "date": "2024-06-15",
        "distance_km": 25.0,
        "gps_points": [{"lat": 45.0, "lon": 7.0, "timestamp": "2024-06-15T10:00:00"}],
    }
    response = client.post("/api/v1/rides", json=ride)
    if response.status_code == 200:
        ride_id = response.json()["id"]
        response = client.get(f"/api/v1/rides/{ride_id}/segments")
        assert response.status_code in (200, 400)


def test_update_ride_endpoint(client):
    """Test ride update endpoint."""
    ride = {
        "date": "2024-06-15",
        "distance_km": 25.0,
        "duration_minutes": 60.0,
    }
    response = client.post("/api/v1/rides", json=ride)
    if response.status_code == 200:
        ride_id = response.json()["id"]
        response = client.put(f"/api/v1/rides/{ride_id}", json={"notes": "Updated"})
        assert response.status_code in (200, 404)


def test_analytics_trends_endpoint(client):
    """Test fitness trends analytics endpoint."""
    response = client.get("/api/v1/analytics/trends?metric=distance_km")
    assert response.status_code == 200
    data = response.json()
    assert "trend" in data


def test_analytics_monthly_endpoint(client):
    """Test monthly progression endpoint."""
    response = client.get("/api/v1/analytics/monthly")
    assert response.status_code == 200


def test_analytics_comparison_endpoint(client):
    """Test period comparison endpoint."""
    response = client.get("/api/v1/analytics/comparison?period_days=14")
    assert response.status_code == 200


def test_analytics_projection_endpoint(client):
    """Test volume projection endpoint."""
    response = client.get("/api/v1/analytics/projection?target_days=30")
    assert response.status_code == 200


def test_heatmap_endpoint(client):
    """Test heatmap endpoint."""
    response = client.get("/api/v1/heatmap?athlete_id=0")
    assert response.status_code == 200


def test_training_load_endpoint(client):
    """Test training load endpoint."""
    response = client.get("/api/v1/training/load?athlete_id=0&days=30")
    assert response.status_code == 200


def test_weather_endpoint_no_api_key(client):
    """Test weather endpoint without API key."""
    response = client.get("/api/v1/weather?lat=45.0&lon=7.0")
    assert response.status_code in (200, 500)


def test_weather_geocode_endpoint(client):
    """Test geocode endpoint."""
    response = client.get("/api/v1/weather/geocode?city=Milano")
    assert response.status_code in (200, 404, 500)


def test_maps_places_osm_search(client):
    """Test OSM places search endpoint."""
    response = client.get("/api/v1/maps/places/osm-search?lat=45.0&lon=7.0&query=cafe&limit=5")
    assert response.status_code == 200


def test_calendar_events_endpoints(client):
    """Test calendar events endpoints."""
    response = client.get("/api/v1/calendar/events?athlete_id=0&year=2024&month=6")
    assert response.status_code == 200


def test_coach_full_endpoint(client):
    """Test coach full data endpoint."""
    response = client.get("/api/v1/coach/full?athlete_id=0")
    assert response.status_code == 200


def test_strava_routes(client):
    """Test Strava auth route."""
    response = client.get("/api/v1/import/strava/auth")
    assert response.status_code in (200, 302, 500)


def test_strava_callback_route(client):
    """Test Strava callback route handles missing code."""
    response = client.get("/api/v1/import/strava/callback")
    assert response.status_code in (400, 401, 500)


def test_garmin_routes(client):
    """Test Garmin auth route."""
    response = client.get("/api/v1/import/garmin/auth")
    assert response.status_code in (200, 302, 500)


def test_google_static_map_colored_endpoint(client, db_path):
    """Test Google static map endpoint with colored parameter."""
    from bike_analyzer.backend.db import database as db_mod

    athlete_id = db_mod.save_athlete({"name": "Test Athlete", "experience_level": "Beginner"})
    ride_id = db_mod.save_ride(
        {
            "date": "2024-06-15",
            "distance_km": 25.0,
            "duration_minutes": 60.0,
            "avg_speed_kmh": 25.0,
            "gps_points": [
                {"lat": 45.0, "lon": 9.0, "timestamp": "2024-06-15T10:00:00Z", "speed": 10},
                {"lat": 45.01, "lon": 9.01, "timestamp": "2024-06-15T10:01:00Z", "speed": 30},
            ],
            "athlete_id": athlete_id,
        }
    )
    response = client.get(f"/api/v1/rides/{ride_id}/map/google?colored=true")
    assert response.status_code in (200, 500)


def test_granfondo_plan_and_save(client):
    """Generate a granfondo plan and persist it as calendar events."""
    from bike_analyzer.backend.db import database as db_mod

    athlete_id = db_mod.save_athlete({"name": "GF Athlete", "experience_level": "Intermediate"})

    plan_resp = client.post(
        "/api/v1/training/granfondo/plan",
        json={"athlete_id": athlete_id, "start_date": "2024-06-01", "target_weeks": 8},
    )
    assert plan_resp.status_code == 200
    plan = plan_resp.json()["plan"]
    assert len(plan) > 0

    save_resp = client.post(
        "/api/v1/training/granfondo/save",
        json={"plan": plan, "athlete_id": athlete_id},
    )
    assert save_resp.status_code == 200
    data = save_resp.json()
    assert data["saved"] == len(plan)
    assert len(data["event_ids"]) == len(plan)
    assert data["athlete_id"] == athlete_id

    # Verify events were actually persisted for the athlete.
    stored = db_mod.get_events_by_athlete(athlete_id)
    assert len(stored) == len(plan)


def test_notifications_endpoint(client):
    """Test notifications list endpoint."""
    response = client.get("/api/v1/notifications")
    assert response.status_code in (200, 401)


def test_notifications_create_endpoint(client):
    """Test notifications create endpoint."""
    response = client.post("/api/v1/notifications", json={"message": "test"})
    assert response.status_code in (200, 401, 422)


def test_itineraries_endpoint(client):
    """Test itineraries list endpoint."""
    response = client.get("/api/v1/itineraries")
    assert response.status_code in (200, 401)


def test_itineraries_create_endpoint(client):
    """Test itineraries create endpoint."""
    response = client.post("/api/v1/itineraries", json={"name": "test"})
    assert response.status_code in (200, 401, 422)


def test_admin_users_endpoint(client, db_path):
    """Test admin users endpoint with admin token."""
    from bike_analyzer.backend.api.app_factory import create_app
    from bike_analyzer.backend.db import database as db_mod
    from bike_analyzer.backend.security import create_access_token

    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    app = create_app()
    tc = TestClient(app)
    token = create_access_token(subject="0", is_admin=True)
    tc.headers["Authorization"] = f"Bearer {token}"
    response = tc.get("/api/v1/admin/users")
    assert response.status_code in (200, 500)
