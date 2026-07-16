"""Load Manager — Chronic/Acute Load service (CTL/ATL/TSB + ACWR).

Spec (agent): service producing ``ChronicLoad``. Pure and deterministic.
Does NOT mutate existing ride TSS values (constraint #2).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from .calculators import calculate_acwr, calculate_ewma
from .config import DEFAULT_CONFIG, LoadManagerConfig
from .models import ChronicLoad


def _iso(d: str) -> date:
    return datetime.fromisoformat(d[:10]).date() if len(d) >= 10 else datetime.fromisoformat(d).date()


class ChronicLoadManager:
    """Compute CTL/ATL/TSB time series and ACWR from a TSS series."""

    def __init__(self, config: LoadManagerConfig = DEFAULT_CONFIG) -> None:
        self.config = config

    def compute_series(self, dated_tss: list[tuple[str, float]]) -> list[ChronicLoad]:
        if not dated_tss:
            return []

        dated_tss = sorted(dated_tss, key=lambda x: _iso(x[0]))
        dates = [_iso(d) for d, _ in dated_tss]

        # Build a continuous daily calendar so gaps are represented as 0 TSS.
        start, end = dates[0], dates[-1]
        day_cursor = start
        daily: list[tuple[date, float]] = []
        tss_by_day = {_iso(d): t for d, t in dated_tss}
        while day_cursor <= end:
            daily.append((day_cursor, float(tss_by_day.get(day_cursor, 0.0))))
            day_cursor += timedelta(days=1)

        tss_values = [v for _, v in daily]
        ctl_series = calculate_ewma(tss_values, self.config.tau_ctl)
        atl_series = calculate_ewma(tss_values, self.config.tau_atl)

        result: list[ChronicLoad] = []
        for i, (d, tss) in enumerate(daily):
            ctl, atl = ctl_series[i], atl_series[i]
            tsb = round(ctl - atl, 1)
            acwr = self._acwr_at(daily, i)
            result.append(
                ChronicLoad(
                    date=d.isoformat(),
                    ctl=round(ctl, 1),
                    atl=round(atl, 1),
                    tsb=tsb,
                    tss=round(tss, 1),
                    acwr=acwr,
                )
            )
        return result

    def _acwr_at(self, daily: list[tuple[date, float]], index: int) -> Optional[float]:
        sc = self.config.acwr_short_days
        lc = self.config.acwr_long_days
        if index < sc - 1:
            return None
        short = [v for _, v in daily[index - sc + 1: index + 1]]
        long_start = max(0, index - lc + 1)
        long = [v for _, v in daily[long_start: index + 1]]
        return calculate_acwr(short, long)

    def current(self, dated_tss: list[tuple[str, float]]) -> Optional[ChronicLoad]:
        series = self.compute_series(dated_tss)
        return series[-1] if series else None


__all__ = ["ChronicLoadManager"]
