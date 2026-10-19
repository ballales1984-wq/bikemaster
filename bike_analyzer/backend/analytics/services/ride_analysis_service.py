"""High-level ride analysis service.

Orchestrates the full analysis of a ride including processing,
metrics calculation, and optional fitness state computation.
"""

from __future__ import annotations

import time as _time
from collections.abc import Sequence
from typing import TYPE_CHECKING

from ....core.models import Ride
from ....core.pipeline import AnalysisPipeline
from .fitness_state_service import FitnessStateEngine

if TYPE_CHECKING:
    from ....core.fitness_state import FitnessStateVector


class RideAnalysisService:
    """Service layer for ride analysis - wraps the core pipeline with monitoring.

    Provides both async and sync analysis paths, recording Prometheus
    metrics for ride analysis duration and fatigue scores.
    """

    def __init__(self, ftp: float = 250.0):
        """Initialize the service with an optional FTP threshold.

        Args:
            ftp: Functional Threshold Power in watts, used for TSS calculation.
        """
        self.pipeline = AnalysisPipeline(ftp=ftp)
        self.fitness_engine = FitnessStateEngine(ftp=ftp)

    async def analyze(self, ride: Ride) -> dict:
        """Run the full analysis pipeline for a single ride asynchronously.

        Processes GPS data, computes route statistics and aggregated metrics
        (fatigue, recovery, calories, performance, TSS), and records
        Prometheus metrics for observability.

        Args:
            ride: Cycling activity to analyze.

        Returns:
            Dictionary with keys: ``ride``, ``metrics``, ``route_statistics``.
        """
        from ...monitoring import record_fatigue_score, record_ride_analysis_duration

        start = _time.perf_counter()
        try:
            pipeline_result = await self.pipeline.run(ride)
            data = {
                "ride": pipeline_result.ride.to_dict(),
                "metrics": pipeline_result.metrics,
            }
            if pipeline_result.route_statistics:
                data["route_statistics"] = {
                    "total_distance_m": pipeline_result.route_statistics.total_distance_m,
                    "total_duration_s": pipeline_result.route_statistics.total_duration_s,
                    "avg_speed_km_h": pipeline_result.route_statistics.avg_speed_km_h,
                    "max_speed_km_h": pipeline_result.route_statistics.max_speed_km_h,
                    "total_elevation_gain_m": pipeline_result.route_statistics.total_elevation_gain_m,
                    "total_elevation_loss_m": pipeline_result.route_statistics.total_elevation_loss_m,
                    "segment_count": pipeline_result.route_statistics.segment_count,
                    "pause_count": pipeline_result.route_statistics.pause_count,
                }
            if pipeline_result.metrics and "fatigue_score" in pipeline_result.metrics:
                record_fatigue_score(pipeline_result.metrics["fatigue_score"])
            return data
        finally:
            record_ride_analysis_duration(_time.perf_counter() - start)

    def analyze_sync(self, ride: Ride) -> dict:
        """Run the full analysis pipeline for a single ride synchronously.

        Same as ``analyze`` but blocks until completion. Useful for
        CLI tools and background tasks that don't need async.

        Args:
            ride: Cycling activity to analyze.

        Returns:
            Dictionary with keys: ``ride``, ``metrics``, ``route_statistics``.
        """
        from ...monitoring import record_fatigue_score, record_ride_analysis_duration

        start = _time.perf_counter()
        try:
            pipeline_result = self.pipeline.run_sync(ride)
            data = {
                "ride": pipeline_result.ride.to_dict(),
                "metrics": pipeline_result.metrics,
            }
            if pipeline_result.route_statistics:
                data["route_statistics"] = {
                    "total_distance_m": pipeline_result.route_statistics.total_distance_m,
                    "total_duration_s": pipeline_result.route_statistics.total_duration_s,
                    "avg_speed_km_h": pipeline_result.route_statistics.avg_speed_km_h,
                    "max_speed_km_h": pipeline_result.route_statistics.max_speed_km_h,
                    "total_elevation_gain_m": pipeline_result.route_statistics.total_elevation_gain_m,
                    "total_elevation_loss_m": pipeline_result.route_statistics.total_elevation_loss_m,
                    "segment_count": pipeline_result.route_statistics.segment_count,
                    "pause_count": pipeline_result.route_statistics.pause_count,
                }
            if pipeline_result.metrics and "fatigue_score" in pipeline_result.metrics:
                record_fatigue_score(pipeline_result.metrics["fatigue_score"])
            return data
        finally:
            record_ride_analysis_duration(_time.perf_counter() - start)

    async def compute_fitness_state(self, rides: Sequence[Ride], athlete_id: int) -> FitnessStateVector:
        """Compute the Fitness State Vector (ATL/CTL/TSB) from a ride history.

        Args:
            rides: Sequence of historical rides for the athlete.
            athlete_id: Owner athlete identifier.

        Returns:
            FitnessStateVector with computed ATL, CTL, TSB, trends and recommendations.
        """
        return self.fitness_engine.compute(rides, athlete_id)
