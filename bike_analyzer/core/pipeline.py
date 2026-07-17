"""Core processing pipeline: ingestion → processing → analytics → fitness state."""

from __future__ import annotations

from dataclasses import dataclass

from .models import Ride, RouteStatistics


@dataclass
class PipelineResult:
    """Result container for a single ride analysis run."""
    ride: Ride
    route_statistics: RouteStatistics | None = None
    fitness_snapshot: dict | None = None
    metrics: dict | None = None


class AnalysisPipeline:
    """Processing pipeline that turns a raw ride into cleaned stats and metrics.

    Steps:
    1. GPS cleaning and route statistics (``_process_gps``)
    2. Metrics computation: fatigue, calories, performance, power (``_compute_metrics``)
    """

    def __init__(self, ftp: float = 250.0):
        """Create the pipeline with the athlete's FTP in watts."""
        self.ftp = ftp

    async def run(self, ride: Ride) -> PipelineResult:
        """Execute the pipeline asynchronously for a ride."""
        stats = self._process_gps(ride)
        metrics = self._compute_metrics(ride)
        return PipelineResult(ride=ride, route_statistics=stats, metrics=metrics)

    def run_sync(self, ride: Ride) -> PipelineResult:
        """Execute the pipeline synchronously for a ride."""
        stats = self._process_gps(ride)
        metrics = self._compute_metrics(ride)
        return PipelineResult(ride=ride, route_statistics=stats, metrics=metrics)

    def _process_gps(self, ride: Ride) -> RouteStatistics | None:
        """Clean GPS points and compute route statistics."""
        if not ride.gps_points:
            return None
        from bike_analyzer.backend.processing.processing import process_route

        cleaned, stats = process_route(ride.gps_points)
        ride.gps_points = cleaned
        return stats

    def _compute_metrics(self, ride: Ride) -> dict:
        """Compute fatigue, recovery, calories, performance, efficiency, and TSS."""
        from .calculators import calories, fatigue, performance, power

        fatigue_score = fatigue.calculate_fatigue_score(ride)
        return {
            "fatigue_score": round(fatigue_score, 1),
            "recovery_hours": round(fatigue.estimate_recovery_hours(fatigue_score), 1),
            "calories": round(calories.estimate(ride), 0),
            "performance_score": performance.performance_score(ride),
            "efficiency_score": performance.efficiency_score(ride),
            "tss": power.training_stress_score(ride, self.ftp),
        }
