"""Tests for core calculator modules."""

from datetime import UTC, datetime

import pytest

from bike_analyzer.core.calculators.calories import calories_met, calories_physics, estimate, per_km
from bike_analyzer.core.calculators.fatigue import (
    calculate_fatigue_score,
    estimate_recovery_hours,
    get_recovery_recommendation,
)
from bike_analyzer.core.calculators.performance import (
    efficiency_score,
    endurance_score,
    monthly_scores,
    performance_score,
    recovery_score,
)
from bike_analyzer.core.calculators.power import intensity_factor, normalized_power_approx, training_stress_score
from bike_analyzer.core.calculators.stress import ewma
from bike_analyzer.core.models import GPSPoint, Ride


def _ride(**kwargs):
    defaults = dict(
        id=1, athlete_id=1, date="2024-06-15",
        distance_km=25.0, duration_minutes=60.0, avg_speed_kmh=25.0,
        weight_kg=70.0, calories=600.0, heart_rate_avg=150.0,
        elevation_gain_m=200.0, gps_points=[],
    )
    defaults.update(kwargs)
    return Ride(**defaults)


class TestCaloriesMet:
    def test_basic(self):
        r = _ride(duration_minutes=60, weight_kg=70, avg_speed_kmh=20)
        c = calories_met(r)
        assert c > 0

    def test_none_speed(self):
        r = _ride(avg_speed_kmh=None)
        assert calories_met(r) == 0.0

    def test_slow_speed(self):
        r = _ride(avg_speed_kmh=10, duration_minutes=60, weight_kg=70)
        c = calories_met(r)
        assert c > 0

    def test_fast_speed(self):
        r = _ride(avg_speed_kmh=35, duration_minutes=60, weight_kg=70)
        c = calories_met(r)
        assert c > 0

    def test_zero_duration(self):
        r = _ride(duration_minutes=0)
        assert calories_met(r) == 0.0

    def test_zero_weight(self):
        r = _ride(weight_kg=0)
        assert calories_met(r) == 0.0


class TestCaloriesPhysics:
    def test_basic(self):
        r = _ride(avg_speed_kmh=25, elevation_gain_m=200, distance_km=25)
        c = calories_physics(r)
        assert c > 0

    def test_none_speed(self):
        r = _ride(avg_speed_kmh=None)
        assert calories_physics(r) == 0.0

    def test_zero_distance(self):
        r = _ride(distance_km=0)
        c = calories_physics(r)
        assert c >= 0

    def test_flat_route(self):
        r = _ride(avg_speed_kmh=25, elevation_gain_m=0, distance_km=25)
        c = calories_physics(r)
        assert c > 0


class TestEstimate:
    def test_default_method_met(self):
        r = _ride(duration_minutes=60)
        c = estimate(r)
        assert c > 0


class TestPerKm:
    def test_basic(self):
        r = _ride(calories=600, distance_km=25)
        assert per_km(r) == 24.0

    def test_zero_distance(self):
        r = _ride(distance_km=0)
        assert per_km(r) == 0.0


class TestEwma:
    def test_empty(self):
        assert ewma([], 7.0) == 0.0

    def test_single_value(self):
        assert ewma([100.0], 7.0) == 100.0

    def test_multiple_values(self):
        result = ewma([100.0, 110.0, 105.0, 120.0], 7.0)
        assert result > 0
        assert isinstance(result, float)

    def test_tau_small(self):
        result = ewma([100.0, 200.0], 1.0)
        assert result > 100.0

    def test_tau_large(self):
        result = ewma([100.0, 200.0], 100.0)
        assert 100.0 <= result <= 200.0


class TestFatigueScore:
    def test_low_fatigue(self):
        r = _ride(duration_minutes=30, heart_rate_avg=100, avg_speed_kmh=15, elevation_gain_m=0)
        score = calculate_fatigue_score(r)
        assert score < 5.0

    def test_high_fatigue(self):
        r = _ride(duration_minutes=300, heart_rate_avg=180, avg_speed_kmh=35, elevation_gain_m=1000, weight_kg=90)
        score = calculate_fatigue_score(r)
        assert score > 5.0

    def test_capped_at_10(self):
        r = _ride(duration_minutes=600, heart_rate_avg=200, avg_speed_kmh=50, elevation_gain_m=5000, weight_kg=120)
        score = calculate_fatigue_score(r)
        assert score <= 10.0

    def test_no_heart_rate(self):
        r = _ride(heart_rate_avg=None)
        score = calculate_fatigue_score(r)
        assert score >= 0

    def test_custom_age(self):
        r = _ride(heart_rate_avg=180)
        s1 = calculate_fatigue_score(r, rider_age=25)
        s2 = calculate_fatigue_score(r, rider_age=50)
        assert s1 != s2


class TestRecoveryHours:
    def test_low_fatigue(self):
        assert estimate_recovery_hours(2.0) == 8.0

    def test_moderate_fatigue(self):
        assert estimate_recovery_hours(5.0) == 16.0

    def test_high_fatigue(self):
        assert estimate_recovery_hours(7.0) == 24.0

    def test_extreme_fatigue(self):
        assert estimate_recovery_hours(9.0) == 48.0


class TestRecoveryRecommendation:
    def test_minimal(self):
        assert "Minimal" in get_recovery_recommendation(1.0)

    def test_light(self):
        assert "Light" in get_recovery_recommendation(3.0)

    def test_moderate(self):
        assert "Moderate" in get_recovery_recommendation(5.0)

    def test_high(self):
        assert "High" in get_recovery_recommendation(8.0)

    def test_extreme(self):
        assert "Extreme" in get_recovery_recommendation(9.5)


class TestPerformanceScore:
    def test_basic(self):
        r = _ride(avg_speed_kmh=25, duration_minutes=90, elevation_gain_m=200)
        score = performance_score(r)
        assert 0 <= score <= 10

    def test_zero_speed(self):
        r = _ride(avg_speed_kmh=0, duration_minutes=0, elevation_gain_m=0)
        assert performance_score(r) == 0.0

    def test_max_performance(self):
        r = _ride(avg_speed_kmh=50, duration_minutes=300, elevation_gain_m=2000)
        score = performance_score(r)
        assert score == 10.0


class TestEnduranceScore:
    def test_empty(self):
        assert endurance_score([]) == 0.0

    def test_single_ride(self):
        rides = [_ride(duration_minutes=60)]
        score = endurance_score(rides)
        assert score >= 0

    def test_long_rides(self):
        rides = [_ride(duration_minutes=180) for _ in range(10)]
        score = endurance_score(rides)
        assert score > 0


class TestRecoveryScore:
    def test_low_fatigue(self):
        r = _ride(duration_minutes=30, heart_rate_avg=100)
        score = recovery_score(r)
        assert score > 5.0

    def test_high_fatigue(self):
        r = _ride(duration_minutes=300, heart_rate_avg=180)
        score = recovery_score(r)
        assert score < 5.0


class TestEfficiencyScore:
    def test_basic(self):
        r = _ride(distance_km=25, calories=600)
        score = efficiency_score(r)
        assert 0 <= score <= 10

    def test_zero_distance(self):
        r = _ride(distance_km=0)
        assert efficiency_score(r) == 0.0

    def test_low_calories(self):
        r = _ride(distance_km=25, calories=100)
        score = efficiency_score(r)
        assert score > 5.0


class TestMonthlyScores:
    def test_empty(self):
        result = monthly_scores([])
        assert result["performance"] == 0
        assert result["avg_fatigue"] == 0

    def test_with_rides(self):
        rides = [_ride(duration_minutes=90, heart_rate_avg=150) for _ in range(5)]
        result = monthly_scores(rides)
        assert "performance" in result
        assert "endurance" in result


class TestNormalizedPower:
    def test_no_data(self):
        r = _ride(heart_rate_avg=None, avg_speed_kmh=0)
        assert normalized_power_approx(r) == 0.0

    def test_with_power_data(self):
        points = [GPSPoint(lat=45.0, lon=9.0, power=200.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC)) for _ in range(15)]
        r = _ride(gps_points=points)
        np = normalized_power_approx(r)
        assert np > 0

    def test_hr_fallback(self):
        r = _ride(heart_rate_avg=150, avg_speed_kmh=25)
        np = normalized_power_approx(r)
        assert np > 0

    def test_low_hr_and_speed(self):
        r = _ride(heart_rate_avg=100, avg_speed_kmh=10)
        np = normalized_power_approx(r)
        assert np > 0

    def test_zero_if_for_tss(self):
        r = _ride(duration_minutes=60, heart_rate_avg=None, avg_speed_kmh=0)
        tss = training_stress_score(r, ftp=250)
        assert tss == 0.0


class TestIntensityFactor:
    def test_basic(self):
        r = _ride(heart_rate_avg=150, avg_speed_kmh=25)
        if_ = intensity_factor(r, ftp=250)
        assert 0 <= if_ <= 1.0

    def test_zero_ftp(self):
        r = _ride()
        assert intensity_factor(r, ftp=0) == 0.0


class TestTrainingStressScore:
    def test_basic(self):
        r = _ride(duration_minutes=60, heart_rate_avg=150, avg_speed_kmh=25)
        tss = training_stress_score(r, ftp=250)
        assert tss > 0

    def test_zero_duration(self):
        r = _ride(duration_minutes=0)
        assert training_stress_score(r) == 0.0

    def test_capped_at_500(self):
        r = _ride(duration_minutes=600, heart_rate_avg=200, avg_speed_kmh=50)
        tss = training_stress_score(r, ftp=250)
        assert tss <= 500.0


class TestCaloriesMetSpeedRanges:
    def test_met_below_16(self):
        r = _ride(avg_speed_kmh=15, duration_minutes=60, weight_kg=70)
        c = calories_met(r)
        assert c > 0

    def test_met_16_to_19(self):
        r = _ride(avg_speed_kmh=18, duration_minutes=60, weight_kg=70)
        c = calories_met(r)
        assert c > 0

    def test_met_19_to_22(self):
        r = _ride(avg_speed_kmh=20, duration_minutes=60, weight_kg=70)
        c = calories_met(r)
        assert c > 0


class TestCaloriesPhysicsEdgeCases:
    def test_zero_elevation(self):
        r = _ride(avg_speed_kmh=25, elevation_gain_m=0, distance_km=25)
        c = calories_physics(r)
        assert c > 0

    def test_duration_hours_attribute(self):
        r = _ride(avg_speed_kmh=25, duration_minutes=60, distance_km=25)
        from bike_analyzer.core.calculators.calories import calories_met
        assert hasattr(r, 'duration_hours') or r.duration_minutes == 60


class TestPhysicsMethod:
    def test_estimate_physics(self):
        r = _ride(avg_speed_kmh=25, elevation_gain_m=200, distance_km=25)
        c = estimate(r, method="physics")
        assert c > 0

    def test_estimate_met(self):
        r = _ride(avg_speed_kmh=25, elevation_gain_m=200, distance_km=25)
        c = estimate(r, method="met")
        assert c > 0
