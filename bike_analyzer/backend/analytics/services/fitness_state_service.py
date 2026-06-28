"""Compute Fitness State Vector from rides history."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import date, datetime, timedelta

from ....core.calculators import power, stress
from ....core.fitness_state import FitnessStateVector
from ....core.models import Ride


class FitnessStateEngine:
    def __init__(self, stress_repo=None, ftp: float = 250.0):
        self._stress_repo = stress_repo
        self.ftp = ftp

    def compute(self, rides: Sequence[Ride], athlete_id: int, rider_age: int = 35) -> FitnessStateVector:
        now = date.today()
        window_7 = now - timedelta(days=7)
        window_30 = now - timedelta(days=30)

        ride_days: dict[str, float] = defaultdict(float)
        for r in rides:
            day = r.date[:10] if r.date and len(r.date) >= 10 else "unknown"
            ride_days[day] = max(ride_days[day], power.training_stress_score(r, self.ftp))

        days_sorted = sorted(ride_days.items())
        tss_series = [v for _, v in days_sorted]
        atl_series = [stress.ewma(tss_series[: i + 1], tau_days=7.0) for i in range(len(tss_series))]
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
        if atl > ctl * 1.3 and tsb < -20:
            risk_indicators.append("overtraining_risk")
            recommendation = "Reduce volume immediately"
        if tsb > 15:
            recommendation = "Good freshness - race or hard effort possible"
        if tsb > 5 and atl < ctl * 1.1:
            recommendation = "Ready for hard effort"
        return FitnessStateVector(
            athlete_id=athlete_id,
            computed_at=datetime.now(),
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
