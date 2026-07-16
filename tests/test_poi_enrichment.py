"""Tests for the budget-limited SerpApi POI enrichment bridge (MVP)."""

from __future__ import annotations

import pytest

from bike_analyzer.backend.db import database as db
from bike_analyzer.backend.maps import poi_enrichment as pe
from bike_analyzer.backend.maps import serpapi_maps
from bike_analyzer.backend.settings import get_settings


@pytest.fixture
def enrich_db(db_path, monkeypatch):
    db.DB_PATH = db_path
    db.init_db()
    settings = get_settings()
    monkeypatch.setattr(settings, "serpapi_api_key", "test-key")
    monkeypatch.setattr(settings, "serpapi_monthly_budget", 250)
    yield db_path


def _local(name, lat, lon, category="cafe", address="Via Test 1"):
    return {
        "title": name,
        "gps_coordinates": {"latitude": lat, "longitude": lon},
        "type": category,
        "address": address,
    }


def test_no_api_key_does_not_query(enrich_db, monkeypatch):
    monkeypatch.setattr(get_settings(), "serpapi_api_key", "")
    monkeypatch.setattr(serpapi_maps, "get_serpapi_api_key", lambda: "")
    called = {"n": 0}

    def _boom(*a, **k):
        called["n"] += 1
        return None

    monkeypatch.setattr(serpapi_maps, "search_places", _boom)
    result = pe.enrich_pois_near(45.0, 9.0)
    assert result["queried"] is False
    assert result["reason"] == "no_api_key"
    assert called["n"] == 0


def test_saves_new_pois_and_maps_types(enrich_db, monkeypatch):
    data = {
        "local_results": [
            _local("Bar Sport", 45.0001, 9.0001, category="cafe"),
            _local("Fontana Vecchia", 45.0002, 9.0002, category="fountain"),
            _local("Museo del Ciclismo", 45.0003, 9.0003, category="museum"),
        ]
    }
    monkeypatch.setattr(serpapi_maps, "search_places", lambda *a, **k: data)

    result = pe.enrich_pois_near(45.0, 9.0, dedup_radius_m=10.0)
    assert result["queried"] is True
    assert result["saved"] == 3

    saved = db.get_nearby_pois(45.0, 9.0, radius_km=1.0)
    by_name = {p["name"]: p for p in saved}
    assert by_name["Bar Sport"]["type"] == "ristoro"
    assert by_name["Fontana Vecchia"]["type"] == "fontana"
    assert by_name["Museo del Ciclismo"]["type"] == "culturale"
    assert "source:serpapi" in by_name["Bar Sport"]["tags"]


def test_deduplicates_existing_pois(enrich_db, monkeypatch):
    db.save_poi(
        {"name": "Bar Sport", "description": "x", "lat": 45.0001, "lon": 9.0001, "type": "ristoro"}
    )
    data = {"local_results": [_local("Bar Sport", 45.00011, 9.00011)]}
    monkeypatch.setattr(serpapi_maps, "search_places", lambda *a, **k: data)

    result = pe.enrich_pois_near(45.0, 9.0, dedup_radius_m=200.0)
    assert result["saved"] == 0
    assert result["skipped_duplicates"] == 1


def test_skips_invalid_entries(enrich_db, monkeypatch):
    data = {
        "local_results": [
            {"title": "No Coords"},
            {"gps_coordinates": {"latitude": 45.0, "longitude": 9.0}},  # no name
            _local("Valid Cafe", 45.5, 9.5),
        ]
    }
    monkeypatch.setattr(serpapi_maps, "search_places", lambda *a, **k: data)

    result = pe.enrich_pois_near(45.0, 9.0)
    assert result["saved"] == 1
    assert result["skipped_invalid"] == 2


def test_budget_is_tracked_and_enforced(enrich_db, monkeypatch):
    monkeypatch.setattr(get_settings(), "serpapi_monthly_budget", 1)
    monkeypatch.setattr(serpapi_maps, "search_places", lambda *a, **k: {"local_results": []})

    assert pe.get_remaining_budget() == 1
    first = pe.enrich_pois_near(45.0, 9.0)
    assert first["queried"] is True
    assert pe.get_usage() == 1
    assert pe.get_remaining_budget() == 0

    second = pe.enrich_pois_near(46.0, 10.0)
    assert second["queried"] is False
    assert second["budget_exhausted"] is True
    assert second["reason"] == "budget_exhausted"


def test_falls_back_to_places_results_key(enrich_db, monkeypatch):
    data = {"places_results": [_local("Panificio", 45.1, 9.1, category="bakery")]}
    monkeypatch.setattr(serpapi_maps, "search_places", lambda *a, **k: data)

    result = pe.enrich_pois_near(45.0, 9.0)
    assert result["saved"] == 1
