"""Test Google Maps API (mock mode)."""
from bike_analyzer.backend.models.models import GPSPoint
from bike_analyzer.backend.maps.google_maps import get_google_api_key, create_google_static_map
from datetime import datetime, timezone


def test_get_google_api_key_no_env():
    key = get_google_api_key()
    assert key is None or isinstance(key, str)


def test_create_google_static_map_basic():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc)),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc)),
    ]
    path = create_google_static_map(points, "test-api-key-mock", "test_map.png")
    assert path == "test_map.png"


def test_create_google_static_map_empty_points():
    try:
        create_google_static_map([], "test-api-key-mock", "empty_map.png")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "No GPS points" in str(e)