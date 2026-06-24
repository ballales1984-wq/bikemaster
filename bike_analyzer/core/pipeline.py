"""Core processing pipeline: ingestion → processing → analytics → fitness state."""

from __future__ import annotations

from dataclasses import dataclass

from .models import Ride, RouteStatistics


@dataclass
class PipelineResult:
    ride: Ride
    route_statistics: RouteStatistics | None = None
    fitness_snapshot: dict | None = None
    metrics: dict | None = None


class AnalysisPipeline:
    def __init__(self, ftp: float = 250.0):
        self.ftp = ftp

    async def run(self, ride: Ride) -> PipelineResult:
        stats = self._process_gps(ride)
        metrics = self._compute_metrics(ride)
        return PipelineResult(ride=ride, route_statistics=stats, metrics=metrics)

    def run_sync(self, ride: Ride) -> PipelineResult:
        stats = self._process_gps(ride)
        metrics = self._compute_metrics(ride)
        return PipelineResult(ride=ride, route_statistics=stats, metrics=metrics)

    def _process_gps(self, ride: Ride) -> RouteStatistics | None:
        if not ride.gps_points:
            return None
        from bike_analyzer.backend.processing.processing import process_route
        cleaned, stats = process_route(ride.gps_points)
        ride.gps_points = cleaned
        return stats

    def _compute_metrics(self, ride: Ride) -> dict:
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