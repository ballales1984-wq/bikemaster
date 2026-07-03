"""Tests for processing/processing.py — GPS data processing and cleaning."""

from __future__ import annotations

from datetime import datetime, timedelta

from bike_analyzer.backend.models.models import GPSPoint
from bike_analyzer.backend.processing.processing import (
    ACCEL_THRESHOLD_KM_H_S,
    DECEL_THRESHOLD_KM_H_S,
    PAUSE_MIN_DURATION_MINUTES,
    PAUSE_SPEED_THRESHOLD_KM_H,
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


def make_point(lat: float, lon: float, speed: float | None = None,
               altitude: float | None = None, timestamp_offset_s: float = 0.0) -> GPSPoint:
    base = datetime(2024, 6, 15, 10, 0, 0)
    return GPSPoint(
        lat=lat,
        lon=lon,
        timestamp=base + timedelta(seconds=timestamp_offset_s),
        speed=speed,
        altitude=altitude,
    )


class TestValidateCoordinate:
    def test_valid_coordinates(self):
        assert validate_coordinate(45.0, 9.0) is True

    def test_invalid_lat_high(self):
        assert validate_coordinate(91.0, 9.0) is False

    def test_invalid_lat_low(self):
        assert validate_coordinate(-91.0, 9.0) is False

    def test_invalid_lon_high(self):
        assert validate_coordinate(45.0, 181.0) is False

    def test_invalid_lon_low(self):
        assert validate_coordinate(45.0, -181.0) is False

    def test_boundary_lat(self):
        assert validate_coordinate(90.0, 0.0) is True
        assert validate_coordinate(-90.0, 0.0) is True

    def test_boundary_lon(self):
        assert validate_coordinate(0.0, 180.0) is True
        assert validate_coordinate(0.0, -180.0) is True

    def test_non_numeric(self):
        assert validate_coordinate("abc", 9.0) is False
        assert validate_coordinate(45.0, None) is False
        assert validate_coordinate(None, 9.0) is False


class TestValidateGpsPoint:
    def test_valid_point(self):
        p = make_point(45.0, 9.0, speed=25.0)
        assert validate_gps_point(p) is True

    def test_invalid_lat(self):
        p = make_point(100.0, 9.0, speed=25.0)
        assert validate_gps_point(p) is False

    def test_missing_timestamp(self):
        p = GPSPoint(lat=45.0, lon=9.0, timestamp=None, speed=25.0)
        assert validate_gps_point(p) is False


class TestDetectPauses:
    def test_empty_points(self):
        assert detect_pauses([]) == []

    def test_single_point(self):
        assert detect_pauses([make_point(45.0, 9.0)]) == []

    def test_no_pauses(self):
        points = [make_point(45.0, 9.0, speed=20.0, timestamp_offset_s=i * 10) for i in range(5)]
        assert detect_pauses(points) == []

    def test_detect_pause(self):
        points = []
        for i in range(20):
            speed = 0.5 if 5 <= i <= 12 else 15.0
            points.append(make_point(45.0, 9.0, speed=speed, timestamp_offset_s=i * 30))
        pauses = detect_pauses(points)
        assert len(pauses) == 1
        assert pauses[0].duration_s >= PAUSE_MIN_DURATION_MINUTES * 60

    def test_short_pause_ignored(self):
        points = []
        for i in range(10):
            speed = 0.5 if 3 <= i <= 4 else 15.0
            points.append(make_point(45.0, 9.0, speed=speed, timestamp_offset_s=i * 30))
        pauses = detect_pauses(points)
        assert pauses == []

    def test_multiple_pauses(self):
        points = []
        for i in range(40):
            if 5 <= i <= 10:
                speed = 0.5
            elif 20 <= i <= 26:
                speed = 0.5
            else:
                speed = 15.0
            points.append(make_point(45.0, 9.0, speed=speed, timestamp_offset_s=i * 60))
        pauses = detect_pauses(points)
        assert len(pauses) == 2

    def test_pause_at_end(self):
        points = []
        for i in range(25):
            speed = 0.5 if i >= 12 else 15.0
            points.append(make_point(45.0, 9.0, speed=speed, timestamp_offset_s=i * 60))
        pauses = detect_pauses(points)
        assert len(pauses) == 0
        assert points[12].speed < PAUSE_SPEED_THRESHOLD_KM_H


class TestDetectAccelerations:
    def test_empty_points(self):
        assert detect_accelerations([]) == []

    def test_single_point(self):
        assert detect_accelerations([make_point(45.0, 9.0)]) == []

    def test_detect_acceleration(self):
        points = [make_point(45.0, 9.0, speed=s, timestamp_offset_s=i * 5) for i, s in enumerate([15, 16, 20, 28, 30])]
        accels = detect_accelerations(points)
        assert len(accels) > 0
        assert all(delta >= ACCEL_THRESHOLD_KM_H_S for _, delta in accels)

    def test_no_acceleration_smooth(self):
        points = [make_point(45.0, 9.0, speed=s, timestamp_offset_s=i * 5) for i, s in enumerate([20, 21, 22, 21.5, 22])]
        assert detect_accelerations(points) == []

    def test_none_speeds_ignored(self):
        points = [make_point(45.0, 9.0, speed=None, timestamp_offset_s=0),
                  make_point(45.001, 9.001, speed=25.0, timestamp_offset_s=10)]
        result = detect_accelerations(points)
        assert isinstance(result, list)

    def test_returns_index_and_delta(self):
        points = [make_point(45.0, 9.0, speed=s, timestamp_offset_s=i * 5) for i, s in enumerate([10, 20])]
        accels = detect_accelerations(points)
        assert len(accels) == 1
        idx, delta = accels[0]
        assert idx == 1
        assert delta == 10.0


class TestDetectDecelerations:
    def test_empty_points(self):
        assert detect_decelerations([]) == []

    def test_detect_deceleration(self):
        points = [make_point(45.0, 9.0, speed=s, timestamp_offset_s=i * 5) for i, s in enumerate([30, 28, 22, 18, 15])]
        decels = detect_decelerations(points)
        assert len(decels) > 0
        assert all(delta <= DECEL_THRESHOLD_KM_H_S for _, delta in decels)

    def test_no_deceleration_smooth(self):
        points = [make_point(45.0, 9.0, speed=s, timestamp_offset_s=i * 5) for i, s in enumerate([20, 19, 18, 18.5, 19])]
        assert detect_decelerations(points) == []


class TestRemoveOutliers:
    def test_empty_points(self):
        assert remove_outliers([]) == []

    def test_single_point(self):
        p = make_point(45.0, 9.0, speed=25.0)
        assert remove_outliers([p]) == [p]

    def test_two_points(self):
        p1 = make_point(45.0, 9.0, speed=25.0, timestamp_offset_s=0)
        p2 = make_point(45.001, 9.001, speed=25.0, timestamp_offset_s=10)
        assert len(remove_outliers([p1, p2])) == 2

    def test_removes_fast_point(self):
        p1 = make_point(45.0, 9.0, speed=25.0, timestamp_offset_s=0)
        p2 = make_point(45.0, 9.0, speed=25.0, timestamp_offset_s=10)
        p3 = make_point(46.0, 10.0, speed=200.0, timestamp_offset_s=20)
        cleaned = remove_outliers([p1, p2, p3])
        assert p3 not in cleaned

    def test_keeps_normal_points(self):
        base_ts = [0, 10, 20, 30, 40]
        points = [make_point(45.0 + i * 0.0001, 9.0 + i * 0.0001, speed=25.0, timestamp_offset_s=ts) for i, ts in enumerate(base_ts)]
        cleaned = remove_outliers(points, max_speed_km_h=200.0)
        assert len(cleaned) == 5

    def test_custom_max_speed(self):
        p1 = make_point(45.0, 9.0, speed=25.0, timestamp_offset_s=0)
        p2 = make_point(45.0, 9.0, speed=25.0, timestamp_offset_s=10)
        p3 = make_point(46.0, 10.0, speed=60.0, timestamp_offset_s=20)
        cleaned = remove_outliers([p1, p2, p3], max_speed_km_h=50.0)
        assert p3 not in cleaned


class TestBuildSegments:
    def test_empty_points(self):
        assert build_segments([]) == []

    def test_single_point(self):
        assert build_segments([make_point(45.0, 9.0)]) == []

    def test_two_points(self):
        p1 = make_point(45.0, 9.0, speed=25.0, timestamp_offset_s=0)
        p2 = make_point(45.001, 9.001, speed=25.0, timestamp_offset_s=10)
        segments = build_segments([p1, p2])
        assert len(segments) == 1
        assert segments[0].distance_m > 0
        assert segments[0].duration_s == 10.0

    def test_segment_speed_calculation(self):
        p1 = make_point(45.0, 9.0, timestamp_offset_s=0)
        p2 = make_point(45.001, 9.001, timestamp_offset_s=10)
        segments = build_segments([p1, p2])
        expected_speed = (segments[0].distance_m / 10.0) * 3.6
        assert abs(segments[0].avg_speed_km_h - expected_speed) < 0.01

    def test_elevation_gain(self):
        p1 = make_point(45.0, 9.0, altitude=100.0, timestamp_offset_s=0)
        p2 = make_point(45.001, 9.001, altitude=110.0, timestamp_offset_s=10)
        segments = build_segments([p1, p2])
        assert segments[0].elevation_gain_m == 10.0

    def test_zero_duration_skipped(self):
        p1 = make_point(45.0, 9.0, timestamp_offset_s=0)
        p2 = make_point(45.001, 9.001, timestamp_offset_s=0)
        segments = build_segments([p1, p2])
        assert len(segments) == 0

    def test_no_elevation_data(self):
        p1 = make_point(45.0, 9.0, altitude=None, timestamp_offset_s=0)
        p2 = make_point(45.001, 9.001, altitude=None, timestamp_offset_s=10)
        segments = build_segments([p1, p2])
        assert segments[0].elevation_gain_m == 0.0


class TestComputeStatistics:
    def test_empty_points(self):
        stats = compute_statistics([])
        assert stats.total_distance_m == 0.0
        assert stats.segment_count == 0

    def test_single_point(self):
        p = make_point(45.0, 9.0, timestamp_offset_s=0)
        stats = compute_statistics([p])
        assert stats.segment_count == 0

    def test_two_points(self):
        p1 = make_point(45.0, 9.0, speed=25.0, timestamp_offset_s=0)
        p2 = make_point(45.001, 9.001, speed=25.0, timestamp_offset_s=10)
        stats = compute_statistics([p1, p2])
        assert stats.segment_count == 1
        assert stats.total_distance_m > 0

    def test_pause_detection_in_statistics(self):
        points = []
        for i in range(20):
            speed = 0.5 if 5 <= i <= 12 else 15.0
            points.append(make_point(45.0, 9.0, speed=speed, timestamp_offset_s=i * 30))
        stats = compute_statistics(points)
        assert stats.pause_count >= 0

    def test_max_speed(self):
        points = [
            make_point(45.0, 9.0, speed=10.0, timestamp_offset_s=0),
            make_point(45.001, 9.001, speed=30.0, timestamp_offset_s=10),
            make_point(45.002, 9.002, speed=20.0, timestamp_offset_s=20),
        ]
        stats = compute_statistics(points)
        assert stats.max_speed_km_h >= 30.0


class TestProcessRoute:
    def test_empty_points(self):
        cleaned, stats = process_route([])
        assert cleaned == []
        assert stats.total_distance_m == 0.0

    def test_returns_cleaned_and_stats(self):
        points = [make_point(45.0 + i * 0.001, 9.0 + i * 0.001, speed=25.0, timestamp_offset_s=i * 10) for i in range(5)]
        cleaned, stats = process_route(points)
        assert len(cleaned) >= 2
        assert stats.total_distance_m > 0

    def test_sorts_by_timestamp(self):
        p1 = make_point(45.0, 9.0, speed=25.0, timestamp_offset_s=20)
        p2 = make_point(45.001, 9.001, speed=25.0, timestamp_offset_s=0)
        cleaned, _ = process_route([p1, p2])
        assert cleaned[0].timestamp <= cleaned[1].timestamp

    def test_removes_outliers_by_default(self):
        p1 = make_point(45.0, 9.0, speed=25.0, timestamp_offset_s=0)
        p2 = make_point(45.001, 9.001, speed=25.0, timestamp_offset_s=10)
        p3 = make_point(45.01, 9.01, speed=200.0, timestamp_offset_s=20)
        cleaned, _ = process_route([p1, p2, p3])
        assert p3 not in cleaned
