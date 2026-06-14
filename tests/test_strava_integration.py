"""Tests for Strava integration."""

import pytest

from bike_analyzer.backend.ingestion.strava_client import (
    generate_code_challenge,
    generate_code_verifier,
    strava_to_ride,
)


def test_generate_code_verifier_returns_string():
    v = generate_code_verifier()
    assert isinstance(v, str)
    assert len(v) > 0


def test_generate_code_challenge_matches_verifier():
    v = generate_code_verifier()
    c = generate_code_challenge(v)
    assert isinstance(c, str)
    assert len(c) > 0


def test_strava_to_ride_cycling_activity():
    act = {
        "id": 12345,
        "name": "Morning Ride",
        "sport_type": "Ride",
        "start_date_local": "2026-06-14T08:00:00Z",
        "distance": 25000,
        "moving_time": 3600,
        "average_speed": 7.0,
        "total_elevation_gain": 320,
        "average_heartrate": 145,
        "calories": 600,
    }
    ride = strava_to_ride(act, weight_kg=72.0)
    assert "error" not in ride or not ride.get("error")
    assert ride["distance_km"] == 25.0
    assert ride["duration_minutes"] == 60.0
    assert ride["avg_speed_kmh"] == 25.2
    assert ride["elevation_gain_m"] == 320
    assert ride["heart_rate_avg"] == 145
    assert ride["external_source"] == "strava"
    assert ride["external_id"] == "12345"
    assert ride["title"] == "Morning Ride"


def test_strava_to_ride_skips_non_cycling():
    act = {
        "id": 999,
        "sport_type": "Run",
        "start_date_local": "2026-06-14T08:00:00Z",
        "distance": 10000,
        "moving_time": 2400,
    }
    ride = strava_to_ride(act)
    assert ride.get("skipped") is True


def test_strava_to_ride_handles_zero_times():
    act = {
        "id": 1,
        "sport_type": "VirtualRide",
        "start_date_local": "2026-06-14T08:00:00Z",
        "distance": 0,
        "moving_time": 0,
    }
    ride = strava_to_ride(act)
    assert ride["avg_speed_kmh"] == 0


def test_strava_authorization_url_requires_client_id(monkeypatch):
    import bike_analyzer.backend.ingestion.strava_client as sc
    monkeypatch.setattr(sc, "STRAVA_CLIENT_ID", "")
    with pytest.raises(RuntimeError, match="STRAVA_CLIENT_ID"):
        sc.get_authorization_url()
