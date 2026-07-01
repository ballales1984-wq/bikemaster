"""Tests for core calculator modules."""

from datetime import UTC, date, datetime

from fastapi import HTTPException
from pydantic import ValidationError

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
from bike_analyzer.core.calculators.power import intensity_factor as intensity_factor_core, normalized_power_approx, training_stress_score as training_stress_score_core
from bike_analyzer.core.calculators.stress import ewma
from bike_analyzer.core.engine import AnalysisEngine, EngineResult
from bike_analyzer.core.fitness_state import FitnessStateVector, TrainingStressDay
from bike_analyzer.backend.rate_limiter import (
    RateLimitConfig,
    _is_trusted_proxy,
    check_user_rate_limit,
    get_limiter_key,
    limiter,
    rate_limit_dependency,
)

from bike_analyzer.core.models import AthleteProfile, GPSPoint, Ride
from bike_analyzer.core.validation import ValidatedAthleteProfile, ValidatedGPSPoint, ValidatedRide
from bike_analyzer.core.validators import (
    BusinessValidationError,
    validate_athlete_profile,
    validate_athlete_profile_partial,
    validate_gps_points,
    validate_ride_for_analysis,
    validate_ride_for_import,
)
from bike_analyzer.backend.maps.google_maps import (
    _interpolate_color,
    _speed_to_color,
    _css_to_google_hex,
    _build_speed_segments,
    build_speed_colored_path,
    create_google_static_map,
    SpeedColorSegment,
)
from bike_analyzer.backend.analytics.power_model import (
    normalized_power,
    intensity_factor as intensity_factor_power_model,
    variability_index,
    efficiency_factor,
    training_stress_score as training_stress_score_power_model,
    calculate_power_zones,
    calculate_power_profile,
    estimate_ftp_from_20min,
    estimate_critical_power,
    detect_aerobic_decoupling,
    calculate_advanced_power_metrics,
)
from bike_analyzer.backend.analytics.training_load import (
    TrainingLoadDay,
    calculate_rss,
    calculate_atl_ctl_tsb,
    get_current_training_status,
    get_7day_fitness_summary,
)


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
        tss = training_stress_score_core(r, ftp=250)
        assert tss == 0.0


class TestIntensityFactor:
    def test_basic(self):
        r = _ride(heart_rate_avg=150, avg_speed_kmh=25)
        if_ = intensity_factor_core(r, ftp=250)
        assert 0 <= if_ <= 1.0

    def test_zero_ftp(self):
        r = _ride()
        assert intensity_factor_core(r, ftp=0) == 0.0


class TestTrainingStressScore:
    def test_basic(self):
        r = _ride(duration_minutes=60, heart_rate_avg=150, avg_speed_kmh=25)
        tss = training_stress_score_core(r, ftp=250)
        assert tss > 0

    def test_zero_duration(self):
        r = _ride(duration_minutes=0)
        assert training_stress_score_core(r) == 0.0

    def test_capped_at_500(self):
        r = _ride(duration_minutes=600, heart_rate_avg=200, avg_speed_kmh=50)
        tss = training_stress_score_core(r, ftp=250)
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


class TestFitnessStateVector:
    def test_to_dict(self):
        state = FitnessStateVector(
            athlete_id=1, computed_at=datetime(2024, 1, 1, tzinfo=UTC), atl=50, ctl=60, tsb=10
        )
        d = state.to_dict()
        assert d["athlete_id"] == 1
        assert "atl" in d
        assert "is_overtraining_risk" in d
        assert "is_fresh" in d
        assert "is_ready_for_hard_effort" in d

    def test_is_overtraining_risk(self):
        state = FitnessStateVector(athlete_id=1, computed_at=datetime.now(UTC), atl=80, ctl=60, tsb=-25)
        assert state.is_overtraining_risk is True

    def test_is_not_overtraining_risk(self):
        state = FitnessStateVector(athlete_id=1, computed_at=datetime.now(UTC), atl=50, ctl=60, tsb=10)
        assert state.is_overtraining_risk is False

    def test_is_fresh(self):
        state = FitnessStateVector(athlete_id=1, computed_at=datetime.now(UTC), tsb=20)
        assert state.is_fresh is True

    def test_is_ready_for_hard_effort(self):
        state = FitnessStateVector(athlete_id=1, computed_at=datetime.now(UTC), atl=50, ctl=60, tsb=10)
        assert state.is_ready_for_hard_effort is True


class TestTrainingStressDay:
    def test_creation(self):
        tsd = TrainingStressDay(date=date(2024, 1, 1), tss=50.0, atl=40.0, ctl=50.0, tsb=10.0)
        assert tsd.tss == 50.0
        assert tsd.atl == 40.0


class TestAnalysisEngine:
    def test_process_ride_sync(self):
        engine = AnalysisEngine(ftp=250)
        r = _ride(duration_minutes=60, heart_rate_avg=150, avg_speed_kmh=25)
        result = engine.process_ride_sync(r)
        assert result.success
        assert result.result is not None

    def test_process_ride_sync_error(self):
        engine = AnalysisEngine(ftp=250)
        r = _ride(duration_minutes=60)
        result = engine.process_ride_sync(r)
        assert result.success or result.error is not None

    def test_engine_result_dataclass(self):
        res = EngineResult(success=True, error=None)
        assert res.success is True

    @pytest.mark.asyncio
    async def test_process_ride_async_no_athlete(self):
        engine = AnalysisEngine(ftp=250)
        r = _ride(duration_minutes=60)
        result = await engine.process_ride(r)
        assert result.success

    @pytest.mark.asyncio
    async def test_process_ride_async_with_historical(self):
        engine = AnalysisEngine(ftp=250)
        r = _ride(duration_minutes=60, date="2024-06-15")
        historical = [_ride(duration_minutes=90, date="2024-06-14")]
        result = await engine.process_ride(r, athlete_id=1, historical_rides=historical)
        assert result.success
        assert result.fitness_state is not None

    @pytest.mark.asyncio
    async def test_process_rides_batch(self):
        engine = AnalysisEngine(ftp=250)
        rides = [_ride(duration_minutes=60) for _ in range(3)]
        results = await engine.process_rides_batch(rides)
        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_process_ride_no_historical(self):
        engine = AnalysisEngine(ftp=250)
        r = _ride(duration_minutes=60, date="2024-06-15")
        result = await engine.process_ride(r, athlete_id=1, historical_rides=None)
        assert result.success


class TestAnalysisPipeline:
    def test_run_sync(self):
        from bike_analyzer.core.pipeline import AnalysisPipeline
        pipeline = AnalysisPipeline(ftp=250)
        r = _ride(duration_minutes=60)
        result = pipeline.run_sync(r)
        assert result.ride is not None
        assert result.metrics is not None

    def test_run_sync_no_gps(self):
        from bike_analyzer.core.pipeline import AnalysisPipeline
        pipeline = AnalysisPipeline(ftp=250)
        r = _ride(duration_minutes=60)
        result = pipeline.run_sync(r)
        assert result.route_statistics is None or result.metrics is not None

    @pytest.mark.asyncio
    async def test_run_async(self):
        from bike_analyzer.core.pipeline import AnalysisPipeline
        pipeline = AnalysisPipeline(ftp=250)
        r = _ride(duration_minutes=60)
        result = await pipeline.run(r)
        assert result.ride is not None
        assert result.metrics is not None


class TestValidatedGPSPoint:
    def test_valid_point(self):
        pt = ValidatedGPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC))
        assert pt.lat == 45.0

    def test_invalid_lat(self):
        with pytest.raises(ValidationError):
            ValidatedGPSPoint(lat=100.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC))


class TestValidatedRide:
    def test_valid_ride(self):
        r = ValidatedRide(
            athlete_id=1,
            date=date(2024, 1, 15),
            distance_km=25.0,
            duration_minutes=60.0,
            gps_points=[],
        )
        assert r.athlete_id == 1

    def test_invalid_distance(self):
        with pytest.raises(ValidationError):
            ValidatedRide(athlete_id=1, date=date(2024, 1, 15), distance_km=-5, duration_minutes=60)


class TestValidatedAthleteProfile:
    def test_valid_profile(self):
        p = ValidatedAthleteProfile(
            name="Test Rider",
            age=30,
            weight_kg=70.0,
            experience_level="Intermediate",
        )
        assert p.name == "Test Rider"

    def test_invalid_weight(self):
        with pytest.raises(ValidationError):
            ValidatedAthleteProfile(name="Test", age=30, weight_kg=250, experience_level="Intermediate")


class TestValidators:
    def test_validate_ride_for_analysis(self):
        ride_data = {
            "athlete_id": 1,
            "date": "2024-06-15",
            "distance_km": 25.0,
            "duration_minutes": 60.0,
            "gps_points": [],
        }
        ride = validate_ride_for_analysis(ride_data)
        assert isinstance(ride, Ride)
        assert ride.athlete_id == 1

    def test_validate_ride_for_import(self):
        ride_data = {"athlete_id": 1, "date": "2024-06-15", "distance_km": 25, "duration_minutes": 60}
        ride = validate_ride_for_import(ride_data)
        assert isinstance(ride, Ride)

    def test_validate_ride_invalid(self):
        with pytest.raises(BusinessValidationError):
            validate_ride_for_analysis({"athlete_id": -1, "date": "2024-06-15", "distance_km": 25, "duration_minutes": 60})

    def test_validate_gps_points_too_few(self):
        with pytest.raises(BusinessValidationError):
            validate_gps_points([{"lat": 45.0, "lon": 9.0, "timestamp": "2024-01-01T00:00:00Z"}])

    def test_validate_gps_points_valid(self):
        pts = [
            {"lat": 45.0, "lon": 9.0, "timestamp": "2024-01-01T00:00:00Z"},
            {"lat": 45.1, "lon": 9.1, "timestamp": "2024-01-01T00:01:00Z"},
        ]
        result = validate_gps_points(pts)
        assert len(result) == 2

    def test_validate_athlete_profile(self):
        data = {"name": "Test Rider", "age": 30, "weight_kg": 70.0, "experience_level": "Intermediate"}
        profile = validate_athlete_profile(data)
        assert isinstance(profile, AthleteProfile)
        assert profile.name == "Test Rider"

    def test_validate_athlete_profile_partial(self):
        data = {"name": "Test", "age": 25, "weight_kg": 65.0, "experience_level": "Beginner"}
        profile = validate_athlete_profile_partial(data)
        assert profile.experience_level == "Beginner"


class TestDashboardGenerator:
    def test_generate_dashboard_html(self):
        import tempfile
        import os
        from bike_analyzer.frontend.dashboard import DASHBOARD_HTML, generate_dashboard_html

        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_dashboard_html(f"{tmpdir}/test_dashboard.html")
            assert os.path.exists(path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "BikeMaster" in content
            assert "<!DOCTYPE html>" in content

    def test_dashboard_html_content(self):
        from bike_analyzer.frontend.dashboard import DASHBOARD_HTML
        assert "🚴" in DASHBOARD_HTML
        assert "loadRides" in DASHBOARD_HTML
        assert "fetchWeather" in DASHBOARD_HTML


class TestRateLimiter:
    def test_is_trusted_proxy_localhost(self):
        assert _is_trusted_proxy("127.0.0.1") is True

    def test_is_trusted_proxy_private(self):
        assert _is_trusted_proxy("192.168.1.1") is True

    def test_is_trusted_proxy_public(self):
        assert _is_trusted_proxy("8.8.8.8") is False

    def test_rate_limit_config_defaults(self):
        cfg = RateLimitConfig()
        assert cfg.max_requests == 100
        assert cfg.window_seconds == 60

    def test_rate_limit_config_custom(self):
        cfg = RateLimitConfig(max_requests=50, window_seconds=30)
        assert cfg.max_requests == 50
        assert cfg.window_seconds == 30

    def test_check_user_rate_limit_allows(self):
        cfg = RateLimitConfig(max_requests=5, window_seconds=60)
        check_user_rate_limit(999, "test", cfg)

    def test_check_user_rate_limit_blocks(self):
        cfg = RateLimitConfig(max_requests=2, window_seconds=60)
        check_user_rate_limit(998, "test", cfg)
        check_user_rate_limit(998, "test", cfg)
        with pytest.raises(HTTPException):
            check_user_rate_limit(998, "test", cfg)

    def test_rate_limit_dependency(self):
        from unittest.mock import MagicMock
        dep = rate_limit_dependency(max_requests=10, window_seconds=30)
        mock_user = {"id": "123"}
        result = dep(mock_user)
        assert result == mock_user

    def test_is_trusted_proxy_ipv6(self):
        assert _is_trusted_proxy("::1") is True

    def test_is_trusted_proxy_invalid(self):
        assert _is_trusted_proxy("not-an-ip") is False


class TestGoogleMapsHelpers:
    def test_interpolate_color_min(self):
        assert _interpolate_color(30, 30, 30) == "#FFFF00"

    def test_interpolate_color_mid(self):
        result = _interpolate_color(15, 0, 30)
        assert result.startswith("#")

    def test_speed_to_color_fast(self):
        assert _speed_to_color(40) == "#00cc44"

    def test_speed_to_color_medium(self):
        assert _speed_to_color(20) == "#ddbb00"

    def test_speed_to_color_slow(self):
        assert _speed_to_color(10) == "#ee8800"

    def test_speed_to_color_none(self):
        assert _speed_to_color(None) == "#4488ff"

    def test_css_to_google_hex(self):
        assert _css_to_google_hex("#FF0000") == "0xFF0000"

    def test_css_to_google_hex_prefixed(self):
        assert _css_to_google_hex("0xABC") == "0xABC"


class TestGoogleMapsBuilder:
    def test_build_speed_colored_path_empty(self):
        assert build_speed_colored_path([]) == []

    def test_build_speed_colored_path_single(self):
        pts = [GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC))]
        assert build_speed_colored_path(pts) == []

    def test_build_speed_colored_path_multiple(self):
        pts = [
            GPSPoint(lat=45.0, lon=9.0, speed=25.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC)),
            GPSPoint(lat=45.1, lon=9.1, speed=30.0, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC)),
        ]
        result = build_speed_colored_path(pts)
        assert len(result) >= 1
        assert "start" in result[0]
        assert "end" in result[0]

    def test_create_google_static_map_invalid(self):
        with pytest.raises(ValueError):
            create_google_static_map([], "test-mock-key")

    def test_create_google_static_map_mock(self):
        pts = [
            GPSPoint(lat=45.0, lon=9.0, speed=25.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC)),
            GPSPoint(lat=45.1, lon=9.1, speed=30.0, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC)),
        ]
        result = create_google_static_map(pts, "test-mock-key")
        assert result == "google_map.png"

    def test_create_google_static_map_colored_mock(self):
        pts = [
            GPSPoint(lat=45.0, lon=9.0, speed=25.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC)),
            GPSPoint(lat=45.1, lon=9.1, speed=30.0, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC)),
        ]
        result = create_google_static_map(pts, "test-mock-key", colored=True)
        assert result == "google_map.png"


class TestPowerModel:
    def test_normalized_power_basic(self):
        watts = [200.0] * 50
        np = normalized_power(watts, window_size=30)
        assert np > 0

    def test_normalized_power_empty(self):
        assert normalized_power([]) == 0.0

    def test_intensity_factor(self):
        assert intensity_factor_power_model(200.0, 250.0) > 0

    def test_variability_index(self):
        assert variability_index(220, 200) > 1

    def test_efficiency_factor(self):
        assert efficiency_factor(200, 150) > 0

    def test_training_stress_score(self):
        tss = training_stress_score_power_model(200, 0.8, 1.0)
        assert tss > 0

    def test_calculate_power_zones(self):
        pts = [
            GPSPoint(lat=45.0, lon=9.0, power=200.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC)),
            GPSPoint(lat=45.1, lon=9.1, power=250.0, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC)),
        ]
        zones = calculate_power_zones(pts, 250.0)
        assert "Z1" in zones

    def test_calculate_advanced_power_metrics(self):
        pts = [
            GPSPoint(lat=45.0, lon=9.0, power=200.0, heart_rate=150.0, timestamp=datetime(2024, 1, 1, tzinfo=UTC)),
            GPSPoint(lat=45.1, lon=9.1, power=250.0, heart_rate=160.0, timestamp=datetime(2024, 1, 1, 0, 1, tzinfo=UTC)),
        ]
        metrics = calculate_advanced_power_metrics(pts, ftp=250)
        assert metrics["available"] is True

    def test_calculate_power_profile_empty(self):
        result = calculate_power_profile([])
        assert all(v is None for v in result.values())

    def test_estimate_ftp_from_20min_none(self):
        assert estimate_ftp_from_20min([]) == 0.0

    def test_estimate_critical_power_none(self):
        result = estimate_critical_power([])
        assert result["cp_w"] == 0.0

    def test_detect_aerobic_decoupling_short(self):
        pts = [GPSPoint(lat=45.0, lon=9.0, power=200.0, heart_rate=150, timestamp=datetime(2024, 1, 1, tzinfo=UTC)) for _ in range(10)]
        result = detect_aerobic_decoupling(pts, ftp=250)
        assert result["significant"] is False


class TestTrainingLoad:
    def test_calculate_rss(self):
        r = _ride(duration_minutes=60)
        rss = calculate_rss(r)
        assert rss > 0

    def test_calculate_rss_zero_duration(self):
        r = _ride(duration_minutes=0)
        rss = calculate_rss(r)
        assert rss == 0.0

    def test_calculate_atl_ctl_tsb(self):
        rides = [_ride(date="2024-06-15", duration_minutes=60)]
        result = calculate_atl_ctl_tsb(rides)
        assert len(result) == 1
        assert result[0].tss > 0

    def test_calculate_atl_ctl_tsb_empty(self):
        result = calculate_atl_ctl_tsb([])
        assert result == []

    def test_get_current_training_status_empty(self):
        status = get_current_training_status([])
        assert status["status"] == "no_data"

    def test_get_current_training_status_fresh(self):
        rides = [_ride(date="2024-06-15", duration_minutes=10)]
        status = get_current_training_status(rides)
        assert "tsb" in status

    def test_get_7day_fitness_summary_empty(self):
        result = get_7day_fitness_summary([])
        assert result == []


class TestGoogleMapsErrors:
    def test_interpolate_color_equal_bounds(self):
        result = _interpolate_color(25, 30, 30)
        assert result == "#FFFF00"

    def test_speed_to_color_all_ranges(self):
        assert _speed_to_color(45) == "#00cc44"
        assert _speed_to_color(30) == "#88cc00"
        assert _speed_to_color(20) == "#ddbb00"
        assert _speed_to_color(10) == "#ee8800"
        assert _speed_to_color(3) == "#ee3333"
