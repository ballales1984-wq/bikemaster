"""Tests for core pipeline and engine integration."""

from __future__ import annotations

from datetime import UTC, datetime

from bike_analyzer.core.engine import AnalysisEngine
from bike_analyzer.core.models import GPSPoint, Ride
from bike_analyzer.core.pipeline import AnalysisPipeline


def _make_ride(gps_points: list[GPSPoint] | None = None) -> Ride:
    return Ride(
        id=1,
        athlete_id=1,
        date="2026-06-14T10:00:00+00:00",
        distance_km=40.0,
        duration_minutes=120.0,
        avg_speed_kmh=20.0,
        weight_kg=75.0,
        calories=800.0,
        heart_rate_avg=155.0,
        elevation_gain_m=400.0,
        gps_points=gps_points,
    )


def _make_point(lat: float, lon: float, minutes_offset: float = 0.0, speed: float | None = 20.0) -> GPSPoint:
    base = datetime(2026, 6, 14, 10, 0, 0, tzinfo=UTC)
    ts = base.replace(minute=base.minute + int(minutes_offset))
    return GPSPoint(
        lat=lat,
        lon=lon,
        timestamp=ts,
        speed=speed,
    )


def _make_gps_series() -> list[GPSPoint]:
    base_lat, base_lon = 45.0, 9.0
    return [_make_point(base_lat + i * 0.001, base_lon + i * 0.001, minutes_offset=i) for i in range(5)]


class TestAnalysisPipeline:
    def test_run_returns_pipeline_result(self):
        pipeline = AnalysisPipeline(ftp=250.0)
        ride = _make_ride()
        result = pipeline.run_sync(ride)
        assert result.ride is ride
        assert result.metrics is not None
        assert "fatigue_score" in result.metrics
        assert "tss" in result.metrics

    def test_metrics_keys(self):
        pipeline = AnalysisPipeline()
        ride = _make_ride()
        result = pipeline.run_sync(ride)
        expected = {"fatigue_score", "recovery_hours", "calories", "performance_score", "efficiency_score", "tss"}
        assert expected.issubset(result.metrics.keys())

    def test_route_statistics_with_gps(self):
        pipeline = AnalysisPipeline()
        points = _make_gps_series()
        ride = _make_ride(gps_points=points)
        result = pipeline.run_sync(ride)
        assert result.route_statistics is not None
        assert result.route_statistics.total_distance_m > 0

    def test_no_route_statistics_without_gps(self):
        pipeline = AnalysisPipeline()
        ride = _make_ride(gps_points=None)
        result = pipeline.run_sync(ride)
        assert result.route_statistics is None


class TestAnalysisEngine:
    def test_success_on_valid_ride(self):
        engine = AnalysisEngine()
        ride = _make_ride()
        result = engine.process_ride_sync(ride)
        assert result.success is True
        assert result.result is not None

    def test_zero_ride_produces_zero_metrics(self):
        engine = AnalysisEngine()
        ride = Ride(date="", duration_minutes=0)
        result = engine.process_ride_sync(ride)
        assert result.success is True
        assert result.result.metrics["tss"] == 0.0


class TestFitnessStateComputation:
    def _make_rides(self) -> list[Ride]:
        base = datetime(2026, 5, 1, tzinfo=UTC)
        return [
            Ride(
                id=i,
                athlete_id=1,
                date=base.replace(day=1 + i).isoformat(),
                distance_km=30.0 + i * 5,
                duration_minutes=90.0 + i * 10,
                avg_speed_kmh=20.0,
                weight_kg=75.0,
                calories=600.0 + i * 50,
                heart_rate_avg=150.0,
                elevation_gain_m=200.0 + i * 50,
            )
            for i in range(5)
        ]

    def test_compute_returns_vector(self):
        engine = AnalysisEngine()
        rides = self._make_rides()
        result = engine.process_ride_sync(rides[0])
        assert result.success

    def test_fitness_vector_fields(self):
        from bike_analyzer.backend.analytics.services.fitness_state_service import FitnessStateEngine

        svc = FitnessStateEngine(ftp=250.0)
        fv = svc.compute(self._make_rides(), athlete_id=1)
        assert fv.athlete_id == 1
        assert fv.ctl >= 0
        assert fv.atl >= 0
        assert isinstance(fv.is_overtraining_risk, bool)
        assert isinstance(fv.is_fresh, bool)
        assert isinstance(fv.is_ready_for_hard_effort, bool)
