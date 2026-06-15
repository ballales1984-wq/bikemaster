"""Tests for async_db module - basic coverage."""
import pytest
import os


def test_get_engine_lazy():
    from bike_analyzer.backend.db import async_db
    async_db._engine = None
    async_db._async_session_factory = None
    engine = async_db._get_engine()
    assert engine is not None


def test_get_session_factory_lazy():
    from bike_analyzer.backend.db import async_db
    async_db._async_session_factory = None
    factory = async_db.get_session_factory()
    assert factory is not None


def test_ride_model_to_dict():
    from bike_analyzer.backend.db import async_db
    from datetime import datetime, UTC

    class MockRow:
        id = 1
        athlete_id = 1
        date = "2024-06-15"
        distance_km = 25.0
        duration_minutes = 60
        avg_speed_kmh = 25.0
        weight_kg = 70
        calories = 400
        heart_rate_avg = 150
        elevation_gain_m = 200
        gps_points = '[{"lat": 45.0, "lon": 7.0}]'
        created_at = datetime.now(UTC)

    result = async_db._ride_model_to_dict(MockRow())
    assert result["id"] == 1
    assert result["gps_points"] == [{"lat": 45.0, "lon": 7.0}]