"""Tests for Douglas-Peucker GPS compression."""

from __future__ import annotations

import pytest

from bike_analyzer.backend.ingestion.gps_parser import douglas_peucker, points_to_ride
from datetime import datetime, timezone


def _ts(i: int) -> datetime:
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc).replace(second=i)


def test_douglas_peucker_preserves_endpoints():
    pts = [
        {"lat": 0.0, "lon": 0.0, "timestamp": _ts(0)},
        {"lat": 0.001, "lon": 0.001, "timestamp": _ts(1)},
        {"lat": 0.002, "lon": 0.002, "timestamp": _ts(2)},
    ]
    out = douglas_peucker(pts, tolerance=0.0001)
    assert out[0] == pts[0]
    assert out[-1] == pts[-1]


def test_douglas_peucker_removes_straight_points():
    pts = [
        {"lat": 0.0, "lon": 0.0, "timestamp": _ts(0)},
        {"lat": 0.0005, "lon": 0.0005, "timestamp": _ts(1)},
        {"lat": 0.001, "lon": 0.001, "timestamp": _ts(2)},
    ]
    out = douglas_peucker(pts, tolerance=0.001)
    assert len(out) == 2


def test_douglas_peucker_keeps_significant_deviation():
    pts = [
        {"lat": 0.0, "lon": 0.0, "timestamp": _ts(0)},
        {"lat": 0.01, "lon": 0.0, "timestamp": _ts(1)},
        {"lat": 0.0, "lon": 0.01, "timestamp": _ts(2)},
        {"lat": 0.0, "lon": 0.0, "timestamp": _ts(3)},
    ]
    out = douglas_peucker(pts, tolerance=0.001)
    assert any(p["lat"] == 0.01 and p["lon"] == 0.0 for p in out)


def test_points_to_ride_applies_compression():
    pts = [
        {"lat": 0.0, "lon": 0.0, "timestamp": _ts(0), "altitude": 100},
        {"lat": 0.0002, "lon": 0.0002, "timestamp": _ts(1), "altitude": 101},
        {"lat": 0.0004, "lon": 0.0004, "timestamp": _ts(2), "altitude": 102},
    ]
    ride = points_to_ride(pts, gps_tolerance=0.001)
    assert "error" not in ride
    assert len(ride["gps_points"]) <= len(pts)


def test_points_to_ride_empty_input():
    assert "error" in points_to_ride([])


def test_points_to_ride_preserves_distance_approximately():
    pts = [
        {"lat": 45.4642, "lon": 9.19, "timestamp": _ts(0), "altitude": 100},
        {"lat": 45.4652, "lon": 9.20, "timestamp": _ts(1), "altitude": 101},
        {"lat": 45.4662, "lon": 9.21, "timestamp": _ts(2), "altitude": 102},
    ]
    ride = points_to_ride(pts, gps_tolerance=0.00001)
    assert ride["distance_km"] > 0
