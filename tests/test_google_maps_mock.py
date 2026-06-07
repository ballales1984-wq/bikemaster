"""Test Google Maps API (mock mode)."""
from bike_analyzer.backend.models.models import GPSPoint
from bike_analyzer.backend.maps.google_maps import get_google_api_key, create_google_static_map, _speed_to_color, _build_speed_segments
from datetime import datetime, timezone


def test_get_google_api_key_no_env():
    key = get_google_api_key()
    assert key is None or isinstance(key, str)


def test_speed_to_color():
    assert _speed_to_color(None) == "0x0000ff"
    assert _speed_to_color(10) == "0xFF0000"
    assert _speed_to_color(20) == "0xFFFF00"
    assert _speed_to_color(30) == "0x00FF00"


def test_build_speed_segments():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc), speed=10),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc), speed=30),
        GPSPoint(lat=45.02, lon=9.02, timestamp=datetime(2024, 1, 1, 0, 2, tzinfo=timezone.utc), speed=None),
    ]
    segs = _build_speed_segments(points)
    assert len(segs) >= 1
    assert segs[0].color in ("0xFF0000", "0x0000ff", "0xFFFF00", "0x00FF00")


def test_build_speed_segments_empty():
    assert _build_speed_segments([]) == []


def test_create_google_static_map_basic():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc)),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc)),
    ]
    path = create_google_static_map(points, "test-api-key-mock", "test_map.png")
    assert path == "test_map.png"


def test_create_google_static_map_colored():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc), speed=10),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc), speed=30),
        GPSPoint(lat=45.02, lon=9.02, timestamp=datetime(2024, 1, 1, 0, 2, tzinfo=timezone.utc), speed=None),
    ]
    path = create_google_static_map(points, "test-api-key-mock", "test_map_colored.png", colored=True)
    assert path == "test_map_colored.png"


def test_create_google_static_map_empty_points():
    try:
        create_google_static_map([], "test-api-key-mock", "empty_map.png")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "No GPS points" in str(e)

def test_speed_to_color_high_speed():
    assert _speed_to_color(25) == "0x00FF00"
    assert _speed_to_color(30) == "0x00FF00"
    assert _speed_to_color(100) == "0x00FF00"

def test_build_speed_segments_single_point():
    points = [GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc), speed=10)]
    segs = _build_speed_segments(points)
    assert len(segs) == 1

def test_build_speed_segments_all_same_color():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc), speed=10),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc), speed=10),
    ]
    segs = _build_speed_segments(points)
    assert len(segs) == 1
    assert segs[0].color == "0xFF0000"

def test_create_google_static_map_colored_branch():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc), speed=10),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc), speed=10),
    ]
    path = create_google_static_map(points, "test-api-key-mock", "test_map_colored2.png", colored=True)
    assert path == "test_map_colored2.png"

import os
def teardown_function():
    for f in ["test_map.png", "test_map_colored.png", "test_map_colored2.png", "empty_map.png"]:
        if os.path.exists(f):
            os.remove(f)

def test_create_google_elevation_chart_no_points():
    from bike_analyzer.backend.maps.google_maps import create_google_elevation_chart
    result = create_google_elevation_chart([], "test-api-key-mock")
    assert result is None

def test_create_google_elevation_chart_invalid_api_key():
    from bike_analyzer.backend.maps.google_maps import create_google_elevation_chart
    points = [GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc))]
    result = create_google_elevation_chart(points, "invalid-key")
    assert result is None

def test_create_google_elevation_chart_short_api_key():
    from bike_analyzer.backend.maps.google_maps import create_google_elevation_chart
    points = [GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc))]
    result = create_google_elevation_chart(points, "short")
    assert result is None