"""Core processing engine - main entry point for ride analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Sequence

from .models import Ride
from .pipeline import AnalysisPipeline, PipelineResult


@dataclass
class EngineResult:
    success: bool
    result: PipelineResult | None = None
    error: str | None = None


class AnalysisEngine:
    def __init__(self, ftp: float = 250.0):
        self.pipeline = AnalysisPipeline(ftp=ftp)

    async def process_ride(self, ride: Ride) -> EngineResult:
        try:
            result = await self.pipeline.run(ride)
            return EngineResult(success=True, result=result)
        except Exception as exc:
            return EngineResult(success=False, error=str(exc))

    def process_ride_sync(self, ride: Ride) -> EngineResult:
        try:
            result = self.pipeline.run_sync(ride)
            return EngineResult(success=True, result=result)
        except Exception as exc:
            return EngineResult(success=False, error=str(exc))

    async def process_rides_batch(self, rides: Sequence[Ride]) -> list[EngineResult]:
        results = []
        for ride in rides:
            results.append(await self.process_ride(ride))
        return results
