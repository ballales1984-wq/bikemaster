"""Compute Fitness State Vector from rides history.

The Fitness State Vector is the core of BikeMaster's training load monitoring,
combining ATL (acute fatigue), CTL (chronic fitness), and TSB (current form)
computed via EWMA over daily TSS values derived from the athlete's ride history.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from ....core.calculators import power, stress
from ....core.fitness_state import FitnessStateVector
from ....core.models import Ride


class FitnessStateEngine:
    """Engine for computing ATL/CTL/TSB from a sequence of rides.

    Aggregates daily TSS, computes EWMA-based fitness/fatigue curves,
    and derives trend indicators and recovery recommendations.
    """

    def __init__(self, stress_repo=None, ftp: float = 250.0):
        """Initialize the engine with an optional FTP threshold.

        Args:
            stress_repo: Optional repository for persisting fitness state.
            ftp: Functional Threshold Power in watts for TSS calculation.
        """
        self._stress_repo = stress_repo
        self.ftp = ftp

    def compute(self, rides: Sequence[Ride], athlete_id: int, rider_age: int = 35) -> FitnessStateVector:
        """Compute the full Fitness State Vector from ride history.

        Aggregates TSS per day, then computes EWMA(7) for ATL and EWMA(42)
        for CTL. TSB = CTL - ATL. Also derives 7-day and 30-day trends,
        risk indicators, and a recovery recommendation.

        Args:
            rides: Sequence of rides for the athlete (ordered by date).
            athlete_id: Owner athlete identifier.
            rider_age: Age in years for fatigue/recovery heuristics.

        Returns:
            FitnessStateVector with computed ATL, CTL, TSB, trends and recommendations.
        """
        now = date.today()
        window_7 = now - timedelta(days=7)
        window_30 = now - timedelta(days=30)

        ride_days: dict[str, float] = defaultdict(float)
        for r in rides:
            day = r.date[:10] if r.date and len(r.date) >= 10 else "unknown"
            # Keep the max TSS per day (multiple rides same day = hardest counts)
            ride_days[day] = max(ride_days[day], power.training_stress_score(r, self.ftp))

        days_sorted = sorted(ride_days.items())
        tss_series = [v for _, v in days_sorted]
        # ATL: 7-day EWMA = acute fatigue
        atl_series = [stress.ewma(tss_series[: i + 1], tau_days=7.0) for i in range(len(tss_series))]
        # CTL: 42-day EWMA = chronic fitness
        ctl_series = [stress.ewma(tss_series[: i + 1], tau_days=42.0) for i in range(len(tss_series))]
        latest = (ctl_series[-1], atl_series[-1]) if ctl_series else (0.0, 0.0)
        ctl, atl = latest
        tsb = round(ctl - atl, 1)
        weekly_tss = sum(v for d, v in days_sorted if d >= str(window_7))
        monthly_tss = sum(v for d, v in days_sorted if d >= str(window_30))
        trend_7d = self._trend(tss_series[-7:]) if len(tss_series) >= 2 else "stable"
        trend_30d = self._trend(tss_series[-30:]) if len(tss_series) >= 2 else "stable"
        risk_indicators: list[str] = []
        recommendation = "Maintain current routine"
        # Overtraining risk: acute load > 130% of chronic + negative TSB
        if atl > ctl * 1.3 and tsb < -20:
            risk_indicators.append("overtraining_risk")
            recommendation = "Reduce volume immediately"
        if tsb > 15:
            recommendation = "Good freshness - race or hard effort possible"
        if tsb > 5 and atl < ctl * 1.1:
            recommendation = "Ready for hard effort"
        return FitnessStateVector(
            athlete_id=athlete_id,
            computed_at=datetime.now(UTC),
            atl=atl,
            ctl=ctl,
            tsb=tsb,
            fitness=round(ctl, 1),
            fatigue=round(atl, 1),
            form=round(tsb, 1),
            weekly_tss=round(weekly_tss, 1),
            monthly_tss=round(monthly_tss, 1),
            trend_7d=trend_7d,
            trend_30d=trend_30d,
            risk_indicators=risk_indicators,
            recommendation=recommendation,
        )

    @staticmethod
    def _trend(series: list[float]) -> str:
        """Classify the trend of a numeric series as increasing/stable/decreasing.

        Compares the average of the second half vs the first half.
        A ratio > 1.1 = increasing, < 0.9 = decreasing.

        Args:
            series: Ordered numeric values (e.g. TSS over days).

        Returns:
            One of: ``"increasing"``, ``"stable"``, ``"decreasing"``.
        """
        if len(series) < 2:
            return "stable"
        mid = len(series) // 2
        first = sum(series[:mid]) / max(mid, 1)
        second = sum(series[mid:]) / max(len(series) - mid, 1)
        ratio = second / first if first > 0 else 1.0
        if ratio > 1.1:
            return "increasing"
        if ratio < 0.9:
            return "decreasing"
        return "stable"
