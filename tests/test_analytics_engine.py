"""Tests for analytics engine."""

import os
import tempfile

import pytest

from bike_analyzer.backend.analytics.analytics import (
    analyze_ride,
    calculate_summary,
    create_distance_chart,
    create_duration_chart,
    create_elevation_chart,
    create_speed_chart,
    export_rides_csv,
    export_rides_json,
    generate_distance_chart,
    generate_speed_chart,
    generate_text_report,
    generate_time_chart,
    ride_to_json,
    rides_to_csv,
    rides_to_json,
)
from bike_analyzer.backend.models.models import GPSPoint, Ride, Segment
from datetime import UTC, datetime


def _make_ride(**kwargs):
    defaults = dict(
        id=1,
        athlete_id=0,
        date="2024-01-01",
        distance_km=25.0,
        duration_minutes=60.0,
        avg_speed_kmh=25.0,
        weight_kg=70.0,
        calories=500.0,
        heart_rate_avg=140.0,
        elevation_gain_m=150.0,
        gps_points=[],
    )
    defaults.update(kwargs)
    return Ride(**defaults)


def _make_segment(start_pt, end_pt, distance_m=1000.0, duration_s=60.0, avg_speed_km_h=25.0, elevation_gain_m=10.0):
    return Segment(
        start=start_pt,
        end=end_pt,
        distance_m=distance_m,
        duration_s=duration_s,
        avg_speed_km_h=avg_speed_km_h,
        elevation_gain_m=elevation_gain_m,
    )


def test_calculate_summary_empty():
    result = calculate_summary([])
    assert result["total_rides"] == 0
    assert result["total_km"] == 0.0


def test_calculate_summary_multiple():
    rides = [
        _make_ride(distance_km=10.0, avg_speed_kmh=20.0, calories=400.0),
        _make_ride(id=2, distance_km=15.0, avg_speed_kmh=25.0, calories=600.0),
    ]
    result = calculate_summary(rides)
    assert result["total_rides"] == 2
    assert result["total_km"] == 25.0
    assert result["total_calories"] == 1000
    assert result["avg_speed"] == 22.5


def test_analyze_ride():
    ride = _make_ride()
    result = analyze_ride(ride)
    assert result["ride_id"] == 1
    assert result["date"] == "2024-01-01"
    assert "fatigue_score" in result
    assert "recovery_hours" in result
    assert "recovery_recommendation" in result


def test_ride_to_json():
    ride = _make_ride()
    json_str = ride_to_json(ride)
    assert "date" in json_str
    assert "2024-01-01" in json_str


def test_rides_to_json():
    rides = [_make_ride(), _make_ride(id=2)]
    json_str = rides_to_json(rides)
    assert json_str.count("date") >= 2


def test_rides_to_csv_empty():
    result = rides_to_csv([])
    assert result == ""


def test_rides_to_csv_with_rides():
    rides = [_make_ride()]
    result = rides_to_csv(rides)
    assert "date" in result
    assert "distance_km" in result
    assert "2024-01-01" in result


def test_export_rides_json():
    rides = [_make_ride()]
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        path = f.name
    try:
        result = export_rides_json(rides, path)
        assert result == path
        with open(path) as f:
            content = f.read()
        assert "date" in content
    finally:
        os.unlink(path)


def test_export_rides_csv():
    rides = [_make_ride()]
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        path = f.name
    try:
        result = export_rides_csv(rides, path)
        assert result == path
        with open(path) as f:
            content = f.read()
        assert "date" in content
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_generate_text_report():
    ride = _make_ride()
    report = generate_text_report(ride)
    assert "BikeMaster Report" in report
    assert "2024-01-01" in report
    assert "25.0 km" in report


def test_create_speed_chart():
    import unittest.mock as mock

    with mock.patch("bike_analyzer.backend.analytics.analytics.plt") as mock_plt:
        mock_plt.savefig = lambda *a, **k: None
        mock_plt.close = lambda: None
        mock_fig = mock.MagicMock()
        mock_plt.figure.return_value = mock_fig
        pts = [
            GPSPoint(lat=45.0 + i * 0.01, lon=9.0 + i * 0.01, timestamp=datetime(2024, 1, 1, i, tzinfo=UTC), speed=20.0)
            for i in range(3)
        ]
        seg = _make_segment(pts[0], pts[1])
        result = create_speed_chart([seg], "/tmp/test_speed.png")
        assert result == "/tmp/test_speed.png"


def test_create_elevation_chart():
    import unittest.mock as mock

    with mock.patch("bike_analyzer.backend.analytics.analytics.plt") as mock_plt:
        mock_plt.savefig = lambda *a, **k: None
        mock_plt.close = lambda: None
        pts = [
            GPSPoint(lat=45.0 + i * 0.01, lon=9.0 + i * 0.01, timestamp=datetime(2024, 1, 1, i, tzinfo=UTC))
            for i in range(3)
        ]
        seg = _make_segment(pts[0], pts[1], elevation_gain_m=15.0)
        result = create_elevation_chart([seg], "/tmp/test_elev.png")
        assert result == "/tmp/test_elev.png"


def test_create_duration_chart():
    import unittest.mock as mock

    with mock.patch("bike_analyzer.backend.analytics.analytics.plt") as mock_plt:
        mock_plt.savefig = lambda *a, **k: None
        mock_plt.close = lambda: None
        rides = [_make_ride()]
        result = create_duration_chart(rides, "/tmp/test_dur.png")
        assert result == "/tmp/test_dur.png"


def test_create_distance_chart():
    import unittest.mock as mock

    with mock.patch("bike_analyzer.backend.analytics.analytics.plt") as mock_plt:
        mock_plt.savefig = lambda *a, **k: None
        mock_plt.close = lambda: None
        pts = [
            GPSPoint(lat=45.0 + i * 0.01, lon=9.0 + i * 0.01, timestamp=datetime(2024, 1, 1, i, tzinfo=UTC))
            for i in range(3)
        ]
        seg = _make_segment(pts[0], pts[1], distance_m=2000.0)
        result = create_distance_chart([seg], "/tmp/test_dist.png")
        assert result == "/tmp/test_dist.png"


def test_generate_speed_chart_empty():
    result = generate_speed_chart([])
    assert result == ""


def test_generate_speed_chart_no_speeds():
    points = [GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC), speed=None)]
    result = generate_speed_chart(points)
    assert result == ""


def test_generate_distance_chart_empty():
    result = generate_distance_chart([])
    assert result == ""


def test_generate_time_chart_empty():
    result = generate_time_chart([])
    assert result == ""
