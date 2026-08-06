"""Test API BikeMaster 2.0 (route /api/v1/bm2)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

SAMPLE = {
    "question": "Quanta energia consumo in questo giro?",
    "athlete": {"weight": 75, "age": 34, "experience_level": "Intermediate", "max_hr": 190},
    "bike": {"weight": 8},
    "world": {"surface": "asphalt", "avg_slope": 4.0},
    "gps_points": [
        {"lat": 45.0, "lon": 9.0, "altitude": 200, "timestamp": "2026-07-10T08:00:00Z"},
        {"lat": 45.005, "lon": 9.005, "altitude": 360, "timestamp": "2026-07-10T09:00:00Z"},
    ],
    "sensors": [{"heart_rate": 140, "power": 180}, {"heart_rate": 165, "power": 240}],
}


def test_bm2_models_endpoint(client):
    r = client.get("/api/v1/bm2/models")
    assert r.status_code == 200
    models = r.json()["models"]
    names = {m["name"] for m in models}
    assert {"EnergyModel", "MovementModel", "FatigueModel"} <= names
    for m in models:
        assert m["formula"] and m["unit"]


def test_bm2_ask_endpoint(client):
    r = client.post("/api/v1/bm2/ask", json=SAMPLE)
    assert r.status_code == 200
    body = r.json()
    assert body["question"] == SAMPLE["question"]
    assert "EnergyModel" in body["models_used"]
    em = body["results"]["EnergyModel"]
    # ogni risultato riporta formula + dati + precisione + fonte
    assert em["formula"] and em["data_used"] and em["source"]
    assert em["precision"] > 0
    assert 0.0 <= em["confidence"] <= 1.0
    assert isinstance(body["insights"], list)


def test_bm2_simulate_endpoint(client):
    payload = dict(SAMPLE)
    payload["question"] = "Se peso -5 kg quanto risparmio?"
    r = client.post("/api/v1/bm2/simulate", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["simulation"] is not None
    assert body["simulation"]["deltas"]["EnergyModel"] < 0
