"""High-level ride analysis service.

Orchestrates the full analysis of a ride including processing,
metrics calculation, and optional fitness state computation.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from ....core.models import Ride
from ....core.pipeline import AnalysisPipeline
from .fitness_state_service import FitnessStateEngine

if TYPE_CHECKING:
    from ....core.fitness_state import FitnessStateVector


class RideAnalysisService:
    def __init__(self, ftp: float = 250.0):
        self.pipeline = AnalysisPipeline(ftp=ftp)
        self.fitness_engine = FitnessStateEngine(ftp=ftp)

    async def analyze(self, ride: Ride) -> dict:
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
        return data

    def analyze_sync(self, ride: Ride) -> dict:
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
        return data

    async def compute_fitness_state(
        self, rides: Sequence[Ride], athlete_id: int
    ) -> FitnessStateVector:
        return self.fitness_engine.compute(rides, athlete_id)
