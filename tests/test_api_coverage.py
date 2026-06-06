"""API coverage tests for endpoints."""
from bike_analyzer.backend.models.models import Ride


def test_rides_crud(client):
    r = client.post("/api/v1/rides", json={
        "date": "2024-06-15",
        "distance_km": 35.0,
        "duration_minutes": 90,
        "avg_speed_kmh": 23.3,
        "calories": 450,
        "elevation_gain_m": 250,
    })
    assert r.status_code in (200, 201)
    ride = r.json()
    ride_id = ride["id"]

    r = client.get("/api/v1/rides")
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    r = client.get(f"/api/v1/rides/{ride_id}")
    assert r.status_code == 200
    assert r.json()["id"] == ride_id

    r = client.delete(f"/api/v1/rides/{ride_id}")
    assert r.status_code == 200
    assert r.json()["deleted"] is True


def test_athlete_crud(client):
    r = client.post("/api/v1/athletes", json={
        "name": "Test Rider",
        "age": 30,
        "weight_kg": 70.0,
        "experience_level": "Amateur",
    })
    assert r.status_code in (200, 201)
    athlete = r.json()
    athlete_id = athlete["id"]

    r = client.get(f"/api/v1/athletes/{athlete_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "Test Rider"

    r = client.put(f"/api/v1/athletes/{athlete_id}", json={"goals": "Gran Fondo"})
    assert r.status_code == 200
    assert r.json()["goals"] == "Gran Fondo"


def test_coach_full(client):
    r = client.get("/api/v1/coach/full")
    assert r.status_code == 200
    data = r.json()
    assert "training_advice" in data
    assert "recovery_advice" in data
    assert "training_scores" in data
    assert "recovery_scores" in data
    assert "charts" in data


def test_knowledge_endpoints(client):
    r = client.get("/api/v1/knowledge")
    assert r.status_code == 200
    assert "topics" in r.json()

    r = client.get("/api/v1/knowledge/search?q=allenamento")
    assert r.status_code == 200
    assert "results" in r.json()


def test_admin_stats(client):
    r = client.get("/api/v1/admin/stats")
    assert r.status_code == 200
    assert "rides_count" in r.json()


def test_admin_indexes(client):
    r = client.post("/api/v1/admin/indexes")
    assert r.status_code == 200
    assert r.json()["status"] == "indexes_created"


def test_export_json(client):
    r = client.get("/api/v1/rides/export/json")
    assert r.status_code == 200
    assert "application/json" in r.headers["content-type"]


def test_export_csv(client):
    r = client.get("/api/v1/rides/export/csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]


def test_ride_analyze(client):
    r = client.post("/api/v1/rides/analyze", json={
        "rides": [
            {"date": "2024-06-15", "distance_km": 35.0, "duration_minutes": 90, "avg_speed_kmh": 23.3, "calories": 450, "elevation_gain_m": 250},
            {"date": "2024-06-14", "distance_km": 40.0, "duration_minutes": 100, "avg_speed_kmh": 24.0, "calories": 500, "elevation_gain_m": 300},
        ]
    })
    assert r.status_code == 200
    assert "total_rides" in r.json()
