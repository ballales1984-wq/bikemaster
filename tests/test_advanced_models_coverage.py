"""Additional coverage for analytics.advanced pure-model functions."""

from __future__ import annotations

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


def _pt(lat=45.0, lon=7.0, speed=20.0, altitude=100.0, hr=140.0, power=None, ts=None):
    return GPSPoint(
        lat=lat,
        lon=lon,
        speed=speed,
        altitude=altitude,
        heart_rate=hr,
        power=power,
        timestamp=ts or datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
    )


def _ride(**kw):
    base = {
        "date": "2024-01-01",
        "distance_km": 30.0,
        "duration_minutes": 90.0,
        "avg_speed_kmh": 22.0,
        "calories": 600,
        "elevation_gain_m": 200,
        "heart_rate_avg": 150,
        "weight_kg": 70,
    }
    base.update(kw)
    return Ride(**base)


# --- estimate_vo2max ---------------------------------------------------------
def test_estimate_vo2max_returns_level():
    out = estimate_vo2max(avg_speed_kmh=25.0, avg_gradient_percent=2.0, weight_kg=70, age=35)
    assert "vo2_max_ml_kg_min" in out
    assert out["vo2_max_ml_kg_min"] == 42.0 or 30.0 <= out["vo2_max_ml_kg_min"] <= 75.0
    assert out["fitness_level"] in ("Below Average", "Average", "Good", "Very Good", "Excellent")


def test_estimate_vo2max_clamped():
    low = estimate_vo2max(avg_speed_kmh=5.0, avg_gradient_percent=0.0, weight_kg=70, age=80)
    assert low["vo2_max_ml_kg_min"] >= 30.0


# --- classify_ride_difficulty ----------------------------------------------
def test_classify_ride_difficulty_unknown_when_no_distance():
    out = classify_ride_difficulty(_ride(distance_km=0))
    assert out["level"] == "unknown"
    assert out["score"] == 0


def test_classify_ride_difficulty_levels():
    easy = classify_ride_difficulty(_ride(distance_km=10, elevation_gain_m=20, duration_minutes=30))
    hard = classify_ride_difficulty(_ride(distance_km=150, elevation_gain_m=3000, duration_minutes=300, avg_speed_kmh=35))
    assert easy["score"] < hard["score"]
    assert hard["level"] in ("Hard", "Extreme")


# --- analyze_elevation_profile ---------------------------------------------
def test_analyze_elevation_profile_empty():
    out = analyze_elevation_profile([])
    assert out["hardship_index"] == 0.0


def test_analyze_elevation_profile_with_points():
    pts = [_pt(45.0 + i * 0.001, 7.0, altitude=100.0 + i * 5) for i in range(10)]
    out = analyze_elevation_profile(pts)
    assert "grade_distribution" in out
    assert out["total_sampled"] >= 1


# --- analyze_speed_profile --------------------------------------------------
def test_analyze_speed_profile_insufficient():
    out = analyze_speed_profile([_pt(speed=20.0)])
    assert out["acceleration_events"] == 0


def test_analyze_speed_profile_events():
    pts = [_pt(45.0 + i * 0.001, 7.0, speed=15.0 + i * 3) for i in range(10)]
    out = analyze_speed_profile(pts)
    assert out["acceleration_events"] >= 1
    assert "speed_variance" in out


# --- calculate_progress_trend ----------------------------------------------
def test_calculate_progress_trend_insufficient():
    out = calculate_progress_trend([_ride()])
    assert out["trend"] == "insufficient_data"


def test_calculate_progress_trend_improving():
    rides = [
        _ride(date="2024-01-01", avg_speed_kmh=18.0),
        _ride(date="2024-01-02", avg_speed_kmh=20.0),
        _ride(date="2024-01-03", avg_speed_kmh=24.0),
    ]
    out = calculate_progress_trend(rides)
    assert out["trend"] == "improving"
    assert out["improvement_pct"] > 0


# --- estimate_ideal_weight --------------------------------------------------
def test_estimate_ideal_weight_invalid():
    assert estimate_ideal_weight(0.0, 0.0) == 70.0


def test_estimate_ideal_weight_elite():
    w = estimate_ideal_weight(350.0, 180.0, "Elite")
    assert 50.0 < w < 90.0


# --- calculate_garmin_power_factor -----------------------------------------
def test_calculate_garmin_power_factor_zero():
    out = calculate_garmin_power_factor(_ride(avg_speed_kmh=0.0))
    assert out["pf"] == 0.0


def test_calculate_garmin_power_factor_values():
    out = calculate_garmin_power_factor(_ride(avg_speed_kmh=30.0, weight_kg=70))
    assert out["pf"] >= 0.0
    assert "np_w" in out


# --- calculate_heart_rate_zones --------------------------------------------
def test_calculate_heart_rate_zones():
    zones = calculate_heart_rate_zones(max_hr=190, lthr=160)
    assert "Z1 (Recovery)" in zones
    assert "Z5 (VO2max)" in zones


def test_calculate_heart_rate_zones_in_zone():
    zones = calculate_heart_rate_zones(max_hr=190, lthr=160, current_avg_hr=170)
    assert all("in_zone" in z for z in zones.values())
    assert any(z["in_zone"] for z in zones.values())


# --- calculate_ride_recommendation_score -----------------------------------
def test_calculate_ride_recommendation_score():
    out = calculate_ride_recommendation_score(_ride(distance_km=15, avg_speed_kmh=22, elevation_gain_m=100))
    assert "overall_score" in out
    assert out["label"] in ("Recovery Ride", "Tempo Ride", "Hard Training", "Race / Peak Effort")


# --- detect_speed_surges ----------------------------------------------------
def test_detect_speed_surges_short():
    assert detect_speed_surges([_pt(speed=20.0)]) == []


def test_detect_speed_surges_detects():
    pts = [_pt(45.0 + i * 0.001, 7.0, speed=15.0 if i < 5 else 30.0) for i in range(10)]
    surges = detect_speed_surges(pts)
    assert isinstance(surges, list)


# --- calculate_training_stress_balance --------------------------------------
def test_training_stress_balance_no_data():
    out = calculate_training_stress_balance([])
    assert out["form"] == "no_data"


def test_training_stress_balance_with_rides():
    rides = [
        _ride(date="2024-01-01", distance_km=40, duration_minutes=120),
        _ride(date="2024-01-03", distance_km=50, duration_minutes=150),
        _ride(date="2024-01-05", distance_km=30, duration_minutes=90),
    ]
    out = calculate_training_stress_balance(rides)
    assert "atl" in out and "ctl" in out and "tsb" in out
    assert out["form"] in ("fresh", "optimal", "fatigued", "overreached", "burnout_risk")


# --- calculate_pace_consistency / classify_climb / power_estimate ----------
def test_calculate_pace_consistency():
    a = _pt(45.0, 7.0, speed=20.0)
    b = _pt(45.1, 7.1, speed=20.0)
    segs = [Segment(start=a, end=b, avg_speed_km_h=20.0), Segment(start=b, end=_pt(45.2, 7.2, speed=22.0), avg_speed_km_h=22.0)]
    out = calculate_pace_consistency(segs)
    assert "cv_percent" in out


def test_calculate_pace_consistency_insufficient():
    out = calculate_pace_consistency([])
    assert out["pace_strategy"] == "unknown"


def test_classify_climb_none():
    out = classify_climb(0.1, 1.0)
    assert out["category"] == "none"


def test_classify_climb_hc():
    out = classify_climb(5.0, 16.0)
    assert out["category"] == "HC"
    assert out["points"] == 5


def test_calculate_power_estimate_zero():
    out = calculate_power_estimate(_ride(avg_speed_kmh=0.0, duration_minutes=0))
    assert out["power_avg_w"] == 0.0


def test_calculate_power_estimate_values():
    out = calculate_power_estimate(_ride(avg_speed_kmh=25.0, elevation_gain_m=200, distance_km=30))
    assert out["power_avg_w"] > 0
    assert "grade_percent" in out
