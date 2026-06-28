"""Tests for analytics/advanced.py — 14 mathematical models."""

from __future__ import annotations

import math

import pytest

from bike_analyzer.backend.analytics.advanced import (
    ENDURANCE_METRICS_AVAILABLE,
    CLIMB_CATEGORIES,
    POWER_CONSTANTS,
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


def make_ride(**kwargs):
    defaults = dict(
        id=1,
        athlete_id=1,
        date="2024-06-15T10:00:00",
        distance_km=50.0,
        duration_minutes=120.0,
        avg_speed_kmh=25.0,
        weight_kg=70.0,
        calories=800.0,
        heart_rate_avg=150.0,
        elevation_gain_m=500.0,
        gps_points=None,
        external_source=None,
        external_id=None,
        title=None,
        duration_hours=2.0,
    )
    defaults.update(kwargs)
    return Ride(**{k: v for k, v in defaults.items() if k in {f.name for f in Ride.__dataclass_fields__.values()}})


def make_segment(avg_speed_kmh: float, distance_m: float = 1000.0) -> Segment:
    p1 = GPSPoint(lat=0.0, lon=0.0, timestamp="2024-06-15T10:00:00", speed=avg_speed_kmh)
    p2 = GPSPoint(lat=0.01, lon=0.01, timestamp="2024-06-15T10:05:00", speed=avg_speed_kmh)
    return Segment(
        start=p1,
        end=p2,
        distance_m=distance_m,
        duration_s=300.0,
        avg_speed_km_h=avg_speed_kmh,
        elevation_gain_m=0.0,
    )


def make_gps_point(speed: float | None = None, altitude: float | None = None, lat_offset: float = 0.0) -> GPSPoint:
    return GPSPoint(
        lat=lat_offset + (speed or 0) * 0.0001,
        lon=0.0,
        timestamp="2024-06-15T10:00:00",
        altitude=altitude,
        speed=speed,
    )


class TestCalculatePaceConsistency:
    def test_empty_segments(self):
        result = calculate_pace_consistency([])
        assert result["cv_percent"] == 0.0
        assert result["pace_strategy"] == "unknown"
        assert result["negative_split"] is False

    def test_single_segment(self):
        result = calculate_pace_consistency([make_segment(25.0)])
        assert result["cv_percent"] == 0.0
        assert result["pace_strategy"] == "unknown"

    def test_steady_pace(self):
        segments = [make_segment(25.0) for _ in range(10)]
        result = calculate_pace_consistency(segments)
        assert result["pace_strategy"] == "steady"
        assert result["cv_percent"] < 10

    def test_variable_pace(self):
        segments = [make_segment(20.0 + i * 2) for i in range(10)]
        result = calculate_pace_consistency(segments)
        assert result["pace_strategy"] == "variable"
        assert 10 <= result["cv_percent"] < 25

    def test_erratic_pace(self):
        speeds = [10.0, 40.0, 5.0, 45.0, 8.0, 42.0, 12.0, 38.0]
        segments = [make_segment(s) for s in speeds]
        result = calculate_pace_consistency(segments)
        assert result["pace_strategy"] == "erratic"
        assert result["cv_percent"] >= 25

    def test_negative_split(self):
        fast_first = [make_segment(30.0) for _ in range(5)]
        slow_second = [make_segment(20.0) for _ in range(5)]
        result = calculate_pace_consistency(fast_first + slow_second)
        assert result["negative_split"] is False

    def test_positive_split(self):
        slow_first = [make_segment(20.0) for _ in range(5)]
        fast_second = [make_segment(30.0) for _ in range(5)]
        result = calculate_pace_consistency(slow_first + fast_second)
        assert result["negative_split"] is True

    def test_returns_expected_keys(self):
        segments = [make_segment(25.0) for _ in range(5)]
        result = calculate_pace_consistency(segments)
        assert "cv_percent" in result
        assert "min_speed" in result
        assert "max_speed" in result
        assert "pace_strategy" in result
        assert "first_half_avg" in result
        assert "second_half_avg" in result


class TestCalculatePowerEstimate:
    def test_zero_speed(self):
        ride = make_ride(avg_speed_kmh=0, duration_minutes=0)
        result = calculate_power_estimate(ride)
        assert result["power_avg_w"] == 0.0
        assert result["power_per_kg_w"] == 0.0

    def test_flat_ride(self):
        ride = make_ride(avg_speed_kmh=25.0, elevation_gain_m=0, distance_km=30.0, duration_minutes=72.0)
        result = calculate_power_estimate(ride)
        assert result["power_avg_w"] > 0
        assert result["grade_percent"] == 0.0

    def test_hilly_ride(self):
        ride = make_ride(avg_speed_kmh=20.0, elevation_gain_m=1000.0, distance_km=50.0, duration_minutes=150.0, weight_kg=75.0)
        result = calculate_power_estimate(ride)
        assert result["power_avg_w"] > 0
        assert result["grade_percent"] > 0

    def test_custom_cda(self):
        ride = make_ride(avg_speed_kmh=30.0, elevation_gain_m=0, distance_km=40.0, duration_minutes=80.0)
        result_aero = calculate_power_estimate(ride, cda=POWER_CONSTANTS["cd_a_aero"])
        result_road = calculate_power_estimate(ride, cda=POWER_CONSTANTS["cd_a_road"])
        assert result_aero["power_avg_w"] < result_road["power_avg_w"]

    def test_power_per_kg(self):
        ride_light = make_ride(avg_speed_kmh=25.0, weight_kg=60.0, distance_km=30.0, duration_minutes=72.0)
        ride_heavy = make_ride(avg_speed_kmh=25.0, weight_kg=90.0, distance_km=30.0, duration_minutes=72.0)
        r_light = calculate_power_estimate(ride_light)
        r_heavy = calculate_power_estimate(ride_heavy)
        assert r_light["power_per_kg_w"] > r_heavy["power_per_kg_w"]

    def test_force_breakdown_sums(self):
        ride = make_ride(avg_speed_kmh=25.0, elevation_gain_m=100.0, distance_km=30.0, duration_minutes=72.0)
        result = calculate_power_estimate(ride)
        total_cd = result["cd_wind"] + result["cd_rolling"] + result["cd_gravity"]
        assert abs(total_cd - 100.0) < 5.0


class TestClassifyClimb:
    @pytest.mark.parametrize("length,gradient,expected", [
        (0.2, 10.0, "none"),
        (0.5, 1.0, "none"),
        (1.0, 3.0, "4"),
        (2.0, 6.0, "3"),
        (3.0, 9.0, "2"),
        (5.0, 12.0, "1"),
        (10.0, 15.0, "HC"),
    ])
    def test_classify(self, length, gradient, expected):
        result = classify_climb(length, gradient)
        assert result["category"] == expected

    def test_hc_has_highest_points(self):
        result = classify_climb(10.0, 15.0)
        assert result["points"] == 5

    def test_none_has_zero_score(self):
        result = classify_climb(0.1, 1.0)
        assert result["difficulty_score"] == 0
        assert result["points"] == 0


class TestEstimateVo2max:
    def test_base_calculation(self):
        result = estimate_vo2max(avg_speed_kmh=25.0, avg_gradient_percent=0.0, weight_kg=70.0, age=35)
        assert 30.0 <= result["vo2_max_ml_kg_min"] <= 75.0
        assert "fitness_level" in result

    def test_older_rider_lower_vo2(self):
        young = estimate_vo2max(avg_speed_kmh=25.0, avg_gradient_percent=0.0, weight_kg=70.0, age=25)
        old = estimate_vo2max(avg_speed_kmh=25.0, avg_gradient_percent=0.0, weight_kg=70.0, age=55)
        assert old["vo2_max_ml_kg_min"] < young["vo2_max_ml_kg_min"]

    def test_fitness_levels(self):
        low = estimate_vo2max(avg_speed_kmh=15.0, avg_gradient_percent=0.0, weight_kg=70.0, age=35)
        high = estimate_vo2max(avg_speed_kmh=35.0, avg_gradient_percent=0.0, weight_kg=70.0, age=35)
        assert low["fitness_level"] != high["fitness_level"]
        assert high["vo2_max_ml_kg_min"] > low["vo2_max_ml_kg_min"]

    def test_clamped_range(self):
        result = estimate_vo2max(avg_speed_kmh=50.0, avg_gradient_percent=15.0, weight_kg=50.0, age=20)
        assert 30.0 <= result["vo2_max_ml_kg_min"] <= 75.0


class TestClassifyRideDifficulty:
    def test_zero_distance(self):
        ride = make_ride(distance_km=0)
        result = classify_ride_difficulty(ride)
        assert result["score"] == 0

    def test_easy_ride(self):
        ride = make_ride(distance_km=10.0, duration_minutes=30.0, avg_speed_kmh=20.0,
                         elevation_gain_m=50.0, heart_rate_avg=110.0)
        result = classify_ride_difficulty(ride)
        assert result["level"] in ("Easy", "Moderate")

    def test_extreme_ride(self):
        ride = make_ride(distance_km=200.0, duration_minutes=600.0, avg_speed_kmh=35.0,
                         elevation_gain_m=5000.0, heart_rate_avg=175.0)
        result = classify_ride_difficulty(ride)
        assert result["level"] == "Extreme"

    def test_returns_factors(self):
        ride = make_ride(distance_km=50.0)
        result = classify_ride_difficulty(ride)
        assert "factors" in result
        assert "grade" in result["factors"]
        assert "distance" in result["factors"]

    def test_score_bounded(self):
        ride = make_ride(distance_km=150.0, duration_minutes=300.0, avg_speed_kmh=40.0,
                         elevation_gain_m=3000.0, heart_rate_avg=180.0)
        result = classify_ride_difficulty(ride)
        assert 0 <= result["score"] <= 10


class TestAnalyzeElevationProfile:
    def test_empty_points(self):
        result = analyze_elevation_profile([])
        assert result["hardship_index"] == 0.0

    def test_single_point(self):
        result = analyze_elevation_profile([make_gps_point(altitude=100.0)])
        assert result["hardship_index"] == 0.0

    def test_flat_profile(self):
        points = [make_gps_point(altitude=100.0 + i * 0.3, lat_offset=i * 0.0001) for i in range(20)]
        result = analyze_elevation_profile(points)
        assert result["grade_distribution"]["flat"] > 50

    def test_steep_climb(self):
        points = [make_gps_point(altitude=100.0 + i * 30.0, lat_offset=i * 0.0001) for i in range(20)]
        result = analyze_elevation_profile(points)
        assert result["grade_distribution"].get("steep", 0) > 0 or result["grade_distribution"].get("extreme", 0) > 0

    def test_hardship_index(self):
        points = [make_gps_point(altitude=100.0 + i * 3.0, lat_offset=i * 0.0001) for i in range(20)]
        result = analyze_elevation_profile(points)
        assert result["hardship_index"] >= 0


class TestAnalyzeSpeedProfile:
    def test_empty_points(self):
        result = analyze_speed_profile([])
        assert result["acceleration_events"] == 0

    def test_single_point(self):
        result = analyze_speed_profile([make_gps_point(speed=25.0)])
        assert result["acceleration_events"] == 0

    def test_detects_accelerations(self):
        points = [make_gps_point(speed=20.0 + i * 3.0) for i in range(10)]
        result = analyze_speed_profile(points)
        assert result["acceleration_events"] > 0

    def test_detects_decelerations(self):
        points = [make_gps_point(speed=30.0 - i * 2) for i in range(10)]
        result = analyze_speed_profile(points)
        assert result["deceleration_events"] > 0

    def test_coasting_detection(self):
        points = [make_gps_point(speed=25.0) for _ in range(10)]
        result = analyze_speed_profile(points)
        assert result["coasting_time_pct"] > 0


class TestCalculateProgressTrend:
    def test_insufficient_data(self):
        result = calculate_progress_trend([])
        assert result["trend"] == "insufficient_data"
        assert result["slope"] == 0.0

    def test_single_ride(self):
        ride = make_ride(avg_speed_kmh=25.0)
        result = calculate_progress_trend([ride])
        assert result["trend"] == "insufficient_data"

    def test_improving_trend(self):
        rides = [make_ride(date=f"2024-0{i}-15T10:00:00", avg_speed_kmh=20.0 + i * 2, distance_km=30.0 + i * 5, duration_minutes=80 - i * 5) for i in range(1, 7)]
        result = calculate_progress_trend(rides)
        assert result["trend"] == "improving"
        assert result["slope"] > 0

    def test_declining_trend(self):
        rides = [make_ride(date=f"2024-0{i}-15T10:00:00", avg_speed_kmh=30.0 - i * 2, distance_km=40.0 - i * 3, duration_minutes=70 + i * 3) for i in range(1, 7)]
        result = calculate_progress_trend(rides)
        assert result["trend"] == "declining"
        assert result["slope"] < 0

    def test_stable_trend(self):
        rides = [make_ride(date=f"2024-0{i}-15T10:00:00", avg_speed_kmh=25.0, distance_km=35.0, duration_minutes=84.0) for i in range(1, 7)]
        result = calculate_progress_trend(rides)
        assert result["trend"] == "stable"

    def test_returns_expected_keys(self):
        rides = [make_ride(date=f"2024-0{i}-15T10:00:00", avg_speed_kmh=20.0 + i, distance_km=30.0 + i * 2, duration_minutes=80 - i * 2) for i in range(1, 7)]
        result = calculate_progress_trend(rides)
        assert "r_squared" in result
        assert "improvement_pct" in result
        assert "data_points" in result


class TestCalculateTrainingStressBalance:
    def test_empty_rides(self):
        result = calculate_training_stress_balance([])
        assert result["form"] == "no_data"
        assert result["atl"] == 0.0

    def test_with_rides(self):
        rides = [
            make_ride(date="2024-06-01T10:00:00", calories=800.0),
            make_ride(date="2024-06-02T10:00:00", calories=600.0),
            make_ride(date="2024-06-03T10:00:00", calories=1000.0),
        ]
        result = calculate_training_stress_balance(rides)
        assert "atl" in result
        assert "ctl" in result
        assert "tsb" in result
        assert "form" in result
        assert "daily_load" in result

    def test_form_classification(self):
        rides = [make_ride(date="2024-06-15T10:00:00", calories=2000.0, duration_minutes=300.0)]
        result = calculate_training_stress_balance(rides)
        assert result["form"] in ("fresh", "optimal", "fatigued", "overreached", "burnout_risk", "no_data")

    def test_daily_load_max_14(self):
        rides = [make_ride(date=f"2024-06-{i:02d}T10:00:00", calories=800.0) for i in range(1, 21)]
        result = calculate_training_stress_balance(rides)
        assert len(result["daily_load"]) <= 14


class TestEstimateIdealWeight:
    def test_positive_ftp(self):
        result = estimate_ideal_weight(ftp=300.0, height_cm=180.0)
        assert 50.0 < result < 100.0

    def test_zero_ftp(self):
        assert estimate_ideal_weight(ftp=0, height_cm=180.0) == 70.0

    def test_zero_height(self):
        assert estimate_ideal_weight(ftp=300.0, height_cm=0) == 70.0

    def test_high_ftp_heavier(self):
        low_ftp = estimate_ideal_weight(ftp=200.0, height_cm=175.0)
        high_ftp = estimate_ideal_weight(ftp=350.0, height_cm=175.0)
        assert high_ftp > low_ftp


class TestCalculateGarminPowerFactor:
    def test_zero_speed(self):
        ride = make_ride(avg_speed_kmh=0, duration_minutes=0)
        result = calculate_garmin_power_factor(ride)
        assert result["pf"] == 0.0
        assert result["np_w"] == 0.0

    def test_returns_keys(self):
        ride = make_ride(avg_speed_kmh=25.0, elevation_gain_m=100.0, distance_km=30.0, duration_minutes=72.0)
        result = calculate_garmin_power_factor(ride)
        assert "pf" in result
        assert "np_w" in result
        assert "if" in result
        assert "tss_est" in result

    def test_higher_speed_higher_power(self):
        flat_kwargs = dict(elevation_gain_m=0, distance_km=40.0, duration_minutes=96.0)
        slow = make_ride(avg_speed_kmh=20.0, **flat_kwargs)
        fast = make_ride(avg_speed_kmh=35.0, **flat_kwargs)
        assert calculate_garmin_power_factor(fast)["np_w"] > calculate_garmin_power_factor(slow)["np_w"]


class TestCalculateHeartRateZones:
    def test_default_zones(self):
        zones = calculate_heart_rate_zones()
        assert len(zones) == 5
        assert "Z1 (Recovery)" in zones
        assert "Z5 (VO2max)" in zones

    def test_zones_ordered(self):
        zones = calculate_heart_rate_zones(max_hr=180)
        keys = list(zones.keys())
        assert zones[keys[0]]["min"] < zones[keys[-1]]["min"]

    def test_in_zone_flag(self):
        zones = calculate_heart_rate_zones(max_hr=180, current_avg_hr=160.0)
        in_zone = [z for z in zones.values() if z.get("in_zone")]
        assert len(in_zone) == 1

    def test_no_current_hr(self):
        zones = calculate_heart_rate_zones(max_hr=180, current_avg_hr=None)
        assert all("in_zone" not in z for z in zones.values())


class TestCalculateRideRecommendationScore:
    def test_recovery_ride(self):
        ride = make_ride(distance_km=3.0, avg_speed_kmh=10.0, elevation_gain_m=10.0, duration_minutes=18.0)
        result = calculate_ride_recommendation_score(ride)
        assert result["label"] == "Recovery Ride"

    def test_race_effort(self):
        ride = make_ride(distance_km=100.0, avg_speed_kmh=35.0, elevation_gain_m=2000.0)
        result = calculate_ride_recommendation_score(ride)
        assert result["label"] == "Race / Peak Effort"

    def test_score_components(self):
        ride = make_ride(distance_km=50.0, avg_speed_kmh=25.0, elevation_gain_m=500.0)
        result = calculate_ride_recommendation_score(ride)
        assert "overall_score" in result
        assert "volume_score" in result
        assert "intensity_score" in result
        assert "elevation_score" in result

    def test_score_range(self):
        ride = make_ride(distance_km=50.0, avg_speed_kmh=25.0, elevation_gain_m=500.0)
        result = calculate_ride_recommendation_score(ride)
        assert 0 <= result["overall_score"] <= 10


class TestDetectSpeedSurges:
    def test_empty_points(self):
        result = detect_speed_surges([])
        assert result == []

    def test_single_point(self):
        result = detect_speed_surges([make_gps_point(speed=25.0)])
        assert result == []

    def test_detects_surge(self):
        points = [make_gps_point(speed=s) for s in [20.0, 21.0, 28.0, 29.0, 27.0]]
        result = detect_speed_surges(points, threshold_kmh=5.0)
        assert len(result) > 0
        assert result[0]["speed_jump_kmh"] >= 5.0

    def test_no_surge_smooth(self):
        points = [make_gps_point(speed=25.0 + i * 0.5) for i in range(10)]
        result = detect_speed_surges(points, threshold_kmh=8.0)
        assert result == []

    def test_below_min_speed(self):
        points = [make_gps_point(speed=s) for s in [5.0, 7.0, 14.0, 13.0, 15.0]]
        result = detect_speed_surges(points, threshold_kmh=5.0, min_speed_kmh=20.0)
        assert result == []

    def test_none_speeds_ignored(self):
        points = [make_gps_point(speed=None), make_gps_point(speed=25.0)]
        result = detect_speed_surges(points)
        assert isinstance(result, list)


class TestComputeCtlAtlTsbExternal:
    def test_returns_dict(self):
        rides = [make_ride(date="2024-06-15T10:00:00", calories=800.0)]
        result = __import__("bike_analyzer.backend.analytics.advanced", fromlist=["compute_ctl_atl_tsb_external"]).compute_ctl_atl_tsb_external(rides)
        assert "ctl" in result
        assert "atl" in result
        assert "tsb" in result


class TestPowerConstants:
    def test_constants_exist(self):
        assert "g" in POWER_CONSTANTS
        assert "air_density" in POWER_CONSTANTS
        assert "cd_a_road" in POWER_CONSTANTS

    def test_physical_plausibility(self):
        assert POWER_CONSTANTS["g"] == pytest.approx(9.81, rel=1e-3)
        assert POWER_CONSTANTS["air_density"] == pytest.approx(1.225, rel=1e-3)


class TestClimbCategories:
    def test_categories_ordered(self):
        thresholds = [cat[1] for cat in CLIMB_CATEGORIES]
        assert thresholds == sorted(thresholds, reverse=True)

    def test_all_categories(self):
        cats = [cat[0] for cat in CLIMB_CATEGORIES]
        assert cats == ["HC", "1", "2", "3", "4"]
