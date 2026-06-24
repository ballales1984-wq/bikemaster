"""Tests for RideAnalysisService."""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch

from bike_analyzer.backend.analytics.services.ride_analysis_service import (
    RideAnalysisService,
)


def _make_ride():
    from bike_analyzer.core.models import Ride, GPSPoint
    ts = datetime(2024, 6, 15, 10, 0, 0, tzinfo=UTC)
    points = [
        GPSPoint(lat=45.0, lon=9.0, altitude=100.0, speed=10.0, timestamp=ts),
        GPSPoint(lat=45.01, lon=9.01, altitude=105.0, speed=12.0, timestamp=ts),
    ]
    return Ride(
        id=1,
        athlete_id=1,
        date="2024-06-15",
        distance_km=25.0,
        duration_minutes=60,
        avg_speed_kmh=25.0,
        calories=600,
        gps_points=points,
    )


class TestRideAnalysisService:
    def test_constructor_defaults(self):
        svc = RideAnalysisService()
        assert svc.pipeline is not None
        assert svc.fitness_engine is not None

    def test_constructor_with_ftp(self):
        svc = RideAnalysisService(ftp=280.0)
        assert svc.pipeline.ftp == 280.0
        assert svc.fitness_engine.ftp == 280.0

    @pytest.mark.asyncio
    async def test_analyze_returns_dict(self):
        svc = RideAnalysisService()
        ride = _make_ride()
        with patch.object(svc.pipeline, 'run', new_callable=AsyncMock) as mock_run:
            from bike_analyzer.core.pipeline import PipelineResult
            from bike_analyzer.core.models import RouteStatistics
            pr = PipelineResult(
                ride=ride,
                metrics={"fatigue_score": 3.0},
                route_statistics=RouteStatistics(
                    total_distance_m=25000,
                    total_duration_s=3600,
                    avg_speed_km_h=25.0,
                    max_speed_km_h=35.0,
                    total_elevation_gain_m=150,
                    total_elevation_loss_m=50,
                    segment_count=3,
                    pause_count=1,
                ),
            )
            mock_run.return_value = pr
            result = await svc.analyze(ride)
            assert "ride" in result
            assert "metrics" in result
            assert "route_statistics" in result
            assert result["route_statistics"]["total_distance_m"] == 25000

    @pytest.mark.asyncio
    async def test_analyze_without_route_statistics(self):
        svc = RideAnalysisService()
        ride = _make_ride()
        with patch.object(svc.pipeline, 'run', new_callable=AsyncMock) as mock_run:
            from bike_analyzer.core.pipeline import PipelineResult
            pr = PipelineResult(ride=ride, metrics={"fatigue_score": 2.0}, route_statistics=None)
            mock_run.return_value = pr
            result = await svc.analyze(ride)
            assert "ride" in result
            assert "metrics" in result
            assert "route_statistics" not in result

    def test_analyze_sync_returns_dict(self):
        svc = RideAnalysisService()
        ride = _make_ride()
        with patch.object(svc.pipeline, 'run_sync') as mock_run:
            from bike_analyzer.core.pipeline import PipelineResult
            pr = PipelineResult(ride=ride, metrics={"fatigue_score": 3.5}, route_statistics=None)
            mock_run.return_value = pr
            result = svc.analyze_sync(ride)
            assert result["ride"]["id"] == 1
            assert result["metrics"]["fatigue_score"] == 3.5

    @pytest.mark.asyncio
    async def test_compute_fitness_state(self):
        svc = RideAnalysisService(ftp=250.0)
        ride = _make_ride()
        result = await svc.compute_fitness_state([ride], athlete_id=1)
        from bike_analyzer.core.fitness_state import FitnessStateVector
        assert isinstance(result, FitnessStateVector)
        assert result.athlete_id == 1

    @pytest.mark.asyncio
    async def test_compute_fitness_state_empty_rides(self):
        svc = RideAnalysisService(ftp=250.0)
        result = await svc.compute_fitness_state([], athlete_id=1)
        from bike_analyzer.core.fitness_state import FitnessStateVector
        assert isinstance(result, FitnessStateVector)
        assert result.athlete_id == 1
