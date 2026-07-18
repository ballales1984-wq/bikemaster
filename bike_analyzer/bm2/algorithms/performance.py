"""BikeMaster 2.0 - Performance Model (indice di prestazione normalizzato)."""

from __future__ import annotations

from typing import Optional

from ..models import AnalysisContext
from .base import Algorithm

__all__ = ["PerformanceModel"]

REFERENCE_SPEED_KMH = {
    "Beginner": 18.0,
    "Intermediate": 24.0,
    "Advanced": 30.0,
    "Elite": 36.0,
}


class PerformanceModel(Algorithm):
    """Indice di prestazione normalizzato sull'esperienza dell'atleta.

    Formula: indice = clamp(v_media_kmh / v_riferimento(experience) · 100, 0, 120)
    """

    name = "PerformanceModel"
    formula = "indice = clamp(v_media_kmh / v_riferimento(experience) · 100, 0, 120)"
    description = "Indice di prestazione normalizzato sull'esperienza dell'atleta."
    unit = "score"
    required_inputs = ["velocità_media", "experience_level"]

    def _compute(self, ctx: AnalysisContext, extra: Optional[dict]) -> tuple[float, float, float]:
        """Calcola l'indice di prestazione normalizzato per livello di esperienza."""
        m = ctx.activity.metrics(ctx.transformer)
        v_kmh = (m["avg_speed_ms"] * 3.6) if m["avg_speed_ms"] else 0.0
        ref = REFERENCE_SPEED_KMH.get(ctx.athlete.experience_level, 24.0)
        index = max(0.0, min(v_kmh / ref * 100.0, 120.0))
        precision = 6.0
        confidence = 0.7 if v_kmh > 0 else 0.3
        if ctx.athlete.experience_level in ("Advanced", "Elite"):
            confidence = min(confidence + 0.05, 0.85)
        return index, precision, confidence

    def _extra_details(self, ctx: AnalysisContext, extra: Optional[dict]) -> dict:
        """Restituisce velocita' media, riferimento e livello esperienza."""
        m = ctx.activity.metrics(ctx.transformer)
        return {
            "avg_speed_kmh": m["avg_speed_ms"] * 3.6,
            "reference_speed_kmh": REFERENCE_SPEED_KMH.get(ctx.athlete.experience_level, 24.0),
            "experience_level": ctx.athlete.experience_level,
        }
