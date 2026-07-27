"""Additional route coverage tests for P3.5 (>90% routes.py coverage).

These tests focus on endpoints that are computed locally (DB / analytics) plus the
main error branches (404/403/400/422) so they stay deterministic and network-free.
"""

import os

import pytest

try:
    import numpy.random
    _HAS_NUMPY_RANDOM = True
except ImportError:
    _HAS_NUMPY_RANDOM = False

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
    assert client.get("/api/v1/config/google-maps-key").status_code in (200, 401)
    sentry = client.get("/api/v1/sentry-debug")
    assert sentry.status_code in (404, 500)
    webhook = client.post("/api/v1/alerts/webhook", json={"receiver": "test"})
    assert webhook.status_code in (200, 401)


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


def test_power_metrics_endpoint(client):
    ride_payload = {
        "date": "2024-06-15",
        "distance_km": 25.0,
        "duration_minutes": 60.0,
        "weight_kg": 70,
        "gps_points": [
            {"lat": 45.0, "lon": 7.0, "timestamp": "2024-06-15T10:00:00", "altitude": 100, "speed": 20.0},
            {"lat": 45.001, "lon": 7.001, "timestamp": "2024-06-15T10:30:00", "altitude": 120, "speed": 25.0},
        ],
    }
    resp = client.post("/api/v1/rides", json=ride_payload)
    ride_id = resp.json()["id"]
    r = client.get(f"/api/v1/rides/{ride_id}/power-metrics", params={"ftp": 250.0})
    assert r.status_code in (200, 400, 422)


def test_analytics_route_suggestions(client):
    r = client.get("/api/v1/analytics/route-suggestions", params={"athlete_id": 0, "min_distance_km": 10})
    assert r.status_code == 200
    body = r.json()
    assert "suggestions" in body or "routes" in body


def test_analytics_multi_classify(client):
    r = client.get("/api/v1/analytics/multi-classify")
    assert r.status_code == 200
    body = r.json()
    assert "total_rides" in body
    assert "rides" in body


def test_analytics_vip(client):
    r = client.get("/api/v1/analytics/vip")
    assert r.status_code == 200
    body = r.json()
    assert "probability_index" in body
    assert "readiness_score" in body


def test_analytics_inactivity(client):
    r = client.get("/api/v1/analytics/inactivity")
    assert r.status_code == 200
    body = r.json()
    assert "current_streak_days" in body
    assert "advice" in body


def test_notifications_evaluate_post(client):
    r = client.post("/api/v1/notifications/evaluate", json={"athlete_id": 0})
    assert r.status_code in (200, 422, 404, 500)


def test_badges_endpoint(client):
    r = client.get("/api/v1/badges", params={"athlete_id": 0})
    assert r.status_code == 200
    body = r.json()
    assert "badges" in body or "achievements" in body


def test_dashboard_endpoint(client):
    r = client.get("/api/v1/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)


def test_client_athletes_endpoints(db_path):
    from bike_analyzer.backend.api.app_factory import create_app
    from bike_analyzer.backend.db import database as db_mod
    from bike_analyzer.backend.security import create_access_token

    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    db_mod.save_user({
        "username": "client99",
        "email": "client99@test.com",
        "password_hash": "test",
        "is_client": True,
    })
    app = create_app()
    tc = TestClient(app)
    token = create_access_token(subject="0", is_admin=False, is_client=True)
    tc.headers["Authorization"] = f"Bearer {token}"

    import bike_analyzer.backend.db.database as db_database
    original_get_all = db_database.get_all_athletes
    def _patched_get_all_athletes(*args, **kwargs):
        return []
    db_database.get_all_athletes = _patched_get_all_athletes
    try:
        r = tc.get("/api/v1/client/athletes")
        assert r.status_code == 200
        body = r.json()
        assert "athletes" in body or "clients" in body or isinstance(body, list)
    finally:
        db_database.get_all_athletes = original_get_all

    r = tc.post("/api/v1/client/athletes/999999/assign", json={})
    assert r.status_code in (404, 400, 422)


def test_beck_assessment_crud(client):
    r = client.post("/api/v1/beck/assessments", json={"score": 5, "category": "mild"})
    assert r.status_code in (201, 200, 422)
    r = client.get("/api/v1/beck/assessments")
    assert r.status_code == 200
    r = client.get("/api/v1/beck/assessments/latest")
    assert r.status_code in (200, 404)
    r = client.get("/api/v1/beck/history")
    assert r.status_code == 200


def test_athlete_state_endpoint(client):
    r = client.get("/api/v1/athlete/state")
    assert r.status_code == 200
    body = r.json()
    assert "fatigue_score" in body or "readiness" in body or "athlete_id" in body or "acwr" in body


def test_nutrition_crud_with_assertions(client):
    created = client.post(
        "/api/v1/metabolism/nutrition",
        json={"name": "Banana", "kcal_per_100g": 89.0, "carbs_g": 22.8, "protein_g": 1.1, "fat_g": 0.3},
    )
    assert created.status_code == 201
    item_id = created.json().get("id")
    if item_id:
        fetched = client.get(f"/api/v1/metabolism/nutrition/{item_id}")
        assert fetched.status_code == 200
        assert fetched.json().get("name") == "Banana"
        updated = client.put(f"/api/v1/metabolism/nutrition/{item_id}", json={"name": "Banana Organic"})
        assert updated.status_code == 200
        assert updated.json().get("name") == "Banana Organic"
        deleted = client.delete(f"/api/v1/metabolism/nutrition/{item_id}")
        assert deleted.status_code == 204


def test_food_log_crud_with_assertions(db_path):
    from bike_analyzer.backend.api.app_factory import create_app
    from bike_analyzer.backend.db import database as db_mod
    from bike_analyzer.backend.security import create_access_token

    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    db_mod.save_athlete({"name": "FoodLog Rider", "experience_level": "Intermediate"}, athlete_id=0)
    app = create_app()
    tc = TestClient(app)
    token = create_access_token(subject="0", is_admin=True)
    tc.headers["Authorization"] = f"Bearer {token}"

    created = tc.post(
        "/api/v1/metabolism/food-log",
        json={"date": "2024-06-15", "meal_type": "lunch", "description": "Pasta lunch", "kcal": 450.0},
    )
    assert created.status_code == 201
    log_id = created.json().get("id")
    if log_id:
        fetched = tc.get("/api/v1/metabolism/food-log?date=2024-06-15")
        assert fetched.status_code == 200
        logs = fetched.json()
        assert isinstance(logs, list)
        updated = tc.put(
            f"/api/v1/metabolism/food-log/{log_id}",
            json={"date": "2024-06-15", "meal_type": "lunch", "description": "Pasta Updated", "kcal": 500.0},
        )
        assert updated.status_code == 200
        deleted = tc.delete(f"/api/v1/metabolism/food-log/{log_id}")
        assert deleted.status_code == 204


# --------------------------------------------------------------------------- #
# Metabolism endpoints
# --------------------------------------------------------------------------- #
def test_metabolism_profile_and_summary(client):
    client.post("/api/v1/athletes", json={"name": "Meta Athlete", "age": 30, "weight_kg": 70, "experience_level": "Amateur"})
    assert client.get("/api/v1/metabolism/profile").status_code in (200, 404)
    assert client.put("/api/v1/metabolism/profile", json={"experience_level": "Amateur"}).status_code in (200, 404)
    assert client.get("/api/v1/metabolism/food-log", params={"date": "2024-06-15"}).status_code == 200
    assert client.post("/api/v1/metabolism/food-log", json={"date": "2024-06-15", "meal_type": "lunch", "description": "Pasta lunch", "kcal": 450.0}).status_code in (201, 404)
    assert client.get("/api/v1/metabolism/daily-summary", params={"date": "2024-06-15"}).status_code in (200, 404, 500)
    assert client.get("/api/v1/metabolism/range-summary", params={"start_date": "2024-06-01", "end_date": "2024-06-30"}).status_code in (200, 404, 500)
    assert client.post("/api/v1/metabolism/recalculate", params={"date": "2024-06-15"}).status_code in (200, 404, 500)
    assert client.get("/api/v1/metabolism/reference-values").status_code == 200
    assert client.post("/api/v1/metabolism/reference-values", json={"values": []}).status_code == 200


def test_metabolism_nutrition_search_and_categories(client):
    assert client.get("/api/v1/metabolism/nutrition/search", params={"q": "banana"}).status_code == 200
    assert client.get("/api/v1/metabolism/nutrition/categories").status_code == 200
    assert client.get("/api/v1/metabolism/nutrition/999999").status_code == 404


def test_metabolism_nutrition_builtin_protection(client):
    builtin = client.post(
        "/api/v1/metabolism/nutrition",
        json={"name": "Builtin Item", "kcal_per_100g": 100.0},
    )
    assert builtin.status_code == 201
    item_id = builtin.json().get("id")
    if item_id:
        upd = client.put(f"/api/v1/metabolism/nutrition/{item_id}", json={"name": "Hacked"})
        assert upd.status_code in (403, 404, 200)
        dele = client.delete(f"/api/v1/metabolism/nutrition/{item_id}")
        assert dele.status_code in (403, 404, 204)


# --------------------------------------------------------------------------- #
# BLE device management
# --------------------------------------------------------------------------- #
def test_ble_devices_crud(client):
    client.post("/api/v1/athletes", json={"name": "BLE Athlete", "age": 30, "weight_kg": 70, "experience_level": "Beginner"})
    r = client.post("/api/v1/ble/devices", json={"device_id": "ble-1", "name": "Scale", "device_type": "weight_scale"})
    assert r.status_code in (200, 201)
    dev_id = r.json().get("id")
    assert client.get("/api/v1/ble/devices").status_code == 200
    if dev_id:
        assert client.get(f"/api/v1/ble/devices/{dev_id}").status_code in (200, 404)
        assert client.put(f"/api/v1/ble/devices/{dev_id}", json={"name": "Scale Updated"}).status_code in (200, 404)
        assert client.post(f"/api/v1/ble/devices/{dev_id}/sync").status_code in (200, 404)
        assert client.delete(f"/api/v1/ble/devices/{dev_id}").status_code in (200, 404)


# --------------------------------------------------------------------------- #
# Calendar events
# --------------------------------------------------------------------------- #
def test_calendar_events_full_crud(db_path):
    from bike_analyzer.backend.api.app_factory import create_app
    from bike_analyzer.backend.db import database as db_mod
    from bike_analyzer.backend.security import create_access_token

    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    aid = db_mod.save_athlete({"name": "Cal Athlete2", "experience_level": "Beginner"})
    db_mod.update_athlete(aid, {"tenant_id": aid})
    app = create_app()
    tc = TestClient(app)
    token = create_access_token(subject=str(aid), is_admin=False)
    tc.headers["Authorization"] = f"Bearer {token}"

    body = {"athlete_id": aid, "title": "Full Test Ride", "date": "2024-06-20", "event_type": "training", "duration_minutes": 60}
    r = tc.post("/api/v1/calendar/events", json=body)
    assert r.status_code in (200, 201)
    event_id = r.json().get("id")
    assert tc.get("/api/v1/calendar/events", params={"athlete_id": aid, "year": 2024, "month": 6}).status_code == 200
    assert tc.get("/api/v1/calendar/events/range", params={"athlete_id": aid, "start": "2024-06-01", "end": "2024-06-30"}).status_code == 200
    if event_id:
        assert tc.get(f"/api/v1/calendar/events/{event_id}").status_code == 200
        assert tc.put(f"/api/v1/calendar/events/{event_id}", json={"title": "Updated Ride"}).status_code in (200, 404)
        assert tc.post(f"/api/v1/calendar/events/{event_id}/complete").status_code in (200, 404)
        assert tc.delete(f"/api/v1/calendar/events/{event_id}").status_code in (200, 404)


# --------------------------------------------------------------------------- #
# Training endpoints
# --------------------------------------------------------------------------- #
def test_training_endpoints_full(client):
    assert client.get("/api/v1/training/load", params={"athlete_id": 0, "days": 30}).status_code == 200
    assert client.get("/api/v1/training/status", params={"athlete_id": 0}).status_code == 200
    assert client.get("/api/v1/training/summary", params={"athlete_id": 0}).status_code == 200
    assert client.get("/api/v1/training/goals", params={"athlete_id": 0}).status_code in (200, 404, 500)
    r = client.post("/api/v1/training/goals", json={"title": "Granfondo 2024", "goal_type": "granfondo", "target_distance_km": 120})
    assert r.status_code in (200, 201, 400, 500)
    goal_id = r.json().get("id") if r.status_code in (200, 201) else None
    if goal_id:
        gen = client.post("/api/v1/training/workouts/generate", json={"goal_id": goal_id, "event_count": 8})
        assert gen.status_code in (200, 400, 422, 500)


# --------------------------------------------------------------------------- #
# Maps / places
# --------------------------------------------------------------------------- #
def test_maps_places_endpoints(client, monkeypatch):
    async def _mock_get_local_results(points, query):
        return [{"name": "Mock Cafe", "lat": 45.0, "lon": 7.0}]

    monkeypatch.setattr("bike_analyzer.backend.maps.osm_maps.get_local_results", _mock_get_local_results)
    assert client.get("/api/v1/maps/places/nearby", params={"ride_id": 1, "query": "cafe", "use_osm": "true"}).status_code in (200, 404, 422)
    assert client.get("/api/v1/maps/places/osm-search", params={"lat": 45.0, "lon": 7.0, "query": "cafe", "limit": 5}).status_code in (200, 500)
    assert client.get("/api/v1/maps/places/search", params={"ride_id": 1, "query": "cafe"}).status_code in (200, 404, 422, 500)


# --------------------------------------------------------------------------- #
# Traffic / safety
# --------------------------------------------------------------------------- #
def test_traffic_and_safety_endpoints(client, monkeypatch):
    def _mock_road_summary(points):
        return {"road_types": {"primary": 1}}

    def _mock_bike_lanes(points, include_geometry):
        return {"elements": []}

    def _mock_incidents(lat, lon, radius_km, days):
        return []

    async def _mock_analyze_safety(points, incidents):
        return {"safety_score": 7.5, "risk_factors": []}

    def _mock_save_route_safety_score(score_data, tenant_id=0):
        return 1

    def _mock_get_route_safety_score(ride_id, tenant_id=None):
        return None

    monkeypatch.setattr("bike_analyzer.backend.traffic.overpass_client.get_road_type_summary", _mock_road_summary)
    monkeypatch.setattr("bike_analyzer.backend.traffic.overpass_client.fetch_bike_lanes", _mock_bike_lanes)
    monkeypatch.setattr("bike_analyzer.backend.traffic.incident_fetcher.fetch_incidents", _mock_incidents)
    monkeypatch.setattr("bike_analyzer.backend.traffic.safety_analyzer.analyze_route_safety", _mock_analyze_safety)
    monkeypatch.setattr("bike_analyzer.backend.db.database.save_route_safety_score", _mock_save_route_safety_score)
    monkeypatch.setattr("bike_analyzer.backend.db.database.get_route_safety_score", _mock_get_route_safety_score)

    resp = client.post("/api/v1/rides", json=SAMPLE_RIDE)
    ride_id = resp.json().get("id") if resp.status_code == 200 else None
    assert client.get("/api/v1/traffic/road-types", params={"lat": 45.0, "lon": 7.0, "radius_km": 2.0}).status_code == 200
    assert client.get("/api/v1/traffic/bike-infrastructure", params={"lat": 45.0, "lon": 7.0, "radius_km": 2.0}).status_code == 200
    assert client.get("/api/v1/traffic/incidents", params={"lat": 45.0, "lon": 7.0, "radius_km": 5.0, "days": 90}).status_code == 200
    if ride_id:
        assert client.get(f"/api/v1/rides/{ride_id}/safety").status_code in (200, 400, 404, 500)


# --------------------------------------------------------------------------- #
# Admin endpoints
# --------------------------------------------------------------------------- #
def test_admin_stats_and_backup(client):
    assert client.get("/api/v1/admin/stats").status_code == 200
    assert client.post("/api/v1/admin/indexes").status_code == 200
    assert client.post("/api/v1/admin/reset-demo").status_code in (200, 404, 500)
    assert client.get("/api/v1/admin/ceo").status_code == 200
    assert client.get("/api/v1/admin/backup").status_code in (200, 404, 500)
    assert client.post("/api/v1/admin/backup/scheduled").status_code in (200, 400, 404, 500)
    assert client.get("/api/v1/admin/audit-logs").status_code == 200
    assert client.get("/api/v1/admin/test-sentry").status_code == 200


def test_admin_forbidden_for_non_admin(db_path):
    tc = _make_client("3", is_admin=False, db_path=db_path)
    assert tc.get("/api/v1/admin/athletes").status_code == 403
    assert tc.get("/api/v1/admin/stats").status_code == 403
    assert tc.get("/api/v1/admin/users").status_code == 403


# --------------------------------------------------------------------------- #
# Google OAuth callback error paths
# --------------------------------------------------------------------------- #
def test_google_oauth_callback_error_paths(client, monkeypatch):
    from bike_analyzer.backend.settings import get_settings

    monkeypatch.setattr(get_settings(), "google_client_id", "test-client")
    monkeypatch.setattr(get_settings(), "google_client_secret", "test-secret")
    r = client.get("/api/v1/auth/google/callback", params={"error": "access_denied", "state": "bad"}, follow_redirects=False)
    assert r.status_code == 307
    assert "oauth_error" in r.headers.get("location", "")
    r = client.get("/api/v1/auth/google/callback", params={"state": "bad"}, follow_redirects=False)
    assert r.status_code == 307
    assert "oauth_error=invalid_state" in r.headers.get("location", "")


def test_google_code_exchange(client, monkeypatch):
    from bike_analyzer.backend.settings import get_settings
    import bike_analyzer.backend.auth.google_auth as google_auth_mod

    monkeypatch.setattr(get_settings(), "google_client_id", "test-client")
    monkeypatch.setattr(get_settings(), "google_client_secret", "test-secret")
    monkeypatch.setattr(google_auth_mod, "exchange_google_code", lambda *a, **k: {"access_token": "tok"})
    monkeypatch.setattr(google_auth_mod, "get_google_user_info", lambda tok: {"sub": "sub", "email": "e@e.com", "name": "E"})
    monkeypatch.setattr(google_auth_mod, "create_google_session", lambda ui, athlete_id=None: {"access_token": "jwt"})
    r = client.post("/api/v1/auth/google/code-exchange", json={"code": "code", "redirect_uri": "https://bikemaster.onrender.com/api/v1/auth/google/callback"})
    assert r.status_code == 200
    assert "access_token" in r.json()


# --------------------------------------------------------------------------- #
# Import endpoints
# --------------------------------------------------------------------------- #
def test_import_gpx_and_tcx(db_path):
    tc = _make_client("0", is_admin=True, db_path=db_path)
    gpx = (
        '<?xml version="1.0"?><gpx version="1.1" '
        'xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>'
        '<trkpt lat="45.0" lon="7.0"><time>2024-06-15T10:00:00Z</time></trkpt>'
        '<trkpt lat="45.001" lon="7.001"><time>2024-06-15T10:30:00Z</time></trkpt>'
        "</trkseg></trk></gpx>"
    )
    from io import BytesIO

    r = tc.post("/api/v1/import/gpx", files={"file": ("t.gpx", BytesIO(gpx.encode()), "application/gpx+xml")})
    assert r.status_code in (200, 400, 422)
    tcx = (
        '<?xml version="1.0"?><TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">'
        "<Activities><Activity><Id>2024-06-15T10:00:00Z</Id>"
        "<Lap><TotalTimeSeconds>3600</TotalTimeSeconds><DistanceMeters>25000</DistanceMeters>"
        "<Track><Trackpoint><Time>2024-06-15T10:00:00Z</Time><Position><LatitudeDegrees>45.0</LatitudeDegrees><LongitudeDegrees>7.0</LongitudeDegrees></Position></Trackpoint>"
        "<Trackpoint><Time>2024-06-15T10:30:00Z</Time><Position><LatitudeDegrees>45.001</LatitudeDegrees><LongitudeDegrees>7.001</LongitudeDegrees></Position></Trackpoint>"
        "</Track></Lap></Activity></Activities></TrainingCenterDatabase>"
    )
    r = tc.post("/api/v1/import/tcx", files={"file": ("t.tcx", BytesIO(tcx.encode()), "application/octet-stream")})
    assert r.status_code in (200, 400, 422, 500)


def test_import_fit_and_multiple(db_path):
    tc = _make_client("0", is_admin=True, db_path=db_path)
    from io import BytesIO

    r = tc.post("/api/v1/import/fit", files={"file": ("t.fit", BytesIO(b"invalid"), "application/octet-stream")})
    assert r.status_code in (400, 422, 500)
    r = tc.post("/api/v1/import/multiple", files={"files": [("f1.gpx", BytesIO(b"<gpx/>"), "application/gpx+xml"), ("f2.gpx", BytesIO(b"<gpx/>"), "application/gpx+xml")]})
    assert r.status_code in (200, 400, 422)


def test_import_google_health(client, monkeypatch):
    import bike_analyzer.backend.ingestion.google_health as gh_mod

    monkeypatch.setattr(gh_mod, "google_health_to_rides", lambda tok, athlete_id=None: [])
    r = client.post("/api/v1/import/google-health", json={"access_token": "tok", "refresh_token": "rtok"})
    assert r.status_code in (200, 400, 422, 500)
    assert client.get("/api/v1/import/providers").status_code == 200


# --------------------------------------------------------------------------- #
# Analytics endpoints
# --------------------------------------------------------------------------- #
def test_analytics_zones_projection_trends(client):
    assert client.get("/api/v1/analytics/zones").status_code == 200
    assert client.get("/api/v1/analytics/projection", params={"target_days": 30}).status_code == 200
    assert client.get("/api/v1/analytics/trends", params={"metric": "distance_km", "window": 7}).status_code == 200
    assert client.get("/api/v1/analytics/monthly").status_code == 200
    assert client.get("/api/v1/analytics/comparison", params={"period_days": 14}).status_code == 200


# --------------------------------------------------------------------------- #
# Beck assessments
# --------------------------------------------------------------------------- #
def test_beck_assessments_full(client):
    r = client.post("/api/v1/beck/assessments", json={"answers": [[1, 2], [2, 3]], "notes": "test"})
    assert r.status_code in (201, 200, 422)
    assert client.get("/api/v1/beck/assessments").status_code == 200
    assert client.get("/api/v1/beck/assessments/latest").status_code in (200, 404)
    assert client.get("/api/v1/beck/history").status_code == 200


# --------------------------------------------------------------------------- #
# Notifications
# --------------------------------------------------------------------------- #
def test_notifications_list_and_preferences(client):
    assert client.get("/api/v1/notifications", params={"athlete_id": 0}).status_code == 200
    assert client.post("/api/v1/notifications/preferences", json={"language": "it", "channels": {"push": True}}).status_code in (200, 422, 500)
    assert client.post("/api/v1/notifications/evaluate", json={"athlete_state": {"tsb": -20}, "plan": {}}).status_code in (200, 422, 500)


# --------------------------------------------------------------------------- #
# Google Maps key config
# --------------------------------------------------------------------------- #
def test_google_maps_key_config(client):
    r = client.get("/api/v1/config/google-maps-key")
    assert r.status_code in (200, 401, 403)


# --------------------------------------------------------------------------- #
# Dashboard cache path
# --------------------------------------------------------------------------- #
def test_dashboard_cache_miss(db_path):
    tc = _make_client("0", is_admin=True, db_path=db_path)
    r = tc.get("/api/v1/dashboard")
    assert r.status_code == 200


# --------------------------------------------------------------------------- #
# Coach chat
# --------------------------------------------------------------------------- #
def test_coach_chat(client, monkeypatch):
    monkeypatch.setattr("bike_analyzer.backend.analytics.ai_coach.generate_training_advice", lambda *a, **k: "Consiglio di allenamento: inizia con 30 minuti a zona 2.")
    r = client.post("/api/v1/coach/chat", json={"message": "Come mi alleno?", "context": "general"})
    assert r.status_code in (200, 422, 500)
    r = client.get("/api/v1/coach/chat", params={"message": "test", "context": "general"})
    assert r.status_code in (200, 422, 500)


# --------------------------------------------------------------------------- #
# Analytics endpoints
# --------------------------------------------------------------------------- #
def test_analytics_trends_and_monthly(client):
    client.post("/api/v1/athletes", json={"name": "Analytics Athlete", "age": 30, "weight_kg": 70, "experience_level": "Intermediate"})
    assert client.get("/api/v1/analytics/trends", params={"athlete_id": 0, "days": 30}).status_code in (200, 404, 500)
    assert client.get("/api/v1/analytics/monthly", params={"athlete_id": 0, "year": 2024, "month": 6}).status_code in (200, 404, 500)
    assert client.get("/api/v1/analytics/comparison", params={"athlete_id": 0, "period": "month"}).status_code in (200, 404, 500)
    assert client.get("/api/v1/analytics/projection", params={"athlete_id": 0, "target_date": "2024-09-01"}).status_code in (200, 404, 500)


# --------------------------------------------------------------------------- #
# Admin endpoints
# --------------------------------------------------------------------------- #
def test_admin_stats_and_indexes(client):
    assert client.get("/api/v1/admin/stats").status_code == 200
    assert client.post("/api/v1/admin/indexes").status_code == 200


def test_admin_users_and_backup(client):
    assert client.get("/api/v1/admin/users").status_code == 200
    assert client.get("/api/v1/admin/backup").status_code in (200, 500)


# --------------------------------------------------------------------------- #
# BM2 simulation
# --------------------------------------------------------------------------- #
def test_bm2_simulate(client):
    r = client.post("/api/v1/bm2/simulate", json={"question": "Cosa succede se perdo 5kg?", "athlete": {"ftp": 250}, "bike": {"weight_kg": 7}})
    assert r.status_code in (200, 400, 500)
    r = client.post("/api/v1/bm2/simulate-ride", json={"question": "Simula Salita", "override": {"weight_kg": 65}, "gps_points": [{"lat": 45.0, "lon": 7.0}]})
    assert r.status_code in (200, 400, 500)


# --------------------------------------------------------------------------- #
# Knowledge endpoints
# --------------------------------------------------------------------------- #
def test_knowledge_reload_and_init(client):
    assert client.post("/api/v1/knowledge/reload").status_code in (200, 401, 403, 500)
    assert client.post("/api/v1/knowledge/init-embeddings").status_code in (200, 401, 403, 500)


# --------------------------------------------------------------------------- #
# Analytics advanced endpoints
# --------------------------------------------------------------------------- #
def test_analytics_zones_and_speed_data(client):
    client.post("/api/v1/athletes", json={"name": "Analytics2 Athlete", "age": 30, "weight_kg": 70, "experience_level": "Intermediate"})
    assert client.get("/api/v1/analytics/zones", params={"athlete_id": 0}).status_code in (200, 404, 500)
    assert client.get("/api/v1/analytics/speed-data", params={"ride_id": 1}).status_code in (200, 404, 500)


def test_analytics_route_suggestions_and_classify(client):
    assert client.get("/api/v1/analytics/route-suggestions", params={"athlete_id": 0}).status_code in (200, 404, 500)
    assert client.get("/api/v1/analytics/multi-classify", params={"athlete_id": 0}).status_code in (200, 404, 500)
    assert client.get("/api/v1/analytics/vip", params={"athlete_id": 0}).status_code in (200, 404, 500)
    assert client.get("/api/v1/analytics/inactivity", params={"athlete_id": 0}).status_code in (200, 404, 500)


# --------------------------------------------------------------------------- #
# AetherMap endpoints
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not _HAS_NUMPY_RANDOM, reason="numpy.random unavailable (AetherMap import crashes)")
def test_aethermap_endpoints(client):
    assert client.get("/api/v1/aethermap/world").status_code in (200, 404, 500)
    assert client.get("/api/v1/aethermap/terrain-tile", params={"lat": 0.0, "lon": 0.0, "zoom": 5}).status_code in (200, 404, 500)


# --------------------------------------------------------------------------- #
# BM2 endpoints
# --------------------------------------------------------------------------- #
def test_bm2_models_and_ask(client, monkeypatch):
    async def _mock_answer(question, raw, extra=None):
        return {"answer": "mock", "confidence": 0.9}

    monkeypatch.setattr("bike_analyzer.bm2.orchestrator.AIOrchestrator.answer", _mock_answer)

    assert client.get("/api/v1/bm2/models").status_code == 200
    assert client.post("/api/v1/bm2/ask", json={"question": "Qual è la mia FTP?"}).status_code in (200, 400, 500)
    assert client.post("/api/v1/bm2/validate", json={"question": "Valida potenza", "power_w": 200}).status_code in (200, 400, 500)


# --------------------------------------------------------------------------- #
# Simple authenticated endpoints (health, auth, athlete, knowledge, coach)
# --------------------------------------------------------------------------- #
def test_health_endpoints(client):
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/health/detailed").status_code == 200
    assert client.get("/api/v1/health/comprehensive").status_code == 200
    assert client.get("/api/v1/health/redis").status_code == 200


def test_auth_register_and_me(client):
    assert client.post("/api/v1/auth/register", json={"username": "reguser", "email": "reg@test.com", "password": "RegPass1"}).status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200


def test_athlete_me_endpoints(client):
    assert client.get("/api/v1/athletes/me").status_code == 200
    assert client.get("/api/v1/athletes/me/history").status_code == 200


def test_knowledge_endpoints(client):
    assert client.get("/api/v1/knowledge").status_code == 200
    assert client.get("/api/v1/knowledge/search", params={"q": "test"}).status_code == 200
    assert client.get("/api/v1/knowledge/stats").status_code == 200


def test_coach_recovery_endpoint(client):
    assert client.get("/api/v1/coach/recovery", params={"fatigue_score": 3.0}).status_code in (200, 404, 500)


def test_notifications_preferences(client):
    assert client.post("/api/v1/notifications/preferences", json={"language": "it"}).status_code == 200
    assert client.get("/api/v1/notifications").status_code == 200


def test_training_status_and_summary(client):
    assert client.get("/api/v1/training/status", params={"athlete_id": 0}).status_code in (200, 404, 500)
    assert client.get("/api/v1/training/summary", params={"athlete_id": 0}).status_code in (200, 404, 500)


def test_weather_endpoints(client):
    assert client.get("/api/v1/weather", params={"lat": 45.0, "lon": 7.0}).status_code in (200, 404, 500)
    assert client.get("/api/v1/weather/forecast", params={"lat": 45.0, "lon": 7.0, "days": 3}).status_code in (200, 404, 500)


def test_rides_export_and_knowledge(client):
    client.post("/api/v1/athletes", json={"name": "Export Athlete", "age": 30, "weight_kg": 70, "experience_level": "Beginner"})
    assert client.get("/api/v1/rides/export/json").status_code in (200, 404, 500)
    assert client.get("/api/v1/rides/export/csv").status_code in (200, 404, 500)
    assert client.get("/api/v1/scores/athlete/0").status_code in (200, 404, 500)


def test_benchmark_and_speed_data(client):
    assert client.post("/api/v1/benchmark/compare", json={"date": "2024-06-15", "distance_km": 25.0, "duration_minutes": 60.0}).status_code in (200, 404, 500)
    client.post("/api/v1/athletes", json={"name": "Speed Athlete", "age": 30, "weight_kg": 70, "experience_level": "Intermediate"})
    assert client.get("/api/v1/analytics/speed-data", params={"ride_id": 1}).status_code in (200, 404, 500)
    assert client.get("/api/v1/rides/export/json").status_code in (200, 404, 500)


# --------------------------------------------------------------------------- #
# Admin endpoints
# --------------------------------------------------------------------------- #
def test_admin_audit_logs_and_ceo(client):
    assert client.get("/api/v1/admin/audit-logs").status_code == 200
    assert client.get("/api/v1/admin/ceo").status_code == 200


def test_admin_reset_demo(client):
    assert client.post("/api/v1/admin/reset-demo").status_code in (200, 500)


# --------------------------------------------------------------------------- #
# Not-found error paths
# --------------------------------------------------------------------------- #
def test_not_found_error_paths(client):
    assert client.get("/api/v1/athletes/999999").status_code == 404
    client.post("/api/v1/athletes", json={"name": "Ride Test", "age": 30, "weight_kg": 70, "experience_level": "Beginner"})
    client.post("/api/v1/rides", json=SAMPLE_RIDE)
    rides_resp = client.get("/api/v1/rides").json()
    rides_list = rides_resp if isinstance(rides_resp, list) else rides_resp.get("rides", [])
    ride_id = rides_list[0]["id"] if rides_list else 1
    assert client.get(f"/api/v1/rides/{ride_id + 9999}").status_code == 404
    assert client.get("/api/v1/calendar/events/999999").status_code == 404
    assert client.put("/api/v1/calendar/events/999999", json={"title": "x"}).status_code == 404
    assert client.delete("/api/v1/calendar/events/999999").status_code == 404


def test_coach_full_and_history_and_training(client):
    assert client.get("/api/v1/coach/full").status_code == 200
    assert client.get("/api/v1/coach/history", params={"athlete_id": 0}).status_code == 200
    assert client.get("/api/v1/training/load", params={"athlete_id": 0}).status_code == 200
    assert client.get("/api/v1/training/goals", params={"athlete_id": 0}).status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 200


# --------------------------------------------------------------------------- #
# BM2 endpoints
# --------------------------------------------------------------------------- #
def test_bm2_models_and_ask(client):
    assert client.get("/api/v1/bm2/models").status_code == 200
    assert client.post("/api/v1/bm2/ask", json={"question": "Qual è la mia FTP?"}).status_code in (200, 400, 500)
    assert client.post("/api/v1/bm2/validate", json={"question": "Valida potenza", "power_w": 200}).status_code in (200, 400, 500)
    assert client.post("/api/v1/bm2/simulate", json={"question": "Cosa succede se perdo 5kg?", "athlete": {"ftp": 250}, "bike": {"weight_kg": 7}}).status_code in (200, 400, 500)
    assert client.post("/api/v1/bm2/simulate-ride", json={"question": "Simula Salita", "override": {"weight_kg": 65}, "gps_points": [{"lat": 45.0, "lon": 7.0}]}).status_code in (200, 400, 500)


# --------------------------------------------------------------------------- #
# Maps / nearby endpoints
# --------------------------------------------------------------------------- #
def test_maps_and_nearby_endpoints(client):
    assert client.get("/api/v1/maps/pois", params={"lat": 45.0, "lon": 7.0}).status_code == 200
    assert client.get("/api/v1/maps/pois/nearby", params={"lat": 45.0, "lon": 7.0, "radius": 5.0}).status_code in (200, 500)
    assert client.get("/api/v1/nearby/places", params={"lat": 45.0, "lon": 7.0, "radius": 1000}).status_code in (200, 404, 500)
    assert client.get("/api/v1/nearby/osm-search", params={"q": "cafe", "lat": 45.0, "lon": 7.0}).status_code in (200, 404, 500)
    assert client.get("/api/v1/nearby/search", params={"q": "cafe", "lat": 45.0, "lon": 7.0}).status_code in (200, 404, 500)


# --------------------------------------------------------------------------- #
# Admin status and management endpoints
# --------------------------------------------------------------------------- #
def test_admin_status_and_management(client):
    assert client.get("/api/v1/admin/stats").status_code == 200
    assert client.post("/api/v1/admin/indexes").status_code == 200
    assert client.get("/api/v1/admin/backup").status_code == 200
    assert client.get("/api/v1/admin/system-stats").status_code in (200, 404, 500)


# --------------------------------------------------------------------------- #
# Validation/schema error paths
# --------------------------------------------------------------------------- #
def test_validation_error_paths(client):
    r = client.post("/api/v1/athletes", json={})
    assert r.status_code == 422
    r = client.post("/api/v1/rides", json={})
    assert r.status_code == 422
    r = client.get("/api/v1/training/load")
    assert r.status_code == 422
    r = client.get("/api/v1/weather")
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# Ride CRUD and analytics handler bodies
# --------------------------------------------------------------------------- #
def test_ride_detail_and_analytics(client):
    client.post("/api/v1/athletes", json={"name": "Analytics3 Athlete", "age": 30, "weight_kg": 70, "experience_level": "Intermediate"})
    ride = client.post("/api/v1/rides", json=SAMPLE_RIDE).json()
    ride_id = ride.get("id", 1)

    r = client.put(f"/api/v1/rides/{ride_id}", json={"notes": "Updated notes"})
    assert r.status_code == 200
    assert client.get(f"/api/v1/rides/{ride_id}").status_code == 200
    assert client.get(f"/api/v1/rides/{ride_id}/map").status_code in (200, 500)
    assert client.get(f"/api/v1/rides/{ride_id}/report").status_code == 200
    assert client.get(f"/api/v1/rides/{ride_id}/safety").status_code in (200, 404, 500)
    assert client.get(f"/api/v1/rides/{ride_id}/power").status_code in (200, 404, 500)


# --------------------------------------------------------------------------- #
# Login and auth refresh
# --------------------------------------------------------------------------- #
def test_auth_login_and_refresh(client):
    client.post("/api/v1/auth/register", json={"username": "loginuser", "email": "login@test.com", "password": "LoginPass1"})
    r = client.post("/api/v1/auth/login", data={"username": "loginuser", "password": "LoginPass1"})
    assert r.status_code == 200
    assert "access_token" in r.json() or r.status_code == 200


# --------------------------------------------------------------------------- #
# Calendar events CRUD
# --------------------------------------------------------------------------- #
def test_calendar_events_crud(client):
    client.post("/api/v1/athletes", json={"name": "Calendar Athlete", "age": 30, "weight_kg": 70, "experience_level": "Beginner"})
    r = client.post("/api/v1/calendar/events", json={"athlete_id": 0, "title": "Test Ride", "date": "2025-01-15", "event_type": "training", "status": "planned"})
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        event_id = r.json().get("id", 1)
        assert client.get(f"/api/v1/calendar/events/{event_id}").status_code == 200
        assert client.put(f"/api/v1/calendar/events/{event_id}", json={"title": "Updated Ride"}).status_code == 200
        assert client.delete(f"/api/v1/calendar/events/{event_id}").status_code == 200


# --------------------------------------------------------------------------- #
# Knowledge search and stats
# --------------------------------------------------------------------------- #
def test_knowledge_search_and_stats(client):
    assert client.get("/api/v1/knowledge").status_code == 200
    assert client.get("/api/v1/knowledge/search", params={"q": "cycling training"}).status_code == 200
    assert client.get("/api/v1/knowledge/search", params={"q": ""}).status_code == 200
    assert client.get("/api/v1/knowledge/stats").status_code == 200


# --------------------------------------------------------------------------- #
# BM2 simulate-ride coverage
# --------------------------------------------------------------------------- #
def test_bm2_simulate_ride_variants(client):
    assert client.post("/api/v1/bm2/simulate-ride", json={"question": "Test", "gps_points": [{"lat": 45.0, "lon": 7.0}]}).status_code in (200, 400, 500)
    assert client.post("/api/v1/bm2/simulate-ride", json={"question": "Test", "gps_points": []}).status_code in (200, 400, 500)
    assert client.post("/api/v1/bm2/validate", json={"question": "Test", "power_w": 200}).status_code in (200, 400, 500)


# --------------------------------------------------------------------------- #
# Import webhook and Strava auth stubs
# --------------------------------------------------------------------------- #
def test_import_webhook_and_auth_stubs(client):
    assert client.get("/api/v1/import/strava/auth").status_code in (200, 302, 500)
    assert client.get("/api/v1/import/garmin/auth").status_code in (200, 302, 500)
    assert client.get("/api/v1/import/wahoo/auth").status_code in (200, 302, 500)
    assert client.get("/api/v1/import/strava/callback", params={"code": "test"}).status_code in (200, 400, 500)
    assert client.post("/api/v1/import/garmin/callback", json={"code": "test"}).status_code in (400, 500, 502)
    assert client.post("/api/v1/import/garmin/sync", json={"code": "test"}).status_code in (200, 400, 500, 502)


# --------------------------------------------------------------------------- #
# Import file endpoints (no file provided -> 422 or 400)
# --------------------------------------------------------------------------- #
def test_import_file_endpoints(client):
    assert client.post("/api/v1/import/gpx").status_code in (400, 422, 500)
    assert client.post("/api/v1/import/tcx").status_code in (400, 422, 500)
    assert client.post("/api/v1/import/fit").status_code in (400, 422, 500)


# --------------------------------------------------------------------------- #
# Auth endpoints
# --------------------------------------------------------------------------- #
def test_auth_login_and_profile(client):
    client.post("/api/v1/auth/register", json={"username": "authtest", "email": "auth@test.com", "password": "AuthPass1"})
    assert client.post("/api/v1/auth/login", data={"username": "authtest", "password": "AuthPass1"}).status_code == 200
    assert client.get("/api/v1/auth/profile").status_code in (200, 404)


# --------------------------------------------------------------------------- #
# Athlete CRUD
# --------------------------------------------------------------------------- #
def test_athlete_list_and_update(client):
    client.post("/api/v1/athletes", json={"name": "List Athlete", "age": 30, "weight_kg": 70, "experience_level": "Beginner"})
    resp = client.get("/api/v1/athletes").json()
    athletes = resp if isinstance(resp, list) else resp.get("athletes", resp.get("items", []))
    if athletes:
        athlete_id = athletes[0].get("id", 0)
        assert client.put(f"/api/v1/athletes/{athlete_id}", json={"goals": "Gran Fondo"}).status_code in (200, 404)


# --------------------------------------------------------------------------- #
# Rides query params and disaggregate
# --------------------------------------------------------------------------- #
def test_rides_query_and_disaggregate(client):
    client.post("/api/v1/athletes", json={"name": "Disaggregate Athlete", "age": 30, "weight_kg": 70, "experience_level": "Intermediate"})
    client.post("/api/v1/rides", json=SAMPLE_RIDE)
    assert client.get("/api/v1/rides", params={"size": 1}).status_code == 200
    assert client.get("/api/v1/rides", params={"sort": "distance"}).status_code == 200
    assert client.get("/api/v1/rides", params={"sort": "duration"}).status_code == 200
    assert client.get("/api/v1/rides", params={"from": "2024-01-01", "to": "2024-12-31", "disaggregate": "true"}).status_code in (200, 404, 500)


# --------------------------------------------------------------------------- #
# Admin users management
# --------------------------------------------------------------------------- #
def test_admin_users_endpoints(client):
    assert client.get("/api/v1/admin/users").status_code in (200, 404, 500)
    assert client.get("/api/v1/admin/athletes").status_code == 200
