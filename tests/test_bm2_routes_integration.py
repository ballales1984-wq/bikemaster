"""Test integrazione route /api/v1/bm2/simulate-ride col flusso Ride."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bike_analyzer.backend.api import bm2_routes  # noqa: E402
from bike_analyzer.backend.api.bm2_routes import _context_kwargs  # noqa: E402
from bike_analyzer.core.models import GPSPoint  # noqa: E402


def _fake_ride_dict():
    return {
        "id": 1, "athlete_id": 1, "tenant_id": 1,
        "distance_km": 12.0, "duration_minutes": 60.0, "avg_speed_kmh": 12.0,
        "weight_kg": 75.0, "elevation_gain_m": 160.0,
        "gps_points": [
            {"lat": 45.0, "lon": 9.0, "altitude": 200.0,
             "timestamp": "2026-07-10T08:00:00+00:00"},
            {"lat": 45.005, "lon": 9.005, "altitude": 360.0,
             "timestamp": "2026-07-10T09:00:00+00:00"},
        ],
    }


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(bm2_routes.bm2_router, prefix="/api/v1/bm2")
    app.dependency_overrides[bm2_routes.get_current_user] = lambda: {"is_admin": True, "id": 1}
    monkeypatch.setattr(
        "bike_analyzer.backend.db.database.get_ride", lambda ride_id: _fake_ride_dict()
    )
    return TestClient(app)


def test_context_kwargs_mapping():
    req = bm2_routes.Bm2SimulateRideRequest(
        bike={"weight": 7.0, "cda": 0.3}, world={"wind_speed": 2.0, "surface": "gravel"}
    )
    kwargs = _context_kwargs(req)
    assert kwargs["bike_weight_kg"] == 7.0
    assert kwargs["cda"] == 0.3
    assert kwargs["wind_speed_ms"] == 2.0
    assert kwargs["surface"] == "gravel"


def test_simulate_ride_by_id(client):
    resp = client.post(
        "/api/v1/bm2/simulate-ride",
        json={"ride_id": 1, "override": {"athlete_weight_delta_kg": -5.0}},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "comparison" in body
    assert "baseline" in body["comparison"] and "scenario" in body["comparison"]
    assert body["ride_id"] == 1
    assert isinstance(body["summary"], str)


def test_simulate_ride_inline_requires_points(client):
    resp = client.post("/api/v1/bm2/simulate-ride", json={"override": {}})
    assert resp.status_code == 400


def test_simulate_ride_not_found(client, monkeypatch):
    monkeypatch.setattr("bike_analyzer.backend.db.database.get_ride", lambda ride_id: None)
    resp = client.post(
        "/api/v1/bm2/simulate-ride",
        json={"ride_id": 999, "override": {"athlete_weight_delta_kg": -5.0}},
    )
    assert resp.status_code == 404


def _power_ride_dict():
    return {
        "id": 1, "athlete_id": 1, "tenant_id": 1,
        "distance_km": 12.0, "duration_minutes": 60.0, "avg_speed_kmh": 12.0,
        "weight_kg": 75.0,
        "gps_points": [
            {
                "lat": 45.0 + 0.001 * i, "lon": 9.0, "altitude": 100.0 + 5.0 * i,
                "timestamp": f"2026-07-10T08:0{i}:00+00:00",
                "power": 200.0 + i,
            }
            for i in range(8)
        ],
    }


def test_validate_ride_with_power_meter(client, monkeypatch):
    monkeypatch.setattr(
        "bike_analyzer.backend.db.database.get_ride", lambda ride_id: _power_ride_dict()
    )
    resp = client.post("/api/v1/bm2/validate", json={"ride_id": 1})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "validation" in body
    for key in ("mae_w", "rmse_w", "bias_w", "r2", "n_points"):
        assert key in body["validation"]
    assert body["validation"]["n_points"] >= 5


def test_validate_insufficient_power_data_returns_422(client):
    # _fake_ride_dict non ha dati power-meter -> 422
    resp = client.post("/api/v1/bm2/validate", json={"ride_id": 1})
    assert resp.status_code == 422
