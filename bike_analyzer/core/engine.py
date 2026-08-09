"""Core processing engine - main entry point for ride analysis.

Production-grade engine with:
- Fitness State Vector integration (CTL/ATL/TSB tracking via FitnessStateEngine)
- Repository pattern for data access
- Multi-tenant isolation support
- Async-first architecture
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from .fitness_state import FitnessStateVector
from .models import AthleteProfile, Ride
from .pipeline import AnalysisPipeline, PipelineResult

try:
    from bike_analyzer.backend.analytics.repositories.fitness_state_repository import (
        FitnessStateRepository,
    )
except ImportError:
    FitnessStateRepository = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class EngineResult:
    """Result of a single ride analysis run."""
    success: bool
    result: PipelineResult | None = None
    fitness_state: FitnessStateVector | None = None
    error: str | None = None


class AnalysisEngine:
    """Main analysis engine orchestrating ride processing and fitness state tracking.

    This is the single entry point for all ride analysis operations.
    Integrates with repositories for persistence and computes fitness state vectors
    using EWMA-based calculations.
    """

    def __init__(self, ftp: float = 250.0, athlete_profile: AthleteProfile | None = None):
        """Initialize the engine with an optional FTP and athlete profile."""
        self.pipeline = AnalysisPipeline(ftp=ftp)
        self._ftp = ftp
        self._athlete_profile = athlete_profile

    async def process_ride(
        self,
        ride: Ride,
        athlete_id: int | None = None,
        session_factory=None,
        historical_rides: Sequence[Ride] | None = None,
    ) -> EngineResult:
        """Run the analysis pipeline for a single ride and update fitness state."""
        try:
            result = await self.pipeline.run(ride)
            fitness_state = await self._update_fitness_state(ride, athlete_id, session_factory, historical_rides)
            return EngineResult(success=True, result=result, fitness_state=fitness_state)
        except Exception as exc:
            logger.exception("Failed to process ride")
            return EngineResult(success=False, error=str(exc))

    def process_ride_sync(self, ride: Ride) -> EngineResult:
        """Run the analysis pipeline synchronously for a single ride."""
        try:
            result = self.pipeline.run_sync(ride)
            return EngineResult(success=True, result=result)
        except Exception as exc:
            logger.exception("Failed to process ride (sync)")
            return EngineResult(success=False, error=str(exc))

    async def process_rides_batch(
        self, rides: Sequence[Ride], athlete_id: int | None = None, session_factory=None, tenant_id: int | None = None
    ) -> list[EngineResult]:
        """Process multiple rides, loading historical context when available."""
        results = []
        historical_rides: list[Ride] = []
        if athlete_id is not None and session_factory is not None:
            historical_rides = await self._load_historical_rides(athlete_id, session_factory, tenant_id=tenant_id)
        for i, ride in enumerate(rides):
            context_rides = list(historical_rides) + list(rides[: i + 1])
            results.append(await self.process_ride(ride, athlete_id, session_factory, context_rides))
        return results

    async def _load_historical_rides(
        self, athlete_id: int, session_factory, tenant_id: int | None = None, limit: int = 90
    ) -> list[Ride]:
        """Load up to ``limit`` recent rides for an athlete from the async DB."""
        try:
            from ..backend.db.async_db import get_rides_by_athlete_async

            raw_rides = await get_rides_by_athlete_async(athlete_id, tenant_id=tenant_id, limit=limit)
            return [Ride(**r) for r in raw_rides]
        except Exception as exc:
            logger.warning("Could not load historical rides for athlete %s: %s", athlete_id, exc)
            return []

    async def _update_fitness_state(
        self,
        ride: Ride,
        athlete_id: int | None,
        session_factory,
        historical_rides: Sequence[Ride] | None = None,
    ) -> FitnessStateVector | None:
        """Compute ATL/CTL/TSB from ride TSS and optionally persist the state."""
        if athlete_id is None:
            return None

        from .calculators import power, stress

        ftp = self._ftp
        if self._athlete_profile and getattr(self._athlete_profile, "ftp_watts", None):
            ftp = self._athlete_profile.ftp_watts

        tss = 0.0
        atl = 0.0
        ctl = 0.0

        if historical_rides:
            ride_days: dict[str, float] = {}
            for r in historical_rides:
                day = r.date[:10] if r.date and len(r.date) >= 10 else "unknown"
                ride_days[day] = ride_days.get(day, 0.0) + power.training_stress_score(r, ftp)

            if ride_days:
                dates = sorted(ride_days.keys())
                start = datetime.strptime(dates[0], "%Y-%m-%d").date()
                end = datetime.strptime(dates[-1], "%Y-%m-%d").date()
                current = start
                full_series: list[float] = []
                while current <= end:
                    key = current.isoformat()
                    full_series.append(ride_days.get(key, 0.0))
                    current += timedelta(days=1)
                tss_series = full_series
            else:
                tss_series = []

            tss = tss_series[-1] if tss_series else 0.0
            atl = stress.ewma(tss_series, tau_days=7.0) if tss_series else 0.0
            ctl = stress.ewma(tss_series, tau_days=42.0) if tss_series else 0.0
        else:
            tss = power.training_stress_score(ride, ftp)
            atl = min(tss * 1.5, 100.0)
            ctl = max(tss * 0.8, 10.0)
            tss_series = [tss]

        tsb = round(ctl - atl, 1)
        weekly_tss = sum(tss_series[-7:]) if tss_series else 0.0
        monthly_tss = sum(tss_series[-30:]) if tss_series else 0.0
        fitness_state = FitnessStateVector(
            athlete_id=athlete_id,
            computed_at=datetime.now(UTC),
            atl=atl,
            ctl=ctl,
            tsb=tsb,
            fitness=round(ctl, 1),
            fatigue=round(atl, 1),
            form=tsb,
            recovery_hours_needed=tss * 2,
            weekly_tss=weekly_tss,
            monthly_tss=monthly_tss,
            trend_7d="stable",
            trend_30d="stable",
        )

        if session_factory:
            await self._persist_fitness_state(fitness_state, session_factory)

        return fitness_state

    async def _persist_fitness_state(self, state: FitnessStateVector, session_factory) -> None:
        """Persist a fitness state vector via the repository when available."""
        if FitnessStateRepository is None:
            raise RuntimeError("FitnessStateRepository unavailable — cannot persist fitness state")
        try:
            repo = FitnessStateRepository(session_factory=session_factory)
            await repo.save(state.to_dict())
        except Exception as exc:
            raise RuntimeError(f"Could not persist fitness state: {exc}") from exc
