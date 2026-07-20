"""BikeMaster 2.0 - Fatigue Model (carico e fatica)."""

from __future__ import annotations

from typing import Optional

from ..models import AnalysisContext
from .base import Algorithm

__all__ = ["FatigueModel"]


class FatigueModel(Algorithm):
    """Stima il carico di fatica (0-10) e le ore di recupero necessarie.

    Formula: score = min(10, (duration·0.3 + intensity·0.3 + speed·0.2
             + elevation·0.1 + weight·0.1)·3)
    """

    name = "FatigueModel"
    formula = ("score = min(10, (duration·0.3 + intensity·0.3 + speed·0.2 "
               "+ elevation·0.1 + weight·0.1)·3)")
    description = "Stima il carico di fatica (0-10) e le ore di recupero necessarie."
    unit = "score"
    required_inputs = ["duration", "intensity", "speed", "elevation", "weight"]

    def _intensity_factor(self, ctx: AnalysisContext, avg_speed_kmh: float) -> float:
        """Calcola il fattore di intensita' da FC media (se disponibile) o da velocita'."""
        hrs = [p.heart_rate for p in ctx.activity.points if p.heart_rate is not None]
        if hrs and ctx.athlete.max_hr_bpm is not None:
            hr_avg = sum(hrs) / len(hrs)
            return min(hr_avg / ctx.athlete.max_hr_bpm.value, 1.0)
        return min(avg_speed_kmh / 30.0, 1.0)

    def _compute(self, ctx: AnalysisContext, extra: Optional[dict]) -> tuple[float, float, float]:
        """Calcola lo score di fatica (0-10) combinando duration, intensita', velocita' e elevation."""
        m = ctx.activity.metrics(ctx.transformer)
        dur_h = m["duration_s"] / 3600.0
        v_kmh = m["avg_speed_ms"] * 3.6
        intensity = self._intensity_factor(ctx, v_kmh)
        elev_factor = 1.0 + min((m["gain_m"] / max(m["distance_m"], 1)) / 20.0, 1.0) \
            if m["distance_m"] > 0 else 1.0
        weight_factor = ctx.athlete.weight_kg.value / 70.0

        duration_f = min(dur_h / 2.0, 3.0)
        score = min(
            (duration_f * 0.3 + intensity * 0.3 + min(v_kmh / 25.0, 2.0) * 0.2
             + elev_factor * 0.1 + weight_factor * 0.1) * 3.0,
            10.0,
        )
        precision = 0.8
        confidence = 0.75 if m["duration_s"] > 0 else 0.3
        if ctx.athlete.max_hr_bpm is not None:
            confidence = min(confidence + 0.05, 0.85)
        return score, precision, confidence

    def _recovery_hours(self, score: float) -> float:
        """Stima le ore di recupero necessarie in base allo score di fatica."""
        if score <= 3.0:
            return 8.0
        if score <= 5.0:
            return 16.0
        if score <= 7.0:
            return 24.0
        return 48.0

    def _extra_details(self, ctx: AnalysisContext, extra: Optional[dict]) -> dict:
        """Aggiunge intensita', recupero stimato e raccomandazione al risultato."""
        m = ctx.activity.metrics(ctx.transformer)
        v_kmh = m["avg_speed_ms"] * 3.6
        intensity = self._intensity_factor(ctx, v_kmh)
        score, _, _ = self._compute(ctx, extra)
        return {
            "intensity_factor": round(intensity, 3),
            "recovery_hours": self._recovery_hours(score),
            "recommendation": self._recommendation(score),
        }

    @staticmethod
    def _recommendation(score: float) -> str:
        """Raccomandazione testuale basata sul livello di fatica."""
        if score <= 2.0:
            return "Fatica minima"
        if score <= 4.0:
            return "Fatica lieve - giro tranquillo o riposo"
        if score <= 6.0:
            return "Fatica moderata - giorno di riposo consigliato"
        if score <= 8.0:
            return "Fatica alta - riposo necessario"
        return "Extreme fatigue - more rest days needed"

