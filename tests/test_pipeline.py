"""Tests for core pipeline module."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from bike_analyzer.core.models import GPSPoint, Ride
from bike_analyzer.core.pipeline import AnalysisPipeline, PipelineResult


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


class TestPipelineResult:
    def test_create(self):
        ride = _ride()
        result = PipelineResult(ride=ride)
        assert result.ride == ride
        assert result.route_statistics is None
        assert result.fitness_snapshot is None
        assert result.metrics is None

    def test_with_stats(self):
        ride = _ride()
        stats = MagicMock()
        result = PipelineResult(ride=ride, route_statistics=stats)
        assert result.route_statistics == stats

    def test_with_metrics(self):
        ride = _ride()
        metrics = {"fatigue_score": 5.0}
        result = PipelineResult(ride=ride, metrics=metrics)
        assert result.metrics == metrics


class TestAnalysisPipelineInit:
    def test_default_ftp(self):
        p = AnalysisPipeline()
        assert p.ftp == 250.0

    def test_custom_ftp(self):
        p = AnalysisPipeline(ftp=300.0)
        assert p.ftp == 300.0


class TestAnalysisPipelineRunSync:
    def test_no_gps_points(self):
        p = AnalysisPipeline()
        ride = _ride(gps_points=[])
        result = p.run_sync(ride)
        assert isinstance(result, PipelineResult)
        assert result.route_statistics is None

    def test_with_gps_points(self):
        p = AnalysisPipeline()
        points = [
            GPSPoint(lat=45.0, lon=9.0, timestamp=datetime(2024, 1, 1, 8, 0, 0, tzinfo=UTC)),
            GPSPoint(lat=45.01, lon=9.01, timestamp=datetime(2024, 1, 1, 8, 10, 0, tzinfo=UTC)),
        ]
        ride = _ride(gps_points=points)
        result = p.run_sync(ride)
        assert isinstance(result, PipelineResult)
        assert result.route_statistics is not None
        assert result.metrics is not None
        assert "fatigue_score" in result.metrics
        assert "calories" in result.metrics
        assert "performance_score" in result.metrics

    def test_metrics_content(self):
        p = AnalysisPipeline()
        ride = _ride(duration_minutes=60, avg_speed_kmh=25)
        result = p.run_sync(ride)
        assert isinstance(result.metrics["fatigue_score"], float)
        assert isinstance(result.metrics["calories"], float)

    def test_process_gps_called(self):
        p = AnalysisPipeline()
        with patch.object(p, "_process_gps", return_value=None):
            ride = _ride(gps_points=[])
            result = p.run_sync(ride)
            assert isinstance(result, PipelineResult)

    def test_returns_pipeline_result(self):
        p = AnalysisPipeline()
        ride = _ride()
        result = p.run_sync(ride)
        assert isinstance(result, PipelineResult)
