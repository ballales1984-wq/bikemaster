"""Test analytics."""

import os
from datetime import UTC, datetime

from bike_analyzer.backend.analytics.analytics import (
    analyze_ride,
    calculate_summary,
    create_duration_chart,
    create_elevation_chart,
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
from bike_analyzer.backend.analytics.calories import estimate_calories
from bike_analyzer.backend.analytics.fatigue import calculate_fatigue_score
from bike_analyzer.backend.ingestion.gps_parser import parse_gpx_file
from bike_analyzer.backend.models.models import AthleteProfile, GPSPoint, Ride
from bike_analyzer.backend.processing.processing import process_route


def test_calorie_estimation():

    r = Ride(
        date="2024-06-01",
        distance_km=25.0,
        duration_minutes=60.0,
        avg_speed_kmh=20.0,
        weight_kg=70.0,
    )

    c = estimate_calories(r)

    assert 0 < c < 1000


def test_fatigue_calculation():

    r = Ride(
        date="2024-06-01",
        distance_km=25.0,
        duration_minutes=90.0,
        avg_speed_kmh=22.0,
        weight_kg=70.0,
        heart_rate_avg=150.0,
        elevation_gain_m=200.0,
    )

    f = calculate_fatigue_score(r)

    assert 0 <= f <= 10


def test_fatigue_high_score():

    r = Ride(
        date="2024-06-01",
        distance_km=100.0,
        duration_minutes=240.0,
        avg_speed_kmh=40.0,
        weight_kg=80.0,
        heart_rate_avg=190.0,
        elevation_gain_m=2000.0,
    )

    f = calculate_fatigue_score(r)

    assert f >= 5.0


def test_fatigue_extreme():

    r = Ride(
        date="2024-06-01",
        distance_km=200.0,
        duration_minutes=600.0,
        avg_speed_kmh=50.0,
        weight_kg=90.0,
        heart_rate_avg=210.0,
        elevation_gain_m=4000.0,
    )

    f = calculate_fatigue_score(r)

    assert f >= 7.0


def test_recovery_recommendations():

    from bike_analyzer.backend.analytics.fatigue import get_recovery_recommendation

    assert "Minimal fatigue" in get_recovery_recommendation(1.0)

    assert "Light fatigue" in get_recovery_recommendation(3.0)

    assert "Moderate fatigue" in get_recovery_recommendation(5.0)

    assert "High fatigue" in get_recovery_recommendation(7.0)

    assert "Extreme fatigue" in get_recovery_recommendation(9.0)


def test_estimate_recovery_hours_all_brackets():

    from bike_analyzer.backend.analytics.fatigue import estimate_recovery_hours

    assert estimate_recovery_hours(2.0) == 8.0

    assert estimate_recovery_hours(4.0) == 16.0

    assert estimate_recovery_hours(6.0) == 24.0

    assert estimate_recovery_hours(8.0) == 48.0

    assert estimate_recovery_hours(9.0) == 48.0


def test_calculate_summary():

    rides = [
        Ride(date="2024-06-01", distance_km=20.0, duration_minutes=45.0, avg_speed_kmh=26.7),
        Ride(date="2024-06-02", distance_km=30.0, duration_minutes=70.0, avg_speed_kmh=25.7),
    ]

    s = calculate_summary(rides)

    assert s["total_rides"] == 2 and s["total_km"] == 50.0


def test_empty_summary():

    assert calculate_summary([])["total_rides"] == 0


def test_process_route():

    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC)),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC)),
        GPSPoint(lat=45.02, lon=9.02, timestamp=datetime(2024, 1, 1, 0, 2, tzinfo=UTC)),
    ]

    cleaned, stats = process_route(points)

    assert len(cleaned) == 3

    assert stats.segment_count == 2

    assert stats.total_distance_m > 0


def test_parse_gpx():

    gpx_content = """<?xml version="1.0"?>

<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">

  <trk><trkseg>

    <trkpt lat="45.0" lon="9.0"><ele>100</ele><time>2024-01-01T10:00:00Z</time></trkpt>

    <trkpt lat="45.01" lon="9.01"><ele>110</ele><time>2024-01-01T10:01:00Z</time></trkpt>

  </trkseg></trk>

</gpx>"""

    points = parse_gpx_file(gpx_content)

    assert len(points) == 2

    assert points[0]["lat"] == 45.0

    assert points[0]["altitude"] == 100.0


def test_export_json():

    rides = [
        Ride(
            date="2024-06-01",
            distance_km=25.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            calories=500,
        )
    ]

    path = export_rides_json(rides, "test_rides.json")

    assert os.path.exists(path)

    os.remove(path)


def test_export_csv():

    rides = [
        Ride(
            date="2024-06-01",
            distance_km=25.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            calories=500,
        )
    ]

    path = export_rides_csv(rides, "test_rides.csv")

    assert os.path.exists(path)

    os.remove(path)


def test_text_report():

    r = Ride(
        date="2024-06-01",
        distance_km=25.0,
        duration_minutes=60.0,
        avg_speed_kmh=25.0,
        calories=500,
        heart_rate_avg=150,
        elevation_gain_m=100,
    )

    report = generate_text_report(r)

    assert "BikeMaster Report" in report and "25" in report


def test_analyze_ride():

    r = Ride(
        date="2024-06-01",
        distance_km=25.0,
        duration_minutes=60.0,
        avg_speed_kmh=25.0,
        calories=500,
        heart_rate_avg=150,
        elevation_gain_m=100,
    )

    result = analyze_ride(r)

    assert "fatigue_score" in result


def test_rides_to_json():

    rides = [
        Ride(
            date="2024-06-01",
            distance_km=25.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            calories=500,
        )
    ]

    assert ride_to_json(rides[0]) != ""

    assert rides_to_json(rides) != ""


def test_rides_to_csv():

    rides = [
        Ride(
            date="2024-06-01",
            distance_km=25.0,
            duration_minutes=60.0,
            avg_speed_kmh=25.0,
            calories=500,
        )
    ]

    result = rides_to_csv(rides)

    assert "2024-06-01" in result


def test_benchmark_comparison():

    from bike_analyzer.backend.analytics.benchmark import compare_athlete_to_benchmark

    athlete = AthleteProfile(name="Test", experience_level="Intermediate")

    comp = compare_athlete_to_benchmark(athlete, 100.0, 25.0, 5.0)

    assert "percentile_km" in comp


def test_benchmark_categories():

    from bike_analyzer.backend.analytics.benchmark import (
        generate_benchmark_report,
        get_age_category,
        get_experience_category,
        get_weight_category,
    )

    assert get_age_category(20) == "Under25"

    assert get_age_category(30) == "25-35"

    assert get_weight_category(60) == "Lightweight"

    assert get_weight_category(70) == "Medium"

    assert get_experience_category(5) == "Experienced"

    athlete = AthleteProfile(
        name="Test", experience_level="Amateur", age=30, weight_kg=75, years_active=3
    )

    report = generate_benchmark_report(athlete, [])

    assert "Atleta: Test" in report


def test_ai_coach_fallbacks():

    import os

    os.environ["AI_COACH_MODE"] = "local"
    os.environ.pop("GROQ_API_KEY", None)

    from bike_analyzer.backend.analytics.ai_coach import (
        generate_recovery_advice,
        generate_training_advice,
    )

    athlete = AthleteProfile(name="Test", experience_level="Beginner")

    result = generate_training_advice(athlete, [])

    assert result is not None

    assert generate_recovery_advice(athlete, []) != ""


def test_google_maps_api_key():

    from bike_analyzer.backend.maps.google_maps import get_google_api_key

    key = get_google_api_key()

    assert isinstance(key, (str, type(None)))


def test_chart_function_signatures():

    from inspect import signature

    from bike_analyzer.backend.analytics.analytics import (
        create_speed_chart,
    )

    assert "output_path" in signature(create_elevation_chart).parameters

    assert "output_path" in signature(create_duration_chart).parameters

    assert "rides" in signature(create_duration_chart).parameters

    assert "points" in signature(generate_speed_chart).parameters

    assert "output_path" in signature(create_speed_chart).parameters


def test_generate_speed_chart_no_points():

    result = generate_speed_chart(None)

    assert result == ""


def test_generate_speed_chart_no_speed_values():

    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC)),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC)),
    ]

    result = generate_speed_chart(points)

    assert result == ""


def test_generate_distance_chart_no_points():

    result = generate_distance_chart(None)

    assert result == ""


def test_generate_time_chart_no_points():
    result = generate_time_chart(None)
    assert result == ""


def test_generate_distance_chart_with_points():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC)),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC)),
    ]
    result = generate_distance_chart(points)
    assert result != ""


def test_generate_time_chart_with_points():
    points = [
        GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, 10, 0, tzinfo=UTC)),
        GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 10, 30, tzinfo=UTC)),
    ]
    result = generate_time_chart(points)
    assert result != ""


def test_calculate_summary_no_rides():
    result = calculate_summary([])
    assert result["total_rides"] == 0
    assert result["avg_fatigue"] == 0.0


def test_analyze_ride_no_id():
    r = Ride(date="2024-06-01", distance_km=20.0, duration_minutes=60.0, avg_speed_kmh=20.0)
    result = analyze_ride(r)
    assert result["ride_id"] is None
