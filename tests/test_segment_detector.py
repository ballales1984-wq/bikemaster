"""Tests for automatic segment detection."""
from datetime import datetime, timezone

from bike_analyzer.backend.models.models import GPSPoint
from bike_analyzer.backend.processing.segment_detector import (
    detect_all_segments,
    detect_climb_segments,
)


def make_point(lat: float, lon: float, alt: float = None, hours: int = 0, mins: int = 0, secs: int = 0):
    """Create a GPS point with timestamp."""
    ts = datetime(2024, 1, 15, 8, 0, 0, tzinfo=timezone.utc)
    total_secs = hours * 3600 + mins * 60 + secs
    mins_from_secs = total_secs // 60
    secs_final = total_secs % 60
    ts = ts.replace(minute=mins_from_secs, second=secs_final)
    return GPSPoint(lat=lat, lon=lon, timestamp=ts, altitude=alt, speed=20.0)


def test_detect_climb_basic():
    """Test basic climb detection."""
    points = [
        make_point(45.0 + i * 0.001, 10.0, alt=i * 10, secs=i * 30)
        for i in range(10)
    ]
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
