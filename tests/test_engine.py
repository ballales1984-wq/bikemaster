"""Tests for core engine module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bike_analyzer.core.engine import AnalysisEngine, EngineResult
from bike_analyzer.core.fitness_state import FitnessStateVector
from bike_analyzer.core.models import Ride
from bike_analyzer.core.pipeline import PipelineResult
from bike_analyzer.core.fitness_state import FitnessStateVector


def _ride(**kwargs):
    defaults = {
        "id": 1,
        "athlete_id": 1,
        "date": "2024-06-15",
        "distance_km": 25.0,
        "duration_minutes": 60.0,
        "avg_speed_kmh": 25.0,
        "weight_kg": 70.0,
        "calories": 600.0,
        "heart_rate_avg": 150.0,
        "elevation_gain_m": 200.0,
        "gps_points": [],
    }
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


class TestProcessRideBatchHistorical:
    @pytest.mark.asyncio
    async def test_batch_loads_history_and_processes(self):
        engine = AnalysisEngine()
        ride = _ride(id=10)
        historical = [_ride(id=i, date=f"2024-05-{10+i:02d}") for i in range(5)]
        with patch.object(engine, "_load_historical_rides", return_value=historical), \
             patch.object(engine, "_persist_fitness_state"):
            results = await engine.process_rides_batch([ride], athlete_id=1, session_factory=object())
        assert len(results) == 1
        assert results[0].success is True


class TestLoadHistoricalRides:
    @pytest.mark.asyncio
    async def test_load_history_success(self):
        engine = AnalysisEngine()
        fake_rides = [
            {"id": 1, "date": "2024-05-01", "distance_km": 20.0, "athlete_id": 1}
        ]
        mock_fn = AsyncMock(return_value=fake_rides)
        with patch("bike_analyzer.backend.db.async_db.get_rides_by_athlete_async", mock_fn):
            result = await engine._load_historical_rides(1, lambda: None)
        assert len(result) == 1
        assert result[0].id == 1

    @pytest.mark.asyncio
    async def test_load_history_failure_returns_empty(self):
        engine = AnalysisEngine()
        mock_fn = AsyncMock(side_effect=RuntimeError("db down"))
        with patch("bike_analyzer.backend.db.async_db.get_rides_by_athlete_async", mock_fn):
            result = await engine._load_historical_rides(1, lambda: None)
        assert result == []


class TestUpdateFitnessState:
    @pytest.mark.asyncio
    async def test_without_historical_rides(self):
        engine = AnalysisEngine(ftp=250.0)
        ride = _ride(duration_minutes=60)
        state = await engine._update_fitness_state(ride, athlete_id=1, session_factory=None)
        assert state is not None
        assert state.athlete_id == 1
        assert state.atl > 0
        assert state.ctl > 0

    @pytest.mark.asyncio
    async def test_with_historical_rides(self):
        engine = AnalysisEngine(ftp=250.0)
        historical = [
            _ride(id=i, date="2024-05-01", duration_minutes=60)
            for i in range(3)
        ]
        ride = _ride(id=10, date="2024-05-02", duration_minutes=60)
        state = await engine._update_fitness_state(ride, athlete_id=1, session_factory=None, historical_rides=historical)
        assert state is not None
        assert state.athlete_id == 1

    @pytest.mark.asyncio
    async def test_no_athlete_id_returns_none(self):
        engine = AnalysisEngine()
        ride = _ride()
        state = await engine._update_fitness_state(ride, athlete_id=None, session_factory=None)
        assert state is None


class TestPersistFitnessState:
    @pytest.mark.asyncio
    async def test_persist_when_repository_unavailable(self):
        engine = AnalysisEngine()
        state = FitnessStateVector(
            athlete_id=1,
            computed_at=datetime.now(UTC),
            atl=10.0,
            ctl=20.0,
            tsb=-10.0,
            fitness=20.0,
            fatigue=10.0,
            form=-10.0,
            recovery_hours_needed=20.0,
            weekly_tss=100.0,
            monthly_tss=400.0,
            trend_7d="stable",
            trend_30d="stable",
        )
        with patch("bike_analyzer.core.engine.FitnessStateRepository", None):
            await engine._persist_fitness_state(state, lambda: None)

    @pytest.mark.asyncio
    async def test_persist_error_is_swallowed(self):
        engine = AnalysisEngine()
        state = FitnessStateVector(
            athlete_id=1,
            computed_at=datetime.now(UTC),
            atl=10.0,
            ctl=20.0,
            tsb=-10.0,
            fitness=20.0,
            fatigue=10.0,
            form=-10.0,
            recovery_hours_needed=20.0,
            weekly_tss=100.0,
            monthly_tss=400.0,
            trend_7d="stable",
            trend_30d="stable",
        )
        fake_repo = AsyncMock()
        fake_repo.save.side_effect = RuntimeError("db error")
        with patch("bike_analyzer.core.engine.FitnessStateRepository", return_value=fake_repo):
            await engine._persist_fitness_state(state, lambda: None)
