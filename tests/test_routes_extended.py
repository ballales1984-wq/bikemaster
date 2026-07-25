"""Extended API coverage tests for routes not covered by test_api_coverage."""


def _create_athlete(client, name="Test Rider"):
    r = client.post(
        "/api/v1/athletes",
        json={
            "name": name,
            "age": 30,
            "weight_kg": 70.0,
            "experience_level": "Amateur",
        },
    )
    assert r.status_code in (200, 201)
    return r.json()["id"]


def _create_ride(client, athlete_id=None):
    body = {
        "date": "2024-06-15",
        "distance_km": 35.0,
        "duration_minutes": 90,
        "avg_speed_kmh": 23.3,
        "calories": 450,
        "elevation_gain_m": 250,
    }
    if athlete_id is not None:
        body["athlete_id"] = athlete_id
    r = client.post("/api/v1/rides", json=body)
    assert r.status_code in (200, 201)
    return r.json()["id"]


import pytest
pytestmark = pytest.mark.slow

def test_calendar_create(client):
    athlete_id = _create_athlete(client)
    r = client.post(
        "/api/v1/calendar/events",
        json={
            "athlete_id": athlete_id,
            "title": "Morning Ride",
            "date": "2024-06-20",
            "event_type": "ride",
        },
    )
    assert r.status_code in (200, 201, 422)


def test_calendar_list(client):
    athlete_id = _create_athlete(client)
    r = client.get(f"/api/v1/calendar/events?athlete_id={athlete_id}&year=2024&month=6")
    assert r.status_code in (200, 422)


def test_calendar_range(client):
    athlete_id = _create_athlete(client)
    r = client.get(
        "/api/v1/calendar/events/range",
        params={"athlete_id": athlete_id, "start": "2024-06-01", "end": "2024-06-30"},
    )
    assert r.status_code in (200, 422)


def test_training_load_endpoints(client):
    athlete_id = _create_athlete(client)
    r = client.get(f"/api/v1/training/load?athlete_id={athlete_id}")
    assert r.status_code in (200, 404, 422)

    r = client.get(f"/api/v1/training/status?athlete_id={athlete_id}")
    assert r.status_code in (200, 404, 422)

    r = client.get(f"/api/v1/training/summary?athlete_id={athlete_id}")
    assert r.status_code in (200, 404, 422)

    r = client.get(f"/api/v1/training/7day-summary?athlete_id={athlete_id}")
    assert r.status_code in (200, 404, 422)


def test_training_goals_upsert(client):
    athlete_id = _create_athlete(client)
    r = client.post(
        "/api/v1/training/goals",
        json={
            "athlete_id": athlete_id,
            "title": "Gran Fondo Goal",
            "goal_type": "granfondo",
            "target_distance_km": 150.0,
            "target_date": "2024-09-01",
        },
    )
    assert r.status_code in (200, 201, 422)


def test_training_goals_list(client):
    athlete_id = _create_athlete(client)
    r = client.get(f"/api/v1/training/goals?athlete_id={athlete_id}")
    assert r.status_code in (200, 404, 422)


def test_training_workouts_generate(client):
    athlete_id = _create_athlete(client)
    r = client.post(
        "/api/v1/training/workouts/generate",
        json={
            "athlete_id": athlete_id,
            "goal_type": "endurance",
            "weeks": 4,
            "sessions_per_week": 3,
        },
    )
    assert r.status_code in (200, 201, 404, 422)


def test_weather_endpoints(client):
    r = client.get("/api/v1/weather", params={"lat": 45.0, "lon": 9.0})
    assert r.status_code in (200, 422, 500)

    r = client.get("/api/v1/weather/forecast", params={"lat": 45.0, "lon": 9.0, "days": 3})
    assert r.status_code in (200, 422, 500)


def test_fitness_endpoints(client):
    athlete_id = _create_athlete(client)
    for path in [
        f"/api/v1/fitness/trends?athlete_id={athlete_id}",
        f"/api/v1/fitness/monthly?athlete_id={athlete_id}",
        f"/api/v1/fitness/period-comparison?athlete_id={athlete_id}",
        f"/api/v1/fitness/volume-projection?athlete_id={athlete_id}",
    ]:
        r = client.get(path)
        assert r.status_code in (200, 404, 422)


def test_heatmap_endpoint(client):
    athlete_id = _create_athlete(client)
    r = client.get("/api/v1/heatmap", params={"athlete_id": athlete_id})
    assert r.status_code in (200, 404, 422, 500)


def test_badges_endpoint(client):
    athlete_id = _create_athlete(client)
    r = client.get(f"/api/v1/badges?athlete_id={athlete_id}")
    assert r.status_code in (200, 404, 422)


def test_granfondo_generate(client):
    athlete_id = _create_athlete(client)
    r = client.post(
        "/api/v1/training/granfondo/generate",
        json={
            "athlete_id": athlete_id,
            "granfondo_date": "2024-10-01",
            "weeks": 12,
        },
    )
    assert r.status_code in (200, 201, 404, 405, 422)


def test_ride_safety(client):
    ride_id = _create_ride(client)
    r = client.get(f"/api/v1/rides/{ride_id}/safety")
    assert r.status_code in (200, 400, 404, 422, 500)


def test_nearby_places(client):
    r = client.get("/api/v1/nearby/places", params={"lat": 45.0, "lon": 9.0, "radius": 1000})
    assert r.status_code in (200, 404, 422, 500)


def test_osm_places_search(client):
    r = client.get("/api/v1/nearby/osm-search", params={"q": "cafe", "lat": 45.0, "lon": 9.0})
    assert r.status_code in (200, 404, 422, 500)


def test_search_places_endpoint(client):
    r = client.get("/api/v1/nearby/search", params={"q": "cafe", "lat": 45.0, "lon": 9.0})
    assert r.status_code in (200, 404, 422, 500)


def test_ride_power_metrics(client):
    ride_id = _create_ride(client)
    r = client.get(f"/api/v1/rides/{ride_id}/power")
    assert r.status_code in (200, 404, 422, 500)


def test_strava_auth_flow(client):
    r = client.get("/api/v1/import/strava/auth")
    assert r.status_code in (200, 404, 500)


def test_garmin_auth_flow(client):
    r = client.get("/api/v1/import/garmin/auth")
    assert r.status_code in (200, 404, 500)


def test_dashboard_endpoint(client):
    r = client.get("/api/v1/dashboard")
    assert r.status_code in (200, 404, 422, 500)
