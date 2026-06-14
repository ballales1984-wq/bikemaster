"""Tests for automatic segment detection."""

from datetime import UTC, datetime

import pytest

from bike_analyzer.backend.models.models import GPSPoint
from bike_analyzer.backend.processing.segment_detector import (
    ClimbSegment,
    calculate_grade_percent,
    categorize_climb,
    detect_all_segments,
    detect_climb_segments,
    segment_to_dict,
)


def make_point(
    lat: float, lon: float, alt: float = None, hours: int = 0, mins: int = 0, secs: int = 0
):
    """Create a GPS point with timestamp."""
    ts = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
    total_secs = hours * 3600 + mins * 60 + secs
    mins_from_secs = total_secs // 60
    secs_final = total_secs % 60
    ts = ts.replace(minute=mins_from_secs, second=secs_final)
    return GPSPoint(lat=lat, lon=lon, timestamp=ts, altitude=alt, speed=20.0)


def test_detect_climb_basic():
    """Test basic climb detection."""
    points = [make_point(45.0 + i * 0.001, 10.0, alt=i * 10, secs=i * 30) for i in range(10)]
    climbs = detect_climb_segments(points, min_elevation_m=30)
    assert len(climbs) >= 1
    assert climbs[0].elevation_gain_m > 0


def test_detect_all_segments():
    """Test segment detection."""
    points = [
        make_point(45.0 + i * 0.002, 10.0, alt=i * 5 if i % 2 == 0 else None, secs=i * 60)
        for i in range(20)
    ]
    segments = detect_all_segments(points, min_length_m=500)
    assert len(segments) >= 1
    for seg in segments:
        assert seg.distance_m >= 500


class TestCalculateGradePercent:
    def test_positive_grade(self):
        assert calculate_grade_percent(10.0, 100.0) == 10.0

    def test_zero_distance(self):
        assert calculate_grade_percent(10.0, 0) == 0.0

    def test_negative_distance(self):
        assert calculate_grade_percent(10.0, -5.0) == 0.0

    def test_steep_grade(self):
        assert calculate_grade_percent(50.0, 100.0) == 50.0

    def test_flat(self):
        assert calculate_grade_percent(0.0, 100.0) == 0.0


class TestCategorizeClimb:
    def test_hc_category(self):
        assert categorize_climb(20.0, 50000) == "hc"

    def test_cat1(self):
        assert categorize_climb(15.0, 50000) == "cat1"

    def test_cat2(self):
        assert categorize_climb(10.0, 30000) == "cat2"

    def test_cat3(self):
        assert categorize_climb(6.0, 10000) == "cat3"

    def test_cat4(self):
        assert categorize_climb(3.0, 2000) == "cat4"

    def test_unclassified_short(self):
        assert categorize_climb(2.0, 1000) == "unclassified"

    def test_first_match_wins(self):
        assert categorize_climb(20.0, 50000) == "hc"


class TestClimbSegmentDataclass:
    def test_create_climb_segment(self):
        start = make_point(45.0, 9.0, alt=100)
        end = make_point(45.01, 9.01, alt=200)
        seg = ClimbSegment(
            start_idx=0,
            end_idx=5,
            distance_m=1000.0,
            elevation_gain_m=100.0,
            avg_grade_percent=10.0,
            category="cat3",
            start_point=start,
            end_point=end,
        )
        assert seg.distance_m == 1000.0
        assert seg.category == "cat3"

    def test_climb_segment_defaults(self):
        start = make_point(45.0, 9.0)
        seg = ClimbSegment(
            start_idx=0,
            end_idx=1,
            distance_m=100.0,
            elevation_gain_m=5.0,
            avg_grade_percent=5.0,
            category="cat4",
            start_point=start,
            end_point=start,
        )
        assert seg.elevation_gain_m == 5.0


class TestSegmentToDict:
    def test_serialization(self):
        start = make_point(45.0, 9.0, alt=100)
        end = make_point(45.01, 9.01, alt=200)
        seg = ClimbSegment(
            start_idx=0,
            end_idx=5,
            distance_m=1250.0,
            elevation_gain_m=100.0,
            avg_grade_percent=8.0,
            category="cat2",
            start_point=start,
            end_point=end,
        )
        d = segment_to_dict(seg)
        assert d["distance_km"] == 1.25
        assert d["elevation_gain_m"] == 100.0
        assert d["avg_grade_percent"] == 8.0
        assert d["category"] == "cat2"
        assert d["start_lat"] == 45.0
        assert d["end_lon"] == 9.01

    def test_rounding(self):
        start = make_point(45.0, 9.0)
        seg = ClimbSegment(
            start_idx=0, end_idx=1, distance_m=1234.0, elevation_gain_m=56.789,
            avg_grade_percent=4.56, category="cat4", start_point=start, end_point=start,
        )
        d = segment_to_dict(seg)
        assert d["distance_km"] == 1.23
        assert d["elevation_gain_m"] == 56.8
        assert d["avg_grade_percent"] == 4.6


def test_detect_climb_short_ride():
    """Test with fewer than 3 points."""
    points = [make_point(45.0, 10.0), make_point(45.01, 10.01)]
    climbs = detect_climb_segments(points)
    assert climbs == []


def test_detect_climb_no_elevation_gain():
    """Test with flat route (no altitude data)."""
    points = [make_point(45.0 + i * 0.001, 10.0, alt=None, secs=i * 30) for i in range(10)]
    climbs = detect_climb_segments(points, min_elevation_m=30)
    assert climbs == []


def test_detect_climb_category_assignment():
    """Test that category is assigned correctly."""
    points = [make_point(45.0 + i * 0.001, 10.0, alt=i * 15, secs=i * 30) for i in range(20)]
    climbs = detect_climb_segments(points, min_elevation_m=10)
    if climbs:
        assert climbs[0].category in ("hc", "cat1", "cat2", "cat3", "cat4", "unclassified")
        assert 0 <= climbs[0].avg_grade_percent <= 100
