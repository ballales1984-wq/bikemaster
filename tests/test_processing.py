"""Tests for GPS data processing module."""

from datetime import UTC, datetime

import pytest

from bike_analyzer.backend.models.models import GPSPoint, Pause, RouteStatistics, Segment
from bike_analyzer.backend.processing.processing import (
    build_segments,
    compute_statistics,
    detect_accelerations,
    detect_decelerations,
    detect_pauses,
    process_route,
    remove_outliers,
    validate_coordinate,
    validate_gps_point,
)


def _point(lat, lon, alt=None, speed=None, hours=0, mins=0, secs=0):
    from datetime import timedelta
    base = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
    ts = base + timedelta(minutes=mins, seconds=secs)
    return GPSPoint(lat=lat, lon=lon, altitude=alt, speed=speed, timestamp=ts)


class TestValidateCoordinate:
    def test_valid_coords(self):
        assert validate_coordinate(45.0, 9.0) is True

    def test_invalid_lat_negative(self):
        assert validate_coordinate(-91, 9.0) is False

    def test_invalid_lat_positive(self):
        assert validate_coordinate(91, 9.0) is False

    def test_invalid_lon_negative(self):
        assert validate_coordinate(45.0, -181) is False

    def test_invalid_lon_positive(self):
        assert validate_coordinate(45.0, 181) is False

    def test_boundary_lat(self):
        assert validate_coordinate(-90, 9.0) is True
        assert validate_coordinate(90, 9.0) is True

    def test_boundary_lon(self):
        assert validate_coordinate(45.0, -180) is True
        assert validate_coordinate(45.0, 180) is True

    def test_non_numeric_lat(self):
        assert validate_coordinate("abc", 9.0) is False

    def test_non_numeric_lon(self):
        assert validate_coordinate(45.0, None) is False


class TestValidateGpsPoint:
    def test_valid_point(self):
        p = _point(45.0, 9.0)
        assert validate_gps_point(p) is True

    def test_invalid_timestamp(self):
        p = _point(45.0, 9.0)
        p.timestamp = "not_a_date"
        assert validate_gps_point(p) is False


class TestDetectPauses:
    def test_no_pauses_fast_ride(self):
        points = [_point(45.0 + i * 0.001, 9.0, speed=15.0, secs=i * 10) for i in range(10)]
        pauses = detect_pauses(points)
        assert pauses == []

    def test_detect_pause(self):
        points = [_point(45.0 + i * 0.0001, 9.0, speed=15.0 if i < 3 or i > 8 else 0.5, secs=i * 30) for i in range(12)]
        pauses = detect_pauses(points)
        assert len(pauses) >= 1
        assert pauses[0].duration_s >= 180

    def test_short_pause_ignored(self):
        points = [_point(45.0 + i * 0.0001, 9.0, speed=0.5 if i == 2 else 15.0, secs=i * 10) for i in range(5)]
        pauses = detect_pauses(points)
        assert pauses == []

    def test_few_points(self):
        points = [_point(45.0, 9.0)]
        assert detect_pauses(points) == []


class TestDetectAccelerations:
    def test_detect_acceleration(self):
        points = [_point(45.0 + i * 0.001, 9.0, speed=10.0 + i * 3, secs=i * 10) for i in range(5)]
        accels = detect_accelerations(points)
        assert len(accels) >= 1
        assert accels[0][0] > 0

    def test_no_acceleration(self):
        points = [_point(45.0 + i * 0.001, 9.0, speed=15.0, secs=i * 10) for i in range(5)]
        accels = detect_accelerations(points)
        assert accels == []

    def test_none_speeds(self):
        points = [_point(45.0 + i * 0.001, 9.0, speed=None, secs=i * 10) for i in range(5)]
        accels = detect_accelerations(points)
        assert accels == []


class TestDetectDecelerations:
    def test_detect_deceleration(self):
        points = [_point(45.0 + i * 0.001, 9.0, speed=20.0 - i * 3, secs=i * 10) for i in range(5)]
        decels = detect_decelerations(points)
        assert len(decels) >= 1

    def test_no_deceleration(self):
        points = [_point(45.0 + i * 0.001, 9.0, speed=15.0, secs=i * 10) for i in range(5)]
        decels = detect_decelerations(points)
        assert decels == []


class TestRemoveOutliers:
    def test_no_outliers(self):
        points = [_point(45.0 + i * 0.0005, 9.0, speed=15.0, secs=i * 30) for i in range(5)]
        cleaned = remove_outliers(points)
        assert len(cleaned) == 5

    def test_remove_outlier(self):
        points = [_point(45.0 + i * 0.005, 9.0, speed=15.0, secs=i * 30) for i in range(5)]
        cleaned = remove_outliers(points, max_speed_km_h=30.0)
        assert len(cleaned) < len(points)

    def test_few_points(self):
        points = [_point(45.0, 9.0), _point(45.01, 9.01)]
        cleaned = remove_outliers(points)
        assert len(cleaned) >= 2


class TestBuildSegments:
    def test_basic_segments(self):
        points = [_point(45.0 + i * 0.001, 9.0, secs=i * 10) for i in range(5)]
        segments = build_segments(points)
        assert len(segments) == 4
        assert all(isinstance(s, Segment) for s in segments)

    def test_segment_distance(self):
        points = [
            _point(45.0, 9.0, secs=0),
            _point(45.01, 9.01, secs=10),
        ]
        segments = build_segments(points)
        assert len(segments) == 1
        assert segments[0].distance_m > 0

    def test_elevation_gain(self):
        points = [
            _point(45.0, 9.0, alt=100.0, secs=0),
            _point(45.01, 9.01, alt=150.0, secs=10),
        ]
        segments = build_segments(points)
        assert segments[0].elevation_gain_m > 0


class TestComputeStatistics:
    def test_basic_stats(self):
        points = [_point(45.0 + i * 0.001, 9.0, secs=i * 10) for i in range(5)]
        stats = compute_statistics(points)
        assert isinstance(stats, RouteStatistics)
        assert stats.total_distance_m > 0
        assert stats.segment_count == 4

    def test_empty_points(self):
        stats = compute_statistics([])
        assert stats.total_distance_m == 0
        assert stats.total_duration_s == 0

    def test_single_point(self):
        points = [_point(45.0, 9.0)]
        stats = compute_statistics(points)
        assert stats.total_distance_m == 0


class TestProcessRoute:
    def test_process_route(self):
        points = [_point(45.0 + i * 0.001, 9.0, secs=i * 10) for i in range(10)]
        cleaned, stats = process_route(points)
        assert len(cleaned) >= 2
        assert stats.total_distance_m > 0
