"""BikeMaster 2.0 - Route Difficulty Model (difficoltà del percorso)."""

from __future__ import annotations

from typing import Optional

from ..models import AnalysisContext
from .base import Algorithm

__all__ = ["RouteDifficultyModel"]

ROUGHNESS_FACTOR = {"asphalt": 1.0, "gravel": 1.25, "dirt": 1.5, "trail": 1.8}


class RouteDifficultyModel(Algorithm):
    """Stima la difficolta' del percorso (0-100) rispetto alla capacita' dell'atleta.

    Formula: difficolta' = clamp(100 · (0.3·norm(distanza) + 0.3·norm(dislivello)
             + 0.25·norm(pendenza) + 0.15·rugosita') / capacita', 0, 100)
    """

    name = "RouteDifficultyModel"
    formula = ("difficoltà = clamp(100 · (0.3·norm(distanza) + 0.3·norm(dislivello) "
               "+ 0.25·norm(pendenza) + 0.15·rugosità) / capacità, 0, 100)")
    description = "Stima la difficoltà del percorso (0-100) rispetto alla capacità dell'atleta."
    unit = "score"
    required_inputs = ["distanza", "dislivello", "pendenza", "rugosità", "capacità_atleta"]

    def _compute(self, ctx: AnalysisContext, extra: Optional[dict]) -> tuple[float, float, float]:
        """Calcola il punteggio di difficolta' normalizzato per livello atleta."""
        m = ctx.activity.metrics(ctx.transformer)
        dist_km = m["distance_m"] / 1000.0
        gain_m = m["gain_m"]
        slope = m["avg_slope_percent"]

        norm_dist = min(dist_km / 100.0, 1.0)
        norm_gain = min(gain_m / 2000.0, 1.0)
        norm_slope = min(abs(slope) / 12.0, 1.0)
        rough = ROUGHNESS_FACTOR.get(ctx.world.surface, 1.0)

        raw = (0.3 * norm_dist + 0.3 * norm_gain + 0.25 * norm_slope + 0.15 * (rough - 1.0))
        # capacità: atleti esperti gestiscono percorsi più difficili
        cap = {"Beginner": 1.3, "Intermediate": 1.0, "Advanced": 0.8, "Elite": 0.65}.get(
            ctx.athlete.experience_level, 1.0)
        difficulty = max(0.0, min(100.0 * raw / cap, 100.0))
        precision = 5.0
        confidence = 0.8 if m["distance_m"] > 0 else 0.3
        return difficulty, precision, confidence

    def _category(self, score: float) -> str:
        """Classifica il punteggio in categoria testuale (Facile/Moderato/Impegnativo/Estremo)."""
        if score < 20:
            return "Facile"
        if score < 45:
            return "Moderato"
        if score < 70:
            return "Impegnativo"
        return "Estremo"

    def _extra_details(self, ctx: AnalysisContext, extra: Optional[dict]) -> dict:
        """Restituisce categoria e superficie del percorso."""
        score, _, _ = self._compute(ctx, extra)
        return {"category": self._category(score), "surface": ctx.world.surface}
