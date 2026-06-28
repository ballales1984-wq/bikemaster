"""Tests for analytics services."""

from datetime import UTC, datetime, date
from unittest.mock import MagicMock, patch

import pytest

from bike_analyzer.backend.analytics.services.fitness_state_service import FitnessStateEngine
from bike_analyzer.backend.analytics.services.ride_analysis_service import RideAnalysisService
from bike_analyzer.backend.analytics.training_stress import (
    estimate_tss,
    exponentially_weighted_moving_average,
)
from bike_analyzer.core.models import Ride


def _ride(**kwargs):
    defaults = dict(
        id=1, athlete_id=1, date=date.today().isoformat(),
        distance_km=25.0, duration_minutes=60.0, avg_speed_kmh=25.0,
        weight_kg=70.0, calories=600.0, heart_rate_avg=150.0,
        elevation_gain_m=200.0, gps_points=[],
    )
    defaults.update(kwargs)
    return Ride(**defaults)


class TestExponentiallyWeightedMovingAverage:
    def test_empty(self):
        assert exponentially_weighted_moving_average([], 7.0) == 0.0

    def test_single_value(self):
        assert exponentially_weighted_moving_average([100.0], 7.0) == 100.0

    def test_returns_float(self):
        result = exponentially_weighted_moving_average([100.0, 110.0], 7.0)
        assert isinstance(result, float)

    def test_rounded(self):
        result = exponentially_weighted_moving_average([100.0, 110.0], 7.0)
        assert result == round(result, 1)

    def test_larger_tau_smoother(self):
        vals = [100.0, 200.0]
        r_small = exponentially_weighted_moving_average(vals, 1.0)
        r_large = exponentially_weighted_moving_average(vals, 100.0)
        assert r_small > r_large

    def test_identical_values(self):
        result = exponentially_weighted_moving_average([50.0, 50.0, 50.0], 7.0)
        assert result == 50.0


class TestEstimateTss:
    def test_zero_duration(self):
        r = _ride(duration_minutes=0)
        assert estimate_tss(r, ftp=250) == 0.0

    def test_basic_ride(self):
        r = _ride(duration_minutes=60, avg_speed_kmh=25)
        tss = estimate_tss(r, ftp=250)
        assert tss > 0

    def test_capped_at_500(self):
        r = _ride(duration_minutes=600, avg_speed_kmh=50)
        tss = estimate_tss(r, ftp=250)
        assert tss <= 500.0

    def test_with_intensity_factor(self):
        r = _ride(duration_minutes=60, avg_speed_kmh=25)
        r.intensity_factor = 0.8
        tss = estimate_tss(r, ftp=250)
        assert tss > 0

    def test_intensity_factor_override(self):
        r = _ride(duration_minutes=60, avg_speed_kmh=25)
        r.intensity_factor = 0.8
        tss1 = estimate_tss(r, ftp=250)
        r.intensity_factor = 0.5
        tss2 = estimate_tss(r, ftp=250)
        assert tss1 > tss2


class TestFitnessStateEngine:
    def _make_engine(self, stress_repo=None):
        return FitnessStateEngine(stress_repo=stress_repo, ftp=250.0)

    def test_default_ftp(self):
        engine = self._make_engine()
        assert engine.ftp == 250.0

    def test_custom_ftp(self):
        engine = FitnessStateEngine(ftp=300.0)
        assert engine.ftp == 300.0

    def test_compute_no_rides(self):
        engine = self._make_engine()
        result = engine.compute([], athlete_id=1)
        assert result.athlete_id == 1
        assert result.atl == 0.0
        assert result.ctl == 0.0

    def test_compute_single_ride(self):
        engine = self._make_engine()
        rides = [_ride(duration_minutes=60, avg_speed_kmh=25)]
        result = engine.compute(rides, athlete_id=1)
        assert result.athlete_id == 1
        assert result.weekly_tss > 0

    def test_compute_multiple_rides(self):
        engine = self._make_engine()
        rides = [_ride(duration_minutes=60, avg_speed_kmh=25) for _ in range(5)]
        result = engine.compute(rides, athlete_id=1)
        assert result.athlete_id == 1
        assert result.atl > 0 or result.ctl > 0

    def test_compute_with_different_dates(self):
        from datetime import date, timedelta
        engine = self._make_engine()
        today = date.today()
        rides = [
            _ride(date=(today - timedelta(days=10)).isoformat(), duration_minutes=60, avg_speed_kmh=25),
            _ride(date=(today - timedelta(days=3)).isoformat(), duration_minutes=60, avg_speed_kmh=25),
            _ride(date=today.isoformat(), duration_minutes=60, avg_speed_kmh=25),
        ]
        result = engine.compute(rides, athlete_id=1)
        assert result.weekly_tss > 0

    def test_compute_risk_indicators(self):
        engine = self._make_engine()
        rides = [_ride(duration_minutes=300, avg_speed_kmh=35, heart_rate_avg=180) for _ in range(7)]
        result = engine.compute(rides, athlete_id=1)
        assert isinstance(result.risk_indicators, list)

    def test_trend_stable(self):
        assert FitnessStateEngine._trend([50.0, 50.0, 50.0]) == "stable"

    def test_trend_increasing(self):
        assert FitnessStateEngine._trend([10.0, 20.0, 30.0, 40.0]) == "increasing"

    def test_trend_decreasing(self):
        assert FitnessStateEngine._trend([40.0, 30.0, 20.0, 10.0]) == "decreasing"

    def test_trend_single_value(self):
        assert FitnessStateEngine._trend([50.0]) == "stable"

    def test_trend_two_values_increasing(self):
        assert FitnessStateEngine._trend([10.0, 11.0]) == "stable"


class TestRideAnalysisService:
    def test_init_default(self):
        service = RideAnalysisService()
        assert service.pipeline is not None
        assert service.fitness_engine is not None

    def test_init_custom_ftp(self):
        service = RideAnalysisService(ftp=300.0)
        assert service.pipeline.ftp == 300.0
        assert service.fitness_engine.ftp == 300.0

    def test_analyze_sync(self):
        service = RideAnalysisService()
        ride = _ride(duration_minutes=60, avg_speed_kmh=25)
        result = service.analyze_sync(ride)
        assert "ride" in result
        assert "metrics" in result

    def test_analyze_sync_returns_metrics(self):
        service = RideAnalysisService()
        ride = _ride(duration_minutes=60, avg_speed_kmh=25)
        result = service.analyze_sync(ride)
        assert "fatigue_score" in result["metrics"]
        assert "calories" in result["metrics"]

    @pytest.mark.asyncio
    async def test_analyze_async(self):
        service = RideAnalysisService()
        ride = _ride(duration_minutes=60, avg_speed_kmh=25)
        result = await service.analyze(ride)
        assert "ride" in result
        assert "metrics" in result
