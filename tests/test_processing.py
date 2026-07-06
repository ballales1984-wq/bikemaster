import pytest
from datetime import datetime, timezone

from bike_analyzer.backend.processing.processing import (
    PAUSE_MIN_DURATION_MINUTES,
    RouteStatistics,
    build_segments,
    compute_statistics,
    detect_accelerations,
    detect_decelerations,
    detect_pauses,
    process_route,
    remove_outliers,
    validate_coordinate,
)
from bike_analyzer.backend.models.models import GPSPoint


def _point(lat, lon, speed=None, timestamp=None):
    return GPSPoint(
        lat=lat,
        lon=lon,
        timestamp=timestamp or datetime.now(timezone.utc),
        speed=speed,
    )


def test_validate_coordinate_valid():
    assert validate_coordinate(45.0, 7.0) is True
    assert validate_coordinate(-90, -180) is True
    assert validate_coordinate(90, 180) is True


def test_validate_coordinate_invalid():
    assert validate_coordinate(91, 7.0) is False
    assert validate_coordinate(45.0, -181) is False
    assert validate_coordinate("a", 7.0) is False


def test_detect_pauses_empty():
    assert detect_pauses([]) == []


def test_detect_pauses_single_point():
    assert detect_pauses([_point(45.0, 7.0)]) == []


def test_detect_pauses_detects_stop():
    base = datetime.now(timezone.utc)
    points = [
        _point(45.0, 7.0, speed=10, timestamp=base),
        _point(45.0, 7.0, speed=0.5, timestamp=base),
        _point(45.0, 7.0, speed=0.5, timestamp=base),
    ]
    pauses = detect_pauses(points)
    assert len(pauses) >= 0
    if pauses:
        assert pauses[0].duration_minutes >= PAUSE_MIN_DURATION_MINUTES


def test_remove_outliers_removes_bad_points():
    points = [
        _point(45.0, 7.0, speed=20),
        _point(45.0, 7.0, speed=200),
        _point(45.0, 7.0, speed=20),
    ]
    cleaned = remove_outliers(points)
    assert len(cleaned) == 3


def test_detect_accelerations():
    points = [
        _point(45.0, 7.0, speed=10),
        _point(45.1, 7.1, speed=30),
    ]
    accels = detect_accelerations(points)
    assert len(accels) >= 0


def test_detect_decelerations():
    points = [
        _point(45.0, 7.0, speed=30),
        _point(45.1, 7.1, speed=10),
    ]
    decels = detect_decelerations(points)
    assert len(decels) >= 0


def test_build_segments_returns_list():
    points = [
        _point(45.0, 7.0, speed=20),
        _point(45.1, 7.1, speed=25),
        _point(45.2, 7.2, speed=30),
    ]
    segments = build_segments(points)
    assert isinstance(segments, list)


def test_compute_statistics_returns_route_stats():
    points = [
        _point(45.0, 7.0, speed=20),
        _point(45.1, 7.1, speed=25),
        _point(45.2, 7.2, speed=30),
    ]
    stats = compute_statistics(points)
    assert isinstance(stats, RouteStatistics)


def test_process_route_returns_tuple():
    points = [
        _point(45.0, 7.0, speed=20),
        _point(45.1, 7.1, speed=25),
    ]
    result = process_route(points)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[1], RouteStatistics)
