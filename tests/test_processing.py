"""Tests for GPS processing module."""
from datetime import datetime, timedelta, timezone

from bike_analyzer.backend.models.models import GPSPoint
from bike_analyzer.backend.processing.processing import (
    build_segments,
    detect_accelerations,
    detect_decelerations,
    detect_pauses,
    process_route,
    remove_outliers,
    validate_coordinate,
    validate_gps_point,
)


def make_point(lat, lon, timestamp, altitude=None, speed=None) -> GPSPoint:
    return GPSPoint(lat=lat, lon=lon, timestamp=timestamp, altitude=altitude, speed=speed)


def test_validate_coordinate_valid():
    assert validate_coordinate(45.0, 9.0) is True


def test_validate_coordinate_invalid_lat():
    assert validate_coordinate(100.0, 9.0) is False
    assert validate_coordinate(-100.0, 9.0) is False


def test_validate_coordinate_invalid_lon():
    assert validate_coordinate(45.0, 200.0) is False
    assert validate_coordinate(45.0, -200.0) is False


def test_validate_coordinate_non_numeric():
    assert validate_coordinate("abc", 9.0) is False
    assert validate_coordinate(45.0, None) is False


def test_validate_gps_point():
    ts = datetime.now(timezone.utc)
    p = make_point(45.0, 9.0, ts)
    assert validate_gps_point(p) is True


def test_detect_pauses_none():
    points = [make_point(45.0, 9.0, datetime.now(timezone.utc) + timedelta(seconds=i), speed=10.0) for i in range(3)]
    pauses = detect_pauses(points)
    assert len(pauses) == 0


def test_detect_pauses_with_slow():
    t0 = datetime.now(timezone.utc)
    points = [
        make_point(45.0, 9.0, t0, speed=10.0),
        make_point(45.0, 9.001, t0 + timedelta(seconds=10), speed=10.0),
        make_point(45.0, 9.002, t0 + timedelta(seconds=200), speed=0.5),
        make_point(45.0, 9.003, t0 + timedelta(seconds=210), speed=0.5),
        make_point(45.0, 9.004, t0 + timedelta(seconds=220), speed=10.0),
    ]
    pauses = detect_pauses(points)
    assert len(pauses) == 1
    assert pauses[0].duration_s >= 180


def test_detect_accelerations():
    points = [
        make_point(45.0, 9.0, datetime.now(timezone.utc) + timedelta(seconds=i), speed=s) for i, s in enumerate([10.0, 15.0, 25.0])
    ]
    accels = detect_accelerations(points)
    assert len(accels) > 0


def test_detect_decelerations():
    points = [
        make_point(45.0, 9.0, datetime.now(timezone.utc) + timedelta(seconds=i), speed=s) for i, s in enumerate([25.0, 15.0, 10.0])
    ]
    decels = detect_decelerations(points)
    assert len(decels) > 0


def test_remove_outliers_fast_point():
    t0 = datetime.now(timezone.utc)
    normal = [make_point(45.0 + i * 0.001, 9.0 + i * 0.001, t0 + timedelta(seconds=i * 10), speed=20.0) for i in range(5)]
    outlier = make_point(45.1, 9.1, t0 + timedelta(seconds=60), speed=200.0)
    cleaned = remove_outliers(normal + [outlier])
    assert len(cleaned) <= 5


def test_build_segments_basic():
    t0 = datetime.now(timezone.utc)
    points = [make_point(45.0 + i * 0.01, 9.0 + i * 0.01, t0 + timedelta(seconds=i * 10), speed=20.0) for i in range(5)]
    segments = build_segments(points)
    assert len(segments) == 4
    for s in segments:
        assert s.distance_m > 0
        assert s.duration_s > 0


def test_process_route():
    t0 = datetime.now(timezone.utc)
    points = [make_point(45.0 + i * 0.001, 9.0 + i * 0.001, t0 + timedelta(seconds=i * 10), speed=20.0) for i in range(10)]
    cleaned, stats = process_route(points)
    assert len(cleaned) > 0
    assert stats.total_distance_m > 0
