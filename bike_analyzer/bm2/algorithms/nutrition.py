"""BikeMaster 2.0 - Nutrition Model (nutrition for the activity)."""

from __future__ import annotations

from typing import Optional

from ..models import AnalysisContext
from .base import Algorithm
from .energy import EnergyModel
from .fatigue import FatigueModel

__all__ = ["NutritionModel"]


class NutritionModel(Algorithm):
    """Stima carboidrati, idratazione e proteine per l'attivita'.

    Formula: carb = intensita'·60 g/h · ore; acqua = 0.6 L/h · ore;
             proteine = 0.3 g/kg (post-attivita')
    """

    name = "NutritionModel"
    formula = ("carb = intensity·60 g/h · ore; acqua = 0.6 L/h · ore; "
               "proteine = 0.3 g/kg (post)")
    description = "Estimates carbs, hydration and protein for the activity."
    unit = "g"
    required_inputs = ["duration", "intensity", "body_mass"]

    def _compute(self, ctx: AnalysisContext, extra: Optional[dict]) -> tuple[float, float, float]:
        """Calcola i carboidrati totali (g) in base a duration e intensita'."""
        m = ctx.activity.metrics(ctx.transformer)
        dur_h = m["duration_s"] / 3600.0
        if dur_h <= 0:
            return 0.0, 0.0, 0.3
        fatigue = FatigueModel().run(ctx)
        intensity = fatigue.details.get("intensity_factor", 0.5)
        carbs_per_h = 30.0 + intensity * 30.0  # 30-60 g/h
        carbs = carbs_per_h * dur_h
        precision = carbs * 0.2
        confidence = 0.7 if dur_h > 0 else 0.3
        return carbs, precision, confidence

    def _extra_details(self, ctx: AnalysisContext, extra: Optional[dict]) -> dict:
        """Aggiunge proteine, acqua, kcal e duration al risultato."""
        m = ctx.activity.metrics(ctx.transformer)
        dur_h = m["duration_s"] / 3600.0
        weight = ctx.athlete.weight_kg.value
        energy = EnergyModel().run(ctx)
        carbs, _, _ = self._compute(ctx, extra)
        return {
            "carbs_g": round(carbs, 1),
            "protein_g": round(0.3 * weight, 1),
            "water_L": round(0.6 * dur_h, 2),
            "kcal": round(energy.value, 0),
            "duration_h": round(dur_h, 2),
        }

