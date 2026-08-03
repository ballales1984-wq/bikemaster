"""Athlete State Service — orchestrates the computation of the athlete's current state.

This service combines:
- FitnessStateEngine (ATL/CTL/TSB, trends)
- fatigue.py (per-ride fatigue score)
- training_stress.py (TSS estimation)
- training_load.py (Banister model)
- load_manager/ (chronic load, ACWR, safety, trends)

The result is a rich ``AthleteState`` model ready for consumption by the
Training Plan, Adaptation Engine, and Proactive Assistant.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ...models.models import AthleteProfile, Ride
from ..services.fitness_state_service import FitnessStateEngine
from .calculators import (
    average_fatigue_score,
    build_daily_tss_series,
    build_risk_indicators,
    compute_readiness,
    compute_recommendation,
    compute_risk_level,
    estimate_recovery_hours,
)
from .models import AthleteState


class AthleteStateService:
    """Compute and expose the current physiological state of an athlete."""

    def __init__(
        self,
        ftp: float = 250.0,
        rider_age: int = 35,
        stress_repo: object = None,
    ):
        self.ftp = ftp
        self.rider_age = rider_age
        self._fitness_engine = FitnessStateEngine(stress_repo=stress_repo, ftp=ftp)

    async def calculate_current_state(
        self,
        athlete_id: int,
        rides: Sequence[Ride],
        athlete_profile: AthleteProfile | None = None,
    ) -> AthleteState:
        """Calculate the current athlete state from ride history.

        Args:
            athlete_id: The athlete identifier.
            rides: Sequence of Ride objects (history + recent).
            athlete_profile: Optional profile with FTP, age, etc.

        Returns:
            A fully populated ``AthleteState`` model.
        """
        ftp = self.ftp
        rider_age = self.rider_age
        if athlete_profile and getattr(athlete_profile, "ftp_watts", None):
            ftp = athlete_profile.ftp_watts
        if athlete_profile and getattr(athlete_profile, "age", None):
            rider_age = athlete_profile.age

        rides_list = list(rides)

        # 1. Fitness State Vector (ATL/CTL/TSB, trends, weekly/monthly TSS)
        fitness_vector = self._fitness_engine.compute(rides_list, athlete_id, rider_age)

        # 2. Training Load (Banister model) — fallback / cross-check
        from ..training_load import calculate_atl_ctl_tsb

        load_history = calculate_atl_ctl_tsb(rides_list, ftp)
        load_history[-1] if load_history else None

        # 3. Fatigue scores
        recent_rides = sorted(rides_list, key=lambda r: r.date or "")[-7:]
        avg_fatigue, max_fatigue = average_fatigue_score(recent_rides, rider_age)

        # 4. Chronic load + ACWR via load_manager
        daily_tss = build_daily_tss_series(rides_list, ftp)
        chronic = self._compute_chronic_load(daily_tss)

        # 5. Trends via load_manager
        self._compute_ctl_trend(daily_tss)

        # 6. Derived metrics
        acwr = (chronic.acwr if chronic and chronic.acwr is not None else 1.0)
        atl = fitness_vector.atl
        ctl = fitness_vector.ctl
        tsb = fitness_vector.tsb

        readiness = compute_readiness(
            atl=atl,
            ctl=ctl,
            tsb=tsb,
            fatigue_score=max_fatigue,
            acwr=acwr,
        )
        recovery_hours = estimate_recovery_hours(max_fatigue, tsb)
        risk_level = compute_risk_level(
            atl=atl,
            ctl=ctl,
            tsb=tsb,
            acwr=acwr,
            fatigue_score=max_fatigue,
        )
        recommendation = compute_recommendation(
            atl=atl,
            ctl=ctl,
            tsb=tsb,
            fatigue_score=max_fatigue,
            readiness=readiness,
        )
        risk_indicators = build_risk_indicators(
            atl=atl,
            ctl=ctl,
            tsb=tsb,
            acwr=acwr,
            fatigue_score=max_fatigue,
            readiness=readiness,
        )

        # 7. Build the canonical model
        return AthleteState(
            athlete_id=athlete_id,
            computed_at=datetime.now(),
            atl=round(atl, 1),
            ctl=round(ctl, 1),
            tsb=round(tsb, 1),
            fitness=round(ctl, 1),
            fatigue=round(atl, 1),
            form=round(tsb, 1),
            fatigue_score=round(avg_fatigue, 1),
            readiness=round(readiness, 1),
            recovery_hours_needed=recovery_hours,
            acwr=round(acwr, 3),
            weekly_tss=round(fitness_vector.weekly_tss, 1),
            monthly_tss=round(fitness_vector.monthly_tss, 1),
            trend_7d=fitness_vector.trend_7d,
            trend_30d=fitness_vector.trend_30d,
            risk_indicators=risk_indicators,
            recommendation=recommendation,
            risk_level=risk_level,
        )

    def _compute_chronic_load(self, daily_tss: list[tuple[str, float]]) -> Any:
        from ..load_manager.chronic_load import ChronicLoadManager
        from ..load_manager.config import DEFAULT_CONFIG

        manager = ChronicLoadManager(config=DEFAULT_CONFIG)
        return manager.current(daily_tss)

    def _compute_ctl_trend(self, daily_tss: list[tuple[str, float]]) -> Any:
        from ..load_manager.chronic_load import ChronicLoadManager
        from ..load_manager.config import DEFAULT_CONFIG
        from ..load_manager.trend_analyzer import TrendAnalyzer

        manager = ChronicLoadManager(config=DEFAULT_CONFIG)
        series = manager.compute_series(daily_tss)
        if not series:
            return None
        ctl_series = [s.ctl for s in series]
        analyzer = TrendAnalyzer()
        return analyzer.ctl_trend(ctl_series)


__all__ = ["AthleteStateService"]
