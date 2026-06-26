"""Tests for advanced analytics models."""

from datetime import UTC, datetime

from bike_analyzer.backend.analytics.advanced import (
    analyze_elevation_profile,
    analyze_speed_profile,
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


def test_pace_consistency_empty_segments():
    result = calculate_pace_consistency([])
    assert result["pace_strategy"] == "unknown"
    assert result["cv_percent"] == 0.0


def test_pace_consistency_zero_speeds():
    s = Segment(start=GPSPoint(46.0, 11.0, datetime.now(UTC)), end=GPSPoint(46.1, 11.1, datetime.now(UTC)), distance_m=1000, duration_s=60, avg_speed_km_h=0)
    result = calculate_pace_consistency([s])
    assert result["pace_strategy"] == "unknown"


def test_pace_consistency_negative_split():
    p1 = GPSPoint(46.1, 11.1, datetime.now(UTC), speed=20.0)
    p2 = GPSPoint(46.1, 11.2, datetime.now(UTC), speed=22.0)
    p3 = GPSPoint(46.1, 11.3, datetime.now(UTC), speed=25.0)
    p4 = GPSPoint(46.1, 11.4, datetime.now(UTC), speed=28.0)
    segments = [
        Segment(start=p1, end=p2, distance_m=1000, duration_s=144, avg_speed_km_h=20.0),
        Segment(start=p2, end=p3, distance_m=1000, duration_s=144, avg_speed_km_h=22.0),
        Segment(start=p3, end=p4, distance_m=1000, duration_s=144, avg_speed_km_h=25.0),
    ]
    result = calculate_pace_consistency(segments)
    assert result["negative_split"] is True


def test_progress_trend_declining():
    rides = [
        Ride(date="2024-01-01", distance_km=20, avg_speed_kmh=30),
        Ride(date="2024-02-01", distance_km=25, avg_speed_kmh=28),
        Ride(date="2024-03-01", distance_km=30, avg_speed_kmh=26),
    ]
    result = calculate_progress_trend(rides)
    assert result["trend"] == "declining"


def test_progress_trend_stable():
    rides = [
        Ride(date="2024-01-01", avg_speed_kmh=25),
        Ride(date="2024-02-01", avg_speed_kmh=25),
        Ride(date="2024-03-01", avg_speed_kmh=25),
    ]
    result = calculate_progress_trend(rides)
    assert result["trend"] == "stable"


def test_elevation_profile_missing_altitude():
    points = [
        GPSPoint(46.1, 11.1, datetime.now(UTC)),
        GPSPoint(46.1, 11.2, datetime.now(UTC), altitude=150),
    ]
    result = analyze_elevation_profile(points)
    assert result["hardship_index"] == 0.0


def test_speed_profile_no_speeds():
    points = [
        GPSPoint(46.1, 11.1, datetime.now(UTC)),
        GPSPoint(46.1, 11.2, datetime.now(UTC)),
    ]
    result = analyze_speed_profile(points)
    assert result["acceleration_events"] == 0


def test_speed_surges_below_threshold():
    points = [
        GPSPoint(46.1, 11.1, datetime.now(UTC), speed=20),
        GPSPoint(46.1, 11.2, datetime.now(UTC), speed=21),
    ]
    result = detect_speed_surges(points, threshold_kmh=5.0)
    assert result == []


def test_training_stress_balance_empty():
    result = calculate_training_stress_balance([])
    assert result["form"] == "no_data"


def test_heart_rate_zones_in_zone():
    zones = calculate_heart_rate_zones(max_hr=180, lthr=170, current_avg_hr=160)
    assert zones["Z4 (Threshold)"]["in_zone"] is True


def test_ideal_weight_various_ftp():
    assert estimate_ideal_weight(ftp=200, height_cm=175) > 0
    assert estimate_ideal_weight(ftp=500, height_cm=180) > 0


def test_compute_ctl_atl_tsb_external():
    rides = [Ride(date="2024-01-01", distance_km=30, duration_minutes=60, avg_speed_kmh=25)]
    result = calculate_training_stress_balance(rides)
    assert result["atl"] >= 0
    assert result["ctl"] >= 0


def test_pace_consistency_erratic():
    p1 = GPSPoint(46.1, 11.1, datetime.now(UTC), speed=10.0)
    p2 = GPSPoint(46.1, 11.2, datetime.now(UTC), speed=30.0)
    p3 = GPSPoint(46.1, 11.3, datetime.now(UTC), speed=15.0)
    p4 = GPSPoint(46.1, 11.4, datetime.now(UTC), speed=35.0)
    p5 = GPSPoint(46.1, 11.5, datetime.now(UTC), speed=12.0)
    p6 = GPSPoint(46.1, 11.6, datetime.now(UTC), speed=38.0)
    segments = [
        Segment(start=p1, end=p2, distance_m=1000, duration_s=60, avg_speed_km_h=10.0),
        Segment(start=p2, end=p3, distance_m=1000, duration_s=80, avg_speed_km_h=30.0),
        Segment(start=p3, end=p4, distance_m=1000, duration_s=60, avg_speed_km_h=15.0),
        Segment(start=p4, end=p5, distance_m=1000, duration_s=120, avg_speed_km_h=35.0),
        Segment(start=p5, end=p6, distance_m=1000, duration_s=60, avg_speed_km_h=12.0),
    ]
    result = calculate_pace_consistency(segments)
    assert result["pace_strategy"] == "erratic"


def test_ride_difficulty_unknown():
    ride = Ride(date="2024-06-01", distance_km=0)
    result = classify_ride_difficulty(ride)
    assert result["level"] == "unknown"


def test_ride_difficulty_challenging():
    ride = Ride(date="2024-06-01", distance_km=80, duration_minutes=180, avg_speed_kmh=28, heart_rate_avg=150, elevation_gain_m=1500)
    result = classify_ride_difficulty(ride)
    assert result["score"] > 0
    assert result["level"] in ["Easy", "Moderate", "Challenging", "Hard", "Extreme"]


def test_ride_difficulty_extreme():
    ride = Ride(date="2024-06-01", distance_km=200, duration_minutes=600, avg_speed_kmh=40, heart_rate_avg=180, elevation_gain_m=4000)
    result = classify_ride_difficulty(ride)
    assert result["level"] == "Extreme"


def test_elevation_profile_single_point():
    points = [GPSPoint(46.1, 11.1, datetime.now(UTC), altitude=100)]
    result = analyze_elevation_profile(points)
    assert result["hardship_index"] == 0.0


def test_speed_profile_with_data():
    points = [
        GPSPoint(46.1, 11.1, datetime.now(UTC), speed=25),
        GPSPoint(46.1, 11.2, datetime.now(UTC), speed=27),
        GPSPoint(46.1, 11.3, datetime.now(UTC), speed=24),
    ]
    result = analyze_speed_profile(points)
    assert result["acceleration_events"] >= 0
    assert result["speed_variance"] >= 0


def test_ride_recommendation_all_labels():
    for label, expected in [
        ("Recovery Ride", 30),
        ("Tempo Ride", 60),
        ("Hard Training", 80),
        ("Race / Peak Effort", 100),
    ]:
        ride = Ride(date="2024-06-01", distance_km=expected, avg_speed_kmh=25, elevation_gain_m=expected * 10)
        result = calculate_ride_recommendation_score(ride)
        assert result["label"] in ["Recovery Ride", "Tempo Ride", "Hard Training", "Race / Peak Effort"]


def test_garmin_power_factor_zero_speed():
    ride = Ride(date="2024-06-01", distance_km=30, duration_minutes=60, avg_speed_kmh=0, weight_kg=70)
    result = calculate_garmin_power_factor(ride)
    assert result["pf"] == 0.0


def test_vo2max_all_levels():
    for speed, expected_level in [(15, "Below Average"), (25, "Average"), (35, "Good")]:
        result = estimate_vo2max(avg_speed_kmh=speed, avg_gradient_percent=0, weight_kg=70, age=30)
        assert result["fitness_level"] in ["Below Average", "Average", "Good", "Very Good", "Excellent"]


def test_ideal_weight_boundary():
    assert estimate_ideal_weight(ftp=50, height_cm=0) == 70.0
    assert estimate_ideal_weight(ftp=0, height_cm=0) == 70.0


def test_power_estimate_explicit_weight():
    ride = Ride(date="2024-06-01", distance_km=30, duration_minutes=60, avg_speed_kmh=30, weight_kg=70, elevation_gain_m=200)
    result = calculate_power_estimate(ride, rider_weight_kg=65)
    assert result["power_avg_w"] > 0


def test_power_estimate_gravel():
    ride = Ride(date="2024-06-01", distance_km=30, duration_minutes=60, avg_speed_kmh=25, weight_kg=70, elevation_gain_m=200)
    result = calculate_power_estimate(ride, crr=0.006)
    assert result["power_avg_w"] > 0


def test_classify_climb_edge_cases():
    r = classify_climb(segment_length_km=0.3, avg_gradient_percent=1)
    assert r["category"] == "none"
    r = classify_climb(segment_length_km=1.0, avg_gradient_percent=10)
    assert r["category"] == "2"


def test_vo2max_boundary():
    result = estimate_vo2max(avg_speed_kmh=10, avg_gradient_percent=10, weight_kg=70, age=50)
    assert result["vo2_max_ml_kg_min"] >= 30
    assert result["fitness_level"] == "Below Average"


def test_progress_trend_none_metric():
    rides = [
        Ride(date="2024-01-01", avg_speed_kmh=None),
        Ride(date="2024-02-01", avg_speed_kmh=25),
    ]
    result = calculate_progress_trend(rides)
    assert result["trend"] == "insufficient_data"
