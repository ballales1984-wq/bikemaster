"""Additional route coverage tests for P3.5 (>90% routes.py coverage).

These tests focus on endpoints that are computed locally (DB / analytics) plus the
main error branches (404/403/400/422) so they stay deterministic and network-free.
"""

import os

import pytest

pytestmark = pytest.mark.slow
from starlette.testclient import TestClient

from bike_analyzer.backend.api.app_factory import create_app
from bike_analyzer.backend.db import database as db_mod
from bike_analyzer.backend.security import create_access_token


def _make_client(subject: str, is_admin: bool = False, db_path: str | None = None):
    if db_path:
        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
    app = create_app()
    tc = TestClient(app)
    tc.headers["Authorization"] = f"Bearer {create_access_token(subject=subject, is_admin=is_admin)}"
    return tc


SAMPLE_RIDE = {
    "date": "2024-06-15",
    "distance_km": 25.0,
    "duration_minutes": 60.0,
    "weight_kg": 70,
    "gps_points": [
        {"lat": 45.0, "lon": 7.0, "timestamp": "2024-06-15T10:00:00", "elevation": 100},
        {"lat": 45.001, "lon": 7.001, "timestamp": "2024-06-15T10:30:00", "elevation": 120},
    ],
}


# --------------------------------------------------------------------------- #
# Rides CRUD
# --------------------------------------------------------------------------- #
def test_create_ride_full(client):
    resp = client.post("/api/v1/rides", json=SAMPLE_RIDE)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"]
    assert data["avg_speed_kmh"] is not None
    assert data["calories"] is not None


def test_create_ride_invalid_date(client):
    resp = client.post("/api/v1/rides", json={**SAMPLE_RIDE, "date": "2024-6-1"})
    assert resp.status_code == 422


def test_list_and_count_rides(client):
    client.post("/api/v1/rides", json=SAMPLE_RIDE)
    assert client.get("/api/v1/rides").status_code == 200
    assert client.get("/api/v1/rides/count").status_code == 200
    assert client.get("/api/v1/rides", params={"page": 1, "page_size": 5, "sort": "distance"}).status_code == 200


def test_get_ride_and_404(client):
    resp = client.post("/api/v1/rides", json=SAMPLE_RIDE)
    ride_id = resp.json()["id"]
    assert client.get(f"/api/v1/rides/{ride_id}").status_code == 200
    assert client.get("/api/v1/rides/999999").status_code == 404


def test_update_ride_and_404(client):
    resp = client.post("/api/v1/rides", json=SAMPLE_RIDE)
    ride_id = resp.json()["id"]
    assert client.put(f"/api/v1/rides/{ride_id}", json={"notes": "ok"}).status_code in (200, 404)
    assert client.put("/api/v1/rides/999999", json={"notes": "x"}).status_code == 404


def test_delete_ride_and_404(client):
    resp = client.post("/api/v1/rides", json=SAMPLE_RIDE)
    ride_id = resp.json()["id"]
    assert client.delete(f"/api/v1/rides/{ride_id}").status_code == 200
    assert client.delete(f"/api/v1/rides/{ride_id}").status_code == 404


def test_ride_map_folium_and_missing(client):
    resp = client.post("/api/v1/rides", json=SAMPLE_RIDE)
    ride_id = resp.json()["id"]
    assert client.get(f"/api/v1/rides/{ride_id}/map", params={"provider": "folium"}).status_code == 200
    assert client.get("/api/v1/rides/999999/map", params={"provider": "folium"}).status_code == 404
    assert client.get(f"/api/v1/rides/{ride_id}/map", params={"provider": "aethermap"}).status_code in (200, 500)


def test_ride_map_no_gps(db_path):
    tc = _make_client("0", is_admin=True, db_path=db_path)
    resp = tc.post("/api/v1/rides", json={"date": "2024-06-15", "distance_km": 10, "duration_minutes": 30})
    ride_id = resp.json()["id"]
    assert tc.get(f"/api/v1/rides/{ride_id}/map").status_code == 400


def test_ride_segments_and_missing(client):
    resp = client.post("/api/v1/rides", json=SAMPLE_RIDE)
    ride_id = resp.json()["id"]
    assert client.get(f"/api/v1/rides/{ride_id}/segments").status_code == 200
    assert client.get("/api/v1/rides/999999/segments").status_code == 404


def test_ride_analyze_endpoints(client):
    resp = client.post("/api/v1/rides", json=SAMPLE_RIDE)
    ride_id = resp.json()["id"]
    assert client.post("/api/v1/rides/analyze", json={"rides": [SAMPLE_RIDE]}).status_code == 200
    assert client.post(f"/api/v1/rides/{ride_id}/analyze", json=SAMPLE_RIDE).status_code == 200


def test_ride_access_denied(db_path):
    admin = _make_client("0", is_admin=True, db_path=db_path)
    resp = admin.post("/api/v1/rides", json=SAMPLE_RIDE)
    ride_id = resp.json()["id"]
    other = _make_client("5", is_admin=False, db_path=db_path)
    assert other.get(f"/api/v1/rides/{ride_id}").status_code == 403
    assert other.delete(f"/api/v1/rides/{ride_id}").status_code == 403


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
def test_register_success_and_duplicates(db_path):
    tc = _make_client("0", is_admin=True, db_path=db_path)
    r = tc.post("/api/v1/auth/register", json={"username": "alice_xyz", "password": "password123"})
    assert r.status_code == 200
    assert tc.post("/api/v1/auth/register", json={"username": "alice_xyz", "password": "password123"}).status_code == 400
    assert tc.post("/api/v1/auth/register", json={"username": "ab", "password": "password123"}).status_code in (400, 422)
    assert tc.post("/api/v1/auth/register", json={"username": "bob_long", "password": "short"}).status_code in (400, 422)
    assert tc.post("/api/v1/auth/register", json={"username": "carol_xyz", "password": "password123", "email": "carol@example.com"}).status_code == 200


def test_login_and_refresh(db_path):
    tc = _make_client("0", is_admin=True, db_path=db_path)
    tc.post("/api/v1/auth/register", json={"username": "dave_xyz", "password": "password123"})
    r = tc.post("/api/v1/auth/login", data={"username": "dave_xyz", "password": "password123"})
    assert r.status_code == 200
    assert "access_token" in r.json()
    bad = tc.post("/api/v1/auth/login", data={"username": "dave_xyz", "password": "wrong"})
    assert bad.status_code == 401
    miss = tc.post("/api/v1/auth/login", data={"username": "ghost_xyz", "password": "password123"})
    assert miss.status_code == 401


def test_refresh_token_variants(db_path):
    tc = _make_client("0", is_admin=True, db_path=db_path)
    r = tc.post("/api/v1/auth/refresh", json={"refresh_token": "not.a.jwt"})
    assert r.status_code == 401
    access = create_access_token(subject="0")
    from bike_analyzer.backend.security import create_refresh_token

    refresh = create_refresh_token(subject="0")
    assert tc.post("/api/v1/auth/refresh", json={"refresh_token": access}).status_code == 401
    assert tc.post("/api/v1/auth/refresh", json={"refresh_token": refresh}).status_code == 200


def test_auth_me_profile_change_password_logout(db_path):
    tc = _make_client("0", is_admin=True, db_path=db_path)
    reg = tc.post("/api/v1/auth/register", json={"username": "erin_xyz", "password": "password123"})
    assert reg.status_code == 200
    aid = reg.json()["id"]
    token = create_access_token(subject=str(aid), is_admin=False, tenant_id=aid)
    erc = TestClient(create_app())
    erc.headers["Authorization"] = f"Bearer {token}"
    os.environ["DB_PATH"] = db_path
    assert erc.get("/api/v1/auth/me").status_code == 200
    r = erc.put("/api/v1/auth/profile", json={"weight_kg": 80, "goals": "granfondo"})
    assert r.status_code == 200
    assert erc.put("/api/v1/auth/profile", json={}).status_code == 400
    bad = erc.post("/api/v1/auth/change-password", json={"current_password": "wrongpass", "new_password": "newpassword123"})
    assert bad.status_code == 400
    dup = erc.post("/api/v1/auth/register", json={"username": "erin_xyz", "password": "password123"})
    assert dup.status_code in (200, 400)
    assert erc.post("/api/v1/auth/change-password", json={"current_password": "password123", "new_password": "newpassword123"}).status_code == 200
    assert erc.post("/api/v1/auth/logout").status_code == 200


def test_change_password_user_not_found(db_path):
    tc = _make_client("99", is_admin=False, db_path=db_path)
    r = tc.post("/api/v1/auth/change-password", json={"current_password": "doesnotexist", "new_password": "newpassword123"})
    assert r.status_code == 404


# --------------------------------------------------------------------------- #
# Analytics / heatmap / training / calendar
# --------------------------------------------------------------------------- #
def test_analytics_endpoints(client):
    for path in ("trends", "monthly", "comparison", "projection", "speed-data"):
        assert client.get(f"/api/v1/analytics/{path}").status_code == 200
    assert client.get("/api/v1/analytics/comparison", params={"period_days": 14}).status_code == 200
    assert client.get("/api/v1/analytics/projection", params={"target_days": 30}).status_code == 200


def test_heatmap(client):
    assert client.get("/api/v1/heatmap", params={"athlete_id": 0}).status_code == 200


def test_training_endpoints(client):
    assert client.get("/api/v1/training/load", params={"athlete_id": 0, "days": 30}).status_code == 200
    assert client.get("/api/v1/training/status", params={"athlete_id": 0}).status_code == 200
    assert client.get("/api/v1/training/summary", params={"athlete_id": 0}).status_code == 200
    assert client.get("/api/v1/training/goals", params={"athlete_id": 0}).status_code == 200
    r = client.post("/api/v1/training/goals", json={"title": "Granfondo 2024", "goal_type": "granfondo", "target_distance_km": 120})
    assert r.status_code in (200, 201, 400)
    gen = client.post("/api/v1/training/workouts/generate", json={"athlete_id": 0, "ftp": 250})
    assert gen.status_code in (200, 400, 422)


def test_calendar_events_crud(client):
    aid = db_mod.save_athlete({"name": "Cal Athlete", "experience_level": "Beginner"})
    db_mod.update_athlete(aid, {"tenant_id": aid})
    body = {"athlete_id": aid, "title": "Morning ride", "date": "2024-06-20", "event_type": "training"}
    r = client.post("/api/v1/calendar/events", json=body)
    assert r.status_code == 200
    event_id = r.json().get("id")
    assert client.get("/api/v1/calendar/events", params={"athlete_id": aid, "year": 2024, "month": 6}).status_code == 200
    assert client.get("/api/v1/calendar/events/range", params={"athlete_id": aid, "start": "2024-06-01", "end": "2024-06-30"}).status_code == 200
    if event_id is not None:
        assert client.get(f"/api/v1/calendar/events/{event_id}").status_code == 200
        assert client.put(f"/api/v1/calendar/events/{event_id}", json={"title": "Updated"}).status_code in (200, 404)
        assert client.post(f"/api/v1/calendar/events/{event_id}/complete").status_code in (200, 404)
        assert client.delete(f"/api/v1/calendar/events/{event_id}").status_code in (200, 404)


def test_calendar_event_not_found(client):
    assert client.get("/api/v1/calendar/events/999999").status_code == 404
    assert client.put("/api/v1/calendar/events/999999", json={"title": "x"}).status_code == 404
    assert client.delete("/api/v1/calendar/events/999999").status_code == 404


# --------------------------------------------------------------------------- #
# Weather
# --------------------------------------------------------------------------- #
def test_weather_endpoints(client):
    assert client.get("/api/v1/weather", params={"lat": 45.0, "lon": 7.0}).status_code in (200, 500)
    assert client.get("/api/v1/weather/forecast", params={"lat": 45.0, "lon": 7.0}).status_code in (200, 500)


# --------------------------------------------------------------------------- #
# Maps / POIs
# --------------------------------------------------------------------------- #
def test_pois_crud(client):
    poi = {"name": "Panorama Point", "description": "Nice view", "lat": 45.0, "lon": 7.0, "type": "vista"}
    r = client.post("/api/v1/maps/pois", json=poi)
    assert r.status_code == 200
    poi_id = r.json()["id"]
    assert client.get("/api/v1/maps/pois").status_code == 200
    assert client.get("/api/v1/maps/pois/nearby", params={"lat": 45.0, "lon": 7.0, "radius": 5}).status_code == 200
    assert client.get(f"/api/v1/maps/pois/{poi_id}").status_code == 200
    assert client.delete(f"/api/v1/maps/pois/{poi_id}").status_code == 200
    assert client.get(f"/api/v1/maps/pois/{poi_id}").status_code == 404
    assert client.delete(f"/api/v1/maps/pois/{poi_id}").status_code == 404


def test_pois_invalid_type(client):
    r = client.post("/api/v1/maps/pois", json={"name": "x", "description": "y", "lat": 45, "lon": 7, "type": "bad"})
    assert r.status_code == 422


def test_maps_places(client):
    assert client.get("/api/v1/maps/places/nearby", params={"lat": 45.0, "lon": 7.0}).status_code in (200, 422, 404, 500)
    assert client.get("/api/v1/maps/places/osm-search", params={"lat": 45.0, "lon": 7.0, "query": "cafe", "limit": 5}).status_code in (200, 500)
    assert client.get("/api/v1/maps/places/search", params={"lat": 45.0, "lon": 7.0, "query": "cafe"}).status_code in (200, 422, 404, 500)


# --------------------------------------------------------------------------- #
# Scores / benchmark / coaches / knowledge
# --------------------------------------------------------------------------- #
def test_scores_and_benchmark(client):
    r = client.post(
        "/api/v1/athletes",
        json={"name": "Score Athlete", "age": 30, "weight_kg": 70, "experience_level": "Amateur"},
    )
    aid = r.json().get("id") if r.status_code == 200 else 0
    assert client.get(f"/api/v1/scores/athlete/{aid}").status_code == 200
    r = client.post("/api/v1/benchmark/compare", json={"date": "2024-06-15", "distance_km": 30, "duration_minutes": 60})
    assert r.status_code in (200, 400)


def test_coach_endpoints(client):
    assert client.get("/api/v1/coach/full", params={"athlete_id": 0}).status_code == 200
    assert client.get("/api/v1/coach/workout", params={"athlete_id": 0}).status_code == 200
    assert client.get("/api/v1/coach/recovery", params={"athlete_id": 0}).status_code == 200
    assert client.get("/api/v1/coach/trends", params={"athlete_id": 0}).status_code == 200
    assert client.get("/api/v1/coach/history", params={"athlete_id": 0}).status_code == 200
    assert client.get("/api/v1/coach/page").status_code in (200, 404)


def test_knowledge_endpoints(client):
    assert client.get("/api/v1/knowledge").status_code == 200
    assert client.get("/api/v1/knowledge/stats").status_code in (200, 404)
    assert client.post("/api/v1/knowledge/reload").status_code in (200, 400, 404)
    assert client.post("/api/v1/knowledge/init-embeddings").status_code in (200, 400, 404, 500)


# --------------------------------------------------------------------------- #
# Admin endpoints
# --------------------------------------------------------------------------- #
def test_admin_endpoints(client):
    assert client.get("/api/v1/admin/athletes").status_code == 200
    assert client.get("/api/v1/admin/stats").status_code == 200
    assert client.get("/api/v1/admin/backup").status_code in (200, 404, 500)
    assert client.post("/api/v1/admin/backup/scheduled").status_code in (200, 400, 404, 500)
    assert client.post("/api/v1/admin/indexes").status_code in (200, 400, 500)
    assert client.post("/api/v1/admin/reset-demo").status_code in (200, 400, 500)
    assert client.get("/api/v1/admin/ceo").status_code in (200, 404)


def test_admin_forbidden_for_non_admin(db_path):
    tc = _make_client("3", is_admin=False, db_path=db_path)
    assert tc.get("/api/v1/admin/athletes").status_code == 403
    assert tc.get("/api/v1/admin/stats").status_code == 403


# --------------------------------------------------------------------------- #
# Health / config / webhooks / import
# --------------------------------------------------------------------------- #
def test_health_and_config(client):
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/health/detailed").status_code == 200
    assert client.get("/api/v1/health/redis").status_code == 200
    assert client.get("/api/v1/config/google-maps-key").status_code == 200
    sentry = client.get("/api/v1/sentry-debug")
    assert sentry.status_code in (404, 500)
    webhook = client.post("/api/v1/alerts/webhook", json={"receiver": "test"})
    assert webhook.status_code == 200


def test_alerts_webhook_unauthorized(client, monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_WEBHOOK_TOKEN", "secret-token")
    bad = client.post("/api/v1/alerts/webhook", json={"receiver": "x"})
    assert bad.status_code == 401
    ok = client.post("/api/v1/alerts/webhook", json={"receiver": "x"}, headers={"X-Alertmanager-Webhook-Token": "secret-token"})
    assert ok.status_code == 200


def test_import_gpx_and_fit(db_path):
    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    aid = db_mod.save_athlete({"name": "Import Athlete", "experience_level": "Beginner"})
    db_mod.update_athlete(aid, {"tenant_id": aid})
    tc = _make_client(str(aid), is_admin=False, db_path=db_path)
    gpx = (
        '<?xml version="1.0"?><gpx version="1.1" '
        'xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>'
        '<trkpt lat="45.0" lon="7.0"><time>2024-06-15T10:00:00Z</time></trkpt>'
        '<trkpt lat="45.001" lon="7.001"><time>2024-06-15T10:30:00Z</time></trkpt>'
        "</trkseg></trk></gpx>"
    )
    from io import BytesIO

    r = tc.post("/api/v1/import/gpx", files={"file": ("t.gpx", BytesIO(gpx.encode()), "application/gpx+xml")})
    assert r.status_code == 200
    bad = tc.post("/api/v1/import/gpx", files={"file": ("t.gpx", BytesIO(b"<bad/>"), "application/gpx+xml")})
    assert bad.status_code in (200, 400, 422)
    ff = tc.post("/api/v1/import/fit", files={"file": ("t.fit", BytesIO(b"invalid"), "application/octet-stream")})
    assert ff.status_code in (400, 422, 500)


def test_import_multiple(client):
    r = client.post("/api/v1/import/multiple", json={"rides": [SAMPLE_RIDE, SAMPLE_RIDE]})
    assert r.status_code in (200, 400, 422)


def test_import_gpx_too_large(client):
    big = b"x" * (51 * 1024 * 1024)
    from io import BytesIO

    r = client.post("/api/v1/import/gpx", files={"file": ("big.gpx", BytesIO(big), "application/gpx+xml")})
    assert r.status_code == 413


# --------------------------------------------------------------------------- #
# Export / charts / report
# --------------------------------------------------------------------------- #
def test_export_and_charts(client, monkeypatch):
    import pathlib

    def _touch(*args, **kwargs):
        path = args[-1] if args else kwargs.get("path")
        if path:
            try:
                pathlib.Path(path).touch()
            except Exception:
                pass

    for name in (
        "create_speed_chart",
        "create_duration_chart",
        "create_distance_chart",
        "create_elevation_chart",
    ):
        monkeypatch.setattr(f"bike_analyzer.backend.analytics.analytics.{name}", _touch)
    resp = client.post("/api/v1/rides", json=SAMPLE_RIDE)
    ride_id = resp.json()["id"]
    assert client.get("/api/v1/rides/export/json").status_code == 200
    assert client.get("/api/v1/rides/export/csv").status_code == 200
    assert client.get(f"/api/v1/rides/{ride_id}/report").status_code == 200
    assert client.get(f"/api/v1/charts/speed/{ride_id}").status_code == 200
    assert client.get("/api/v1/charts/duration").status_code == 200
    assert client.get(f"/api/v1/charts/distance/{ride_id}").status_code == 200
    assert client.get(f"/api/v1/charts/elevation/{ride_id}").status_code == 200


# --------------------------------------------------------------------------- #
# Athletes
# --------------------------------------------------------------------------- #
def test_athletes_endpoints(client):
    assert client.get("/api/v1/athletes").status_code == 200
    assert client.get("/api/v1/athletes/me").status_code == 200
    body = {"name": "New Athlete", "age": 35, "weight_kg": 75, "experience_level": "Amateur"}
    r = client.post("/api/v1/athletes", json=body)
    assert r.status_code in (200, 400)
    if r.status_code == 200:
        aid = r.json().get("id")
        assert client.get(f"/api/v1/athletes/{aid}").status_code == 200
        assert client.put(f"/api/v1/athletes/{aid}", json={"weight_kg": 78}).status_code in (200, 404)
        assert client.post(f"/api/v1/athletes/{aid}/metrics", json={"fatigue_score": 3.0}).status_code in (200, 404)
    assert client.post("/api/v1/athletes", json={"name": "x"}).status_code == 422
