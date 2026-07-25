"""Tests for charts API endpoints.

Covers /charts/speed/{ride_id}, /charts/duration, /charts/distance/{ride_id},
/charts/elevation/{ride_id} including access control and error states.
Chart generation is mocked to avoid matplotlib recursion issues in test env.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from bike_analyzer.backend.api.app_factory import create_app
from bike_analyzer.backend.db import database as db_mod
from bike_analyzer.backend.security import create_access_token


@pytest.fixture
def athlete_client(db_path):
    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    athlete_id = db_mod.save_athlete({"name": "Chart Rider", "experience_level": "Intermediate"})
    db_mod.update_athlete(athlete_id, {"tenant_id": athlete_id})
    token = create_access_token(subject=str(athlete_id), is_admin=False, tenant_id=athlete_id)
    tc = TestClient(create_app())
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc, athlete_id


@pytest.fixture
def admin_client(db_path):
    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    admin_id = db_mod.save_athlete({"name": "Admin", "experience_level": "Advanced"})
    db_mod.update_athlete(admin_id, {"tenant_id": admin_id, "is_admin": True})
    token = create_access_token(subject=str(admin_id), is_admin=True, tenant_id=admin_id)
    tc = TestClient(create_app())
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc, admin_id


@pytest.fixture
def second_athlete_client(db_path):
    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    aid = db_mod.save_athlete({"name": "Other Rider", "experience_level": "Beginner"})
    db_mod.update_athlete(aid, {"tenant_id": aid})
    token = create_access_token(subject=str(aid), is_admin=False, tenant_id=aid)
    tc = TestClient(create_app())
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc, aid


def _create_ride_with_gps(athlete_id):
    """Helper to create a ride with GPS points for chart generation."""
    ride_id = db_mod.save_ride({
        "athlete_id": athlete_id,
        "date": "2024-06-15T10:00:00Z",
        "distance_km": 25.0,
        "duration_minutes": 60.0,
        "avg_speed_kmh": 25.0,
        "elevation_gain_m": 200.0,
        "calories": 600.0,
        "gps_points": [
            {"lat": 45.0, "lon": 7.0, "timestamp": "2024-06-15T10:00:00Z", "power": 200.0, "heart_rate": 150.0, "altitude": 200.0},
            {"lat": 45.1, "lon": 7.1, "timestamp": "2024-06-15T10:01:00Z", "power": 210.0, "heart_rate": 155.0, "altitude": 210.0},
            {"lat": 45.2, "lon": 7.2, "timestamp": "2024-06-15T10:02:00Z", "power": 220.0, "heart_rate": 160.0, "altitude": 220.0},
        ],
    })
    return ride_id


def _mock_chart(*args, **kwargs):
    """No-op chart generator that creates an empty PNG file."""
    path = kwargs.get("path") or (args[1] if len(args) > 1 else "chart.png")
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00")


class TestChartsSpeed:
    def test_speed_chart_returns_png(self, athlete_client):
        tc, aid = athlete_client
        ride_id = _create_ride_with_gps(aid)
        with patch("bike_analyzer.backend.analytics.analytics.create_speed_chart", side_effect=_mock_chart):
            resp = tc.get(f"/api/v1/charts/speed/{ride_id}")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"

    def test_speed_chart_ride_not_found(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/charts/speed/99999")
        assert resp.status_code == 404

    def test_speed_chart_no_gps_returns_400(self, athlete_client):
        tc, aid = athlete_client
        ride_id = db_mod.save_ride({
            "athlete_id": aid,
            "date": "2024-06-15T10:00:00Z",
            "distance_km": 25.0,
            "duration_minutes": 60.0,
        })
        resp = tc.get(f"/api/v1/charts/speed/{ride_id}")
        assert resp.status_code == 400

    def test_speed_chart_other_athlete_forbidden(self, athlete_client, second_athlete_client):
        tc, aid = athlete_client
        tc2, aid2 = second_athlete_client
        ride_id = _create_ride_with_gps(aid)
        resp = tc2.get(f"/api/v1/charts/speed/{ride_id}")
        assert resp.status_code == 403

    def test_speed_chart_unauthorized(self, db_path):
        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        tc = TestClient(create_app())
        resp = tc.get("/api/v1/charts/speed/1")
        assert resp.status_code == 401


class TestChartsDuration:
    def test_duration_chart_returns_png(self, athlete_client):
        tc, aid = athlete_client
        _create_ride_with_gps(aid)
        with patch("bike_analyzer.backend.analytics.analytics.create_duration_chart", side_effect=_mock_chart):
            resp = tc.get("/api/v1/charts/duration")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"

    def test_duration_chart_empty_rides(self, athlete_client):
        tc, aid = athlete_client
        with patch("bike_analyzer.backend.analytics.analytics.create_duration_chart", side_effect=_mock_chart):
            resp = tc.get("/api/v1/charts/duration")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"

    def test_duration_chart_unauthorized(self, db_path):
        os.environ["DB_PATH"] = db_path
        db_mod.DB_PATH = db_path
        db_mod.init_db()
        tc = TestClient(create_app())
        resp = tc.get("/api/v1/charts/duration")
        assert resp.status_code == 401


class TestChartsDistance:
    def test_distance_chart_returns_png(self, athlete_client):
        tc, aid = athlete_client
        ride_id = _create_ride_with_gps(aid)
        with patch("bike_analyzer.backend.analytics.analytics.create_distance_chart", side_effect=_mock_chart):
            resp = tc.get(f"/api/v1/charts/distance/{ride_id}")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"

    def test_distance_chart_ride_not_found(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/charts/distance/99999")
        assert resp.status_code == 404

    def test_distance_chart_no_gps_returns_400(self, athlete_client):
        tc, aid = athlete_client
        ride_id = db_mod.save_ride({
            "athlete_id": aid,
            "date": "2024-06-15T10:00:00Z",
            "distance_km": 25.0,
            "duration_minutes": 60.0,
        })
        resp = tc.get(f"/api/v1/charts/distance/{ride_id}")
        assert resp.status_code == 400


class TestChartsElevation:
    def test_elevation_chart_returns_png(self, athlete_client):
        tc, aid = athlete_client
        ride_id = _create_ride_with_gps(aid)
        with patch("bike_analyzer.backend.analytics.analytics.create_elevation_chart", side_effect=_mock_chart):
            resp = tc.get(f"/api/v1/charts/elevation/{ride_id}")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"

    def test_elevation_chart_ride_not_found(self, athlete_client):
        tc, _ = athlete_client
        resp = tc.get("/api/v1/charts/elevation/99999")
        assert resp.status_code == 404

    def test_elevation_chart_no_gps_returns_400(self, athlete_client):
        tc, aid = athlete_client
        ride_id = db_mod.save_ride({
            "athlete_id": aid,
            "date": "2024-06-15T10:00:00Z",
            "distance_km": 25.0,
            "duration_minutes": 60.0,
        })
        resp = tc.get(f"/api/v1/charts/elevation/{ride_id}")
        assert resp.status_code == 400
