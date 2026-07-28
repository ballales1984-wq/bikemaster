"""BikeMaster 2.0 - Training Load Model (TSS/CTL/ATL/TSB)."""

from __future__ import annotations

from typing import Optional

from ..models import AnalysisContext
from .base import Algorithm

__all__ = ["TrainingLoadModel"]


class TrainingLoadModel(Algorithm):
    """Stima carico di allenamento (TSS/CTL/ATL/TSB) da storico attivita'.

    Formula: TSS = (t·NP·IF) / (FTP·3600) · 100;
             CTL = EMA_42(TSS); ATL = EMA_7(TSS); TSB = CTL - ATL
    """

    name = "TrainingLoadModel"
    formula = ("TSS = (t·NP·IF) / (FTP·3600) · 100; "
               "CTL = EMA_42(TSS); ATL = EMA_7(TSS); TSB = CTL - ATL")
    description = "Estimates training load (TSS/CTL/ATL/TSB) from activity history."
    unit = "score"
    required_inputs = ["ftp", "storico_attivita"]

    @staticmethod
    def _estimate_tss(duration_s: float, avg_power_w: float, ftp_w: float) -> float:
        """Calcola il Training Stress Score (TSS) per una singola attivita'."""
        if ftp_w <= 0 or duration_s <= 0:
            return 0.0
        if_ = min(avg_power_w / ftp_w, 1.5)
        np = avg_power_w * (1.0 + 0.05 * (if_ - 1.0))
        return (duration_s * np * if_) / (ftp_w * 3600.0) * 100.0

    @staticmethod
    def _ema(values: list[float], alpha: float) -> list[float]:
        """Exponential Moving Average (EMA) pesata con coefficiente alpha."""
        if not values:
            return []
        out = [values[0]]
        for v in values[1:]:
            out.append(alpha * v + (1.0 - alpha) * out[-1])
        return out

    def _compute(self, ctx: AnalysisContext, extra: Optional[dict]) -> tuple[float, float, float]:
        """Calcola TSB come differenza tra CTL (42 giorni) e ATL (7 giorni)."""
        extra = extra or {}
        ftp = ctx.athlete.ftp_w.value if ctx.athlete.ftp_w else 0.0
        history = extra.get("activity_history", [])
        tss_history = self._build_tss_history(ctx, history, ftp)

        if not tss_history:
            precision = max(5.0, len(tss_history) * 0.5)
            confidence = 0.3
            return 0.0, precision, confidence

        alpha_ctl = 2.0 / (42.0 + 1.0)
        alpha_atl = 2.0 / (7.0 + 1.0)
        ctl_series = self._ema(tss_history, alpha_ctl)
        atl_series = self._ema(tss_history, alpha_atl)
        ctl = ctl_series[-1] if ctl_series else 0.0
        atl = atl_series[-1] if atl_series else 0.0
        tsb = ctl - atl
        precision = max(ctl * 0.08, 3.0)
        confidence = 0.8 if len(history) >= 7 else (0.6 if len(history) >= 1 else 0.3)
        self._last_details = {
            "ctl": ctl, "atl": atl, "tsb": tsb, "tss_history_count": len(tss_history),
        }
        return tsb, precision, confidence

    def _build_tss_history(self, ctx: AnalysisContext, history: list[dict], ftp: float) -> list[float]:
        """Costruisce la serie storica di TSS da storico esterno o dai punti dell'attivita'."""
        if history:
            tss_history = []
            for act in history:
                dur = float(act.get("duration_s", act.get("duration_h", 0.0) * 3600.0))
                avg_pwr = float(act.get("avg_power_w", ftp * 0.75 if ftp > 0 else 150.0))
                tss_history.append(self._estimate_tss(dur, avg_pwr, ftp))
            return tss_history

        m = ctx.activity.metrics(ctx.transformer)
        pts = [p for p in ctx.activity.points if p.power is not None]
        avg_power = sum(p.power for p in pts) / len(pts) if pts else ftp * 0.7
        return [self._estimate_tss(m["duration_s"], avg_power, ftp)]

    def _extra_details(self, ctx: AnalysisContext, extra: Optional[dict]) -> dict:
        """Restituisce CTL, ATL, TSB e conteggio storico TSS."""
        if hasattr(self, "_last_details") and self._last_details:
            return dict(self._last_details)
        extra = extra or {}
        history = extra.get("activity_history", [])
        ftp = ctx.athlete.ftp_w.value if ctx.athlete.ftp_w else 0.0
        tss_history = self._build_tss_history(ctx, history, ftp)
        if not tss_history:
            return {"ctl": 0.0, "atl": 0.0, "tsb": 0.0, "tss_history_count": 0}
        ctl_series = self._ema(tss_history, 2.0 / 43.0)
        atl_series = self._ema(tss_history, 2.0 / 8.0)
        ctl = ctl_series[-1] if ctl_series else 0.0
        atl = atl_series[-1] if atl_series else 0.0
        return {
            "ctl": round(ctl, 1),
            "atl": round(atl, 1),
            "tsb": round(ctl - atl, 1),
            "tss_history_count": len(tss_history),
        }

