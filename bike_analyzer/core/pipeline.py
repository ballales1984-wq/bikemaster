"""Core processing pipeline: ingestion → processing → analytics → fitness state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from .models import GPSPoint, Ride, RouteStatistics


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
        from bike_analyzer.backend.analytics.calculators.fatigue import calculate_fatigue_score, estimate_recovery_hours
        from bike_analyzer.backend.analytics.calculators.calories import estimate
        from bike_analyzer.backend.analytics.calculators.performance import performance_score, efficiency_score
        from bike_analyzer.backend.analytics.calculators.power import training_stress_score

        fatigue = calculate_fatigue_score(ride)
        return {
            "fatigue_score": round(fatigue, 1),
            "recovery_hours": round(estimate_recovery_hours(fatigue), 1),
            "calories": round(estimate(ride), 0),
            "performance_score": performance_score(ride),
            "efficiency_score": efficiency_score(ride),
            "tss": training_stress_score(ride, self.ftp),
        }
