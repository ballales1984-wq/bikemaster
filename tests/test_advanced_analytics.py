"""Tests for advanced analytics models."""

from datetime import UTC, datetime

from bike_analyzer.backend.analytics.advanced import (
    analyze_elevation_profile,
    calculate_garmin_power_factor,
    calculate_heart_rate_zones,
    calculate_pace_consistency,
    calculate_power_estimate,
    calculate_progress_trend,
    calculate_ride_recommendation_score,
    calculate_training_stress_balance,
    classify_climb,
    classify_ride_difficulty,
    detect_speed_surges,
    estimate_ideal_weight,
    estimate_vo2max,
)
from bike_analyzer.backend.models.models import GPSPoint, Ride, Segment


def test_power_estimate_basic():
    ride = Ride(
        date="2024-06-01",
        distance_km=30,
        duration_minutes=60,
        avg_speed_kmh=30,
        weight_kg=70,
        elevation_gain_m=200,
    )
    result = calculate_power_estimate(ride)
    assert result["power_avg_w"] > 0
    assert result["power_per_kg_w"] > 0


def test_power_estimate_invalid_ride():
    ride = Ride(date="2024-06-01", distance_km=0, duration_minutes=0, avg_speed_kmh=0, weight_kg=70)
    result = calculate_power_estimate(ride)
    assert result["power_avg_w"] == 0.0


def test_climb_classification():
    r = classify_climb(segment_length_km=0.2, avg_gradient_percent=5)
    assert r["category"] == "none"
    r = classify_climb(segment_length_km=2.0, avg_gradient_percent=8)
    assert r["category"] == "3"
    r = classify_climb(segment_length_km=3.0, avg_gradient_percent=7)
    assert r["category"] == "3"
    r = classify_climb(segment_length_km=3.0, avg_gradient_percent=9)
    assert r["category"] == "2"
    r = classify_climb(segment_length_km=2.0, avg_gradient_percent=13)
    assert r["category"] == "1"
    r = classify_climb(segment_length_km=5.0, avg_gradient_percent=18)
    assert r["category"] == "HC"
    r = classify_climb(segment_length_km=5.0, avg_gradient_percent=18)
    assert r["category"] == "HC"


def test_vo2max_estimation():
    result = estimate_vo2max(avg_speed_kmh=25, avg_gradient_percent=2, weight_kg=70, age=30)
    assert "vo2_max_ml_kg_min" in result
    assert result["fitness_level"] in ["Below Average", "Average", "Good", "Very Good", "Excellent"]
    assert result["vo2_max_ml_kg_min"] >= 30
    assert result["vo2_max_ml_kg_min"] <= 75


def test_ride_difficulty():
    easy_ride = Ride(
        date="2024-06-01",
        distance_km=20,
        duration_minutes=60,
        avg_speed_kmh=20,
        heart_rate_avg=130,
        elevation_gain_m=50,
    )
    result = classify_ride_difficulty(easy_ride)
    assert result["level"] in ["Easy", "Moderate", "Challenging", "Hard", "Extreme"]
    assert "score" in result


def test_pace_consistency():
    p1 = GPSPoint(46.1, 11.1, datetime.now(UTC), speed=25.0)
    p2 = GPSPoint(46.1, 11.2, datetime.now(UTC), speed=25.5)
    p3 = GPSPoint(46.1, 11.3, datetime.now(UTC), speed=24.8)
    segments = [
        Segment(start=p1, end=p2, distance_m=1000, duration_s=144, avg_speed_km_h=25.0),
        Segment(start=p2, end=p3, distance_m=1000, duration_s=144, avg_speed_km_h=25.5),
    ]
    result = calculate_pace_consistency(segments)
    assert "pace_strategy" in result
    assert "cv_percent" in result


def test_progress_trend_improving():
    rides = [
        Ride(date="2024-01-01", distance_km=20, avg_speed_kmh=22),
        Ride(date="2024-02-01", distance_km=25, avg_speed_kmh=23),
        Ride(date="2024-03-01", distance_km=30, avg_speed_kmh=24),
        Ride(date="2024-04-01", distance_km=35, avg_speed_kmh=25),
    ]
    result = calculate_progress_trend(rides)
    assert result["trend"] == "improving"
    assert result["r_squared"] > 0


def test_progress_trend_insufficient():
    result = calculate_progress_trend([])
    assert result["trend"] == "insufficient_data"
    result = calculate_progress_trend([Ride(date="2024-01-01", avg_speed_kmh=25)])
    assert result["trend"] == "insufficient_data"


def test_training_stress_balance():
    rides = [
        Ride(date="2024-01-01", distance_km=30, duration_minutes=90, avg_speed_kmh=28),
        Ride(date="2024-01-03", distance_km=25, duration_minutes=60, avg_speed_kmh=25),
        Ride(date="2024-01-05", distance_km=40, duration_minutes=120, avg_speed_kmh=30),
    ]
    result = calculate_training_stress_balance(rides)
    assert "atl" in result
    assert "ctl" in result
    assert "tsb" in result
    assert "form" in result


def test_elevation_profile():
    points = [
        GPSPoint(46.1, 11.1, datetime.now(UTC), altitude=100),
        GPSPoint(46.1, 11.2, datetime.now(UTC), altitude=150),
        GPSPoint(46.1, 11.3, datetime.now(UTC), altitude=120),
        GPSPoint(46.1, 11.4, datetime.now(UTC), altitude=200),
    ]
    result = analyze_elevation_profile(points)
    assert "grade_distribution" in result
    assert "hardship_index" in result


def test_speed_surges():
    points = [
        GPSPoint(46.1, 11.1, datetime.now(UTC), speed=20),
        GPSPoint(46.1, 11.2, datetime.now(UTC), speed=22),
        GPSPoint(46.1, 11.3, datetime.now(UTC), speed=28),
        GPSPoint(46.1, 11.4, datetime.now(UTC), speed=16),
    ]
    result = detect_speed_surges(points)
    assert isinstance(result, list)


def test_heart_rate_zones():
    zones = calculate_heart_rate_zones(max_hr=180, current_avg_hr=155)
    assert "Z1 (Recovery)" in zones
    assert "Z5 (VO2max)" in zones


def test_ride_recommendation_score():
    ride = Ride(
        date="2024-06-01",
        distance_km=50,
        duration_minutes=150,
        avg_speed_kmh=30,
        elevation_gain_m=600,
    )
    result = calculate_ride_recommendation_score(ride)
    assert "overall_score" in result
    assert "label" in result


def test_garmin_power_factor():
    ride = Ride(
        date="2024-06-01", distance_km=30, duration_minutes=60, avg_speed_kmh=30, weight_kg=70
    )
    result = calculate_garmin_power_factor(ride)
    assert "pf" in result
    assert "np_w" in result


def test_estimate_ideal_weight():
    assert estimate_ideal_weight(ftp=0, height_cm=175) == 70.0
    assert estimate_ideal_weight(ftp=350, height_cm=175) > 0
    assert estimate_ideal_weight(ftp=250, height_cm=175) > 0
