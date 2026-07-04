"""Tests for analytics module coverage gaps."""

from datetime import UTC, datetime

from bike_analyzer.backend.analytics.analytics import (
    analyze_ride,
    calculate_summary,
    export_rides_csv,
    export_rides_json,
    generate_text_report,
    ride_to_json,
    rides_to_csv,
    rides_to_json,
)
from bike_analyzer.core.models import GPSPoint, Ride


def _make_ride(
    date="2024-06-15",
    distance_km=25.0,
    duration_minutes=60,
    avg_speed_kmh=25.0,
    calories=600,
    heart_rate_avg=150.0,
    elevation_gain_m=200.0,
):
    ts = datetime(2024, 6, 15, 10, 0, 0, tzinfo=UTC)
    points = [
        GPSPoint(lat=45.0, lon=9.0, altitude=100.0, speed=10.0, timestamp=ts),
        GPSPoint(lat=45.01, lon=9.01, altitude=105.0, speed=12.0, timestamp=ts),
    ]
    return Ride(
        id=1,
        athlete_id=1,
        date=date,
        distance_km=distance_km,
        duration_minutes=duration_minutes,
        avg_speed_kmh=avg_speed_kmh,
        calories=calories,
        heart_rate_avg=heart_rate_avg,
        elevation_gain_m=elevation_gain_m,
        gps_points=points,
    )


class TestCalculateSummary:
    def test_empty_rides(self):
        result = calculate_summary([])
        assert result["total_rides"] == 0
        assert result["total_km"] == 0.0

    def test_single_ride(self):
        rides = [_make_ride()]
        result = calculate_summary(rides)
        assert result["total_rides"] == 1
        assert result["total_km"] == 25.0
        assert result["total_calories"] == 600.0

    def test_multiple_rides(self):
        rides = [_make_ride(), _make_ride(date="2024-06-16", distance_km=30.0, calories=700)]
        result = calculate_summary(rides)
        assert result["total_rides"] == 2
        assert result["total_km"] == 55.0

    def test_avg_fatigue_calculation(self):
        rides = [_make_ride(), _make_ride(date="2024-06-16")]
        result = calculate_summary(rides)
        assert "avg_fatigue" in result


class TestAnalyzeRide:
    def test_analyze_ride_basic(self):
        ride = _make_ride()
        result = analyze_ride(ride)
        assert result["ride_id"] == 1
        assert result["date"] == "2024-06-15"
        assert result["distance_km"] == 25.0
        assert "fatigue_score" in result
        assert "recovery_hours" in result
        assert "recovery_recommendation" in result

    def test_analyze_ride_calories(self):
        ride = _make_ride(calories=800)
        result = analyze_ride(ride)
        assert result["calories"] == 800


class TestSerialization:
    def test_ride_to_json(self):
        ride = _make_ride()
        json_str = ride_to_json(ride)
        assert "2024-06-15" in json_str
        assert "25.0" in json_str

    def test_rides_to_json(self):
        rides = [_make_ride(), _make_ride(date="2024-06-16")]
        json_str = rides_to_json(rides)
        assert "2024-06-15" in json_str
        assert "2024-06-16" in json_str

    def test_rides_to_csv(self):
        rides = [_make_ride()]
        csv_str = rides_to_csv(rides)
        assert "date" in csv_str
        assert "distance_km" in csv_str
        assert "2024-06-15" in csv_str

    def test_rides_to_csv_empty(self):
        result = rides_to_csv([])
        assert result == ""


class TestExportFunctions:
    def test_export_rides_json(self, tmp_path):
        rides = [_make_ride(date="2024-06-16")]
        out = str(tmp_path / "rides.json")
        result = export_rides_json(rides, out)
        assert result == out
        import json

        with open(out) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["date"] == "2024-06-16"

    def test_export_rides_csv(self, tmp_path):
        rides = [_make_ride()]
        out = str(tmp_path / "rides.csv")
        result = export_rides_csv(rides, out)
        assert result == out
        with open(out) as f:
            content = f.read()
        assert "date" in content
        assert "2024-06-15" in content


class TestTextReport:
    def test_generate_text_report(self):
        ride = _make_ride()
        report = generate_text_report(ride)
        assert "BikeMaster Report" in report
        assert "2024-06-15" in report
        assert "25.0 km" in report
        assert "Fatigue Score" in report
