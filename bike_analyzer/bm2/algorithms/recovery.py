"""BikeMaster 2.0 - Recovery Model (recupero e readiness)."""

from __future__ import annotations

from typing import Optional

from ..models import AnalysisContext
from .base import Algorithm
from .fatigue import FatigueModel

__all__ = ["RecoveryModel"]


class RecoveryModel(Algorithm):
    """Stima la prontenza (readiness 0-100) da fatica, sonno e HRV.

    Formula: readiness = clamp(100 - fatica·6 - sonno_carenza·4 + hrv_bonus, 0, 100)
    """

    name = "RecoveryModel"
    formula = "readiness = clamp(100 - fatica·6 - sonno_carenza·4 + hrv_bonus, 0, 100)"
    description = "Stima la prontenza (readiness 0-100) da fatica, sonno e HRV."
    unit = "score"
    required_inputs = ["fatica", "sonno_ore", "hrv"]

    def _compute(self, ctx: AnalysisContext, extra: Optional[dict]) -> tuple[float, float, float]:
        """Calcola la readiness combinando FatigueModel, deficit sonno e bonus HRV."""
        extra = extra or {}
        fatigue_result = FatigueModel().run(ctx)
        fatigue = fatigue_result.value
        sleep = float(extra.get("sleep_hours", 8.0))
        hrv = float(extra.get("hrv_rmssd", 0.0))
        baseline_hrv = float(extra.get("baseline_hrv", 0.0)) or hrv

        sleep_deficit = max(0.0, 8.0 - sleep)
        hrv_bonus = 0.0
        if baseline_hrv > 0:
            hrv_bonus = max(-10.0, min(10.0, (hrv - baseline_hrv) / baseline_hrv * 20.0))

        readiness = max(0.0, min(100.0 - fatigue * 6.0 - sleep_deficit * 4.0 + hrv_bonus, 100.0))
        precision = 8.0
        confidence = 0.7 if (sleep > 0 or hrv > 0) else 0.4
        return readiness, precision, confidence

    def _extra_details(self, ctx: AnalysisContext, extra: Optional[dict]) -> dict:
        """Restituisce fatica, recupero stimato, sonno e HRV utilizzati."""
        extra = extra or {}
        fatigue_result = FatigueModel().run(ctx)
        readiness, _, _ = self._compute(ctx, extra)
        return {
            "fatigue_score": round(fatigue_result.value, 2),
            "recovery_hours": fatigue_result.details.get("recovery_hours", 0.0),
            "sleep_hours": float(extra.get("sleep_hours", 8.0)),
            "hrv_rmssd": float(extra.get("hrv_rmssd", 0.0)),
        }
