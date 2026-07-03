"""Tests for core engine module."""

from unittest.mock import MagicMock, patch

import pytest

from bike_analyzer.core.engine import AnalysisEngine, EngineResult
from bike_analyzer.core.models import Ride


def _ride(**kwargs):
    defaults = dict(
        id=1, athlete_id=1, date="2024-06-15",
        distance_km=25.0, duration_minutes=60.0, avg_speed_kmh=25.0,
        weight_kg=70.0, calories=600.0, heart_rate_avg=150.0,
        elevation_gain_m=200.0, gps_points=[],
    )
    defaults.update(kwargs)
    return Ride(**defaults)


class TestEngineResult:
    def test_success(self):
        r = EngineResult(success=True, result=MagicMock())
        assert r.success is True
        assert r.error is None

    def test_failure(self):
        r = EngineResult(success=False, error="Something went wrong")
        assert r.success is False
        assert r.error == "Something went wrong"

    def test_defaults(self):
        r = EngineResult(success=True)
        assert r.result is None
        assert r.fitness_state is None
        assert r.error is None


class TestAnalysisEngineInit:
    def test_default_ftp(self):
        engine = AnalysisEngine()
        assert engine._ftp == 250.0

    def test_custom_ftp(self):
        engine = AnalysisEngine(ftp=300.0)
        assert engine._ftp == 300.0

    def test_with_athlete_profile(self):
        profile = MagicMock()
        engine = AnalysisEngine(athlete_profile=profile)
        assert engine._athlete_profile == profile


class TestProcessRideSync:
    def test_success(self):
        engine = AnalysisEngine()
        ride = _ride()
        result = engine.process_ride_sync(ride)
        assert isinstance(result, EngineResult)
        assert result.success is True
        assert result.result is not None

    def test_result_contains_metrics(self):
        engine = AnalysisEngine()
        ride = _ride(duration_minutes=60, avg_speed_kmh=25)
        result = engine.process_ride_sync(ride)
        assert "fatigue_score" in result.result.metrics

    def test_error_handling(self):
        engine = AnalysisEngine()
        with patch.object(engine.pipeline, "run_sync", side_effect=RuntimeError("boom")):
            result = engine.process_ride_sync(_ride())
            assert result.success is False
            assert "boom" in result.error


class TestProcessRide:
    @pytest.mark.asyncio
    async def test_success(self):
        engine = AnalysisEngine()
        ride = _ride()
        result = await engine.process_ride(ride)
        assert isinstance(result, EngineResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_with_athlete_id(self):
        engine = AnalysisEngine()
        ride = _ride()
        result = await engine.process_ride(ride, athlete_id=1)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_error_handling(self):
        engine = AnalysisEngine()
        with patch.object(engine.pipeline, "run", side_effect=RuntimeError("boom")):
            result = await engine.process_ride(_ride())
            assert result.success is False


class TestProcessRidesBatch:
    @pytest.mark.asyncio
    async def test_batch(self):
        engine = AnalysisEngine()
        rides = [_ride(id=i) for i in range(3)]
        results = await engine.process_rides_batch(rides)
        assert len(results) == 3
        assert all(isinstance(r, EngineResult) for r in results)
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_batch_with_athlete(self):
        engine = AnalysisEngine()
        rides = [_ride(id=i) for i in range(2)]
        results = await engine.process_rides_batch(rides, athlete_id=1)
        assert len(results) == 2
