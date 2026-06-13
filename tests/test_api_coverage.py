"""API coverage tests for endpoints."""


def test_rides_crud(client):
    r = client.post(
        "/api/v1/rides",
        json={
            "date": "2024-06-15",
            "distance_km": 35.0,
            "duration_minutes": 90,
            "avg_speed_kmh": 23.3,
            "calories": 450,
            "elevation_gain_m": 250,
        },
    )
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
    r = client.post(
        "/api/v1/athletes",
        json={
            "name": "Test Rider",
            "age": 30,
            "weight_kg": 70.0,
            "experience_level": "Amateur",
        },
    )
    assert r.status_code in (200, 201)
    athlete = r.json()
    athlete_id = athlete["id"]

    r = client.get("/api/v1/athletes")
    assert r.status_code == 200
    assert r.json()["athletes"][0]["id"] == athlete_id

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
    r = client.post(
        "/api/v1/rides/analyze",
        json={
            "rides": [
                {
                    "date": "2024-06-15",
                    "distance_km": 35.0,
                    "duration_minutes": 90,
                    "avg_speed_kmh": 23.3,
                    "calories": 450,
                    "elevation_gain_m": 250,
                },
                {
                    "date": "2024-06-14",
                    "distance_km": 40.0,
                    "duration_minutes": 100,
                    "avg_speed_kmh": 24.0,
                    "calories": 500,
                    "elevation_gain_m": 300,
                },
            ]
        },
    )
    assert r.status_code == 200
    assert "total_rides" in r.json()


def test_health_endpoints(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    r = client.get("/api/v1/health/detailed")
    assert r.status_code == 200
    assert r.json()["service"] == "bikemaster"


def test_rides_count(client):
    r = client.get("/api/v1/rides?size=1")
    assert r.status_code == 200


def test_rides_sort(client):
    r = client.get("/api/v1/rides?sort=distance")
    assert r.status_code == 200
    r = client.get("/api/v1/rides?sort=duration")
    assert r.status_code == 200


def test_knowledge_stats(client):
    r = client.get("/api/v1/knowledge/stats")
    assert r.status_code == 200


def test_coach_page(client):
    r = client.get("/api/v1/coach/page")
    assert r.status_code in (200, 404)


def test_coach_trends(client):
    r = client.get("/api/v1/coach/trends")
    assert r.status_code == 200


def test_coach_workout(client):
    r = client.get("/api/v1/coach/workout")
    assert r.status_code == 200


def test_benchmark_compare(client):
    r = client.post(
        "/api/v1/benchmark/compare",
        json={"distance_km": 50.0, "duration_minutes": 120, "avg_speed_kmh": 25.0},
    )
    assert r.status_code == 200


def test_rides_report(client):
    ride = client.post(
        "/api/v1/rides",
        json={
            "date": "2024-06-15",
            "distance_km": 25.0,
            "duration_minutes": 60,
            "calories": 400,
        },
    )
    ride_id = ride.json()["id"]
    r = client.get(f"/api/v1/rides/{ride_id}/report")
    assert r.status_code == 200
    assert "report" in r.json()


def test_athlete_scores(client):
    athlete = client.post(
        "/api/v1/athletes",
        json={
            "name": "Score Test",
            "age": 25,
            "weight_kg": 65.0,
            "experience_level": "Intermediate",
        },
    )
    athlete_id = athlete.json()["id"]
    r = client.get(f"/api/v1/scores/athlete/{athlete_id}")
    assert r.status_code == 200


def test_coach_chat(client):
    athlete = client.post(
        "/api/v1/athletes",
        json={
            "name": "Chat Test",
            "age": 25,
            "weight_kg": 70.0,
            "experience_level": "Beginner",
        },
    )
    athlete_id = athlete.json()["id"]
    r = client.post(f"/api/v1/coach/chat?athlete_id={athlete_id}&message=test")
    assert r.status_code == 200
    assert "response" in r.json()


def test_coach_history(client):
    athlete = client.post(
        "/api/v1/athletes",
        json={
            "name": "History Test",
            "age": 25,
            "weight_kg": 70.0,
            "experience_level": "Beginner",
        },
    )
    athlete_id = athlete.json()["id"]
    r = client.get(f"/api/v1/coach/history?athlete_id={athlete_id}")
    assert r.status_code == 200


def test_ride_map_endpoint(client):
    ride = client.post(
        "/api/v1/rides",
        json={
            "date": "2024-06-15",
            "distance_km": 25.0,
            "duration_minutes": 60,
            "calories": 400,
            "gps_points": [
                {"lat": 45.0, "lon": 9.0, "timestamp": "2024-06-15T10:00:00Z", "speed": 25.0},
                {"lat": 45.01, "lon": 9.01, "timestamp": "2024-06-15T10:01:00Z", "speed": 25.0},
            ],
        },
    )
    ride_id = ride.json()["id"]
    r = client.post(f"/api/v1/rides/{ride_id}/map")
    assert r.status_code == 200


def test_ride_single_analyze(client):
    ride = client.post(
        "/api/v1/rides",
        json={
            "date": "2024-06-15",
            "distance_km": 25.0,
            "duration_minutes": 60,
            "calories": 400,
        },
    )
    ride_id = ride.json()["id"]
    r = client.post(
        f"/api/v1/rides/{ride_id}/analyze",
        json={
            "date": "2024-06-15",
            "distance_km": 25.0,
            "duration_minutes": 60,
            "calories": 400,
        },
    )
    assert r.status_code == 200


def test_coach_recovery(client):
    r = client.get("/api/v1/coach/recovery?fatigue_score=7.0")
    assert r.status_code == 200
    assert "recommendations" in r.json()


def test_google_fit_auth(client):
    r = client.get("/api/v1/import/google-fit/auth?client_id=test_client")
    assert r.status_code == 200
    assert "auth_url" in r.json()


def test_knowledge_reload(client):
    r = client.post("/api/v1/knowledge/reload")
    assert r.status_code == 200


def test_knowledge_search_empty(client):
    r = client.get("/api/v1/knowledge/search?q=")
    assert r.status_code == 200
    assert r.json()["count"] == 0


def test_rides_update(client):
    ride = client.post(
        "/api/v1/rides",
        json={
            "date": "2024-06-15",
            "distance_km": 25.0,
            "duration_minutes": 60,
            "calories": 400,
        },
    )
    ride_id = ride.json()["id"]
    r = client.put(f"/api/v1/rides/{ride_id}", json={"notes": "Updated ride"})
    assert r.status_code == 200


def test_athlete_metrics(client):
    athlete = client.post(
        "/api/v1/athletes",
        json={
            "name": "Metrics Test",
            "age": 25,
            "weight_kg": 70.0,
            "experience_level": "Beginner",
        },
    )
    athlete_id = athlete.json()["id"]
    client.post(
        f"/api/v1/athletes/{athlete_id}/metrics",
        json={
            "type": "ftp",
            "value": 250.0,
        },
    )
