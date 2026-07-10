"""BikeMaster 2.0 - Knowledge Engine (numeri -> concetti).

Trasforma i risultati grezzi degli algoritmi in concetti comprensibili,
es. "Salita impegnativa - richiede alta capacità aerobica". Non calcola:
classifica e spiega.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .algorithms.base import ModelResult

__all__ = ["Insight", "KnowledgeEngine"]


@dataclass
class Insight:
    concept: str
    detail: str
    severity: str = "info"  # info | note | warning | critical

    def to_dict(self) -> dict:
        return {"concept": self.concept, "detail": self.detail, "severity": self.severity}


class KnowledgeEngine:
    def explain(self, results: dict[str, ModelResult]) -> list[Insight]:
        insights: list[Insight] = []
        insights += self._route_insights(results)
        insights += self._fatigue_insights(results)
        insights += self._performance_insights(results)
        insights += self._recovery_insights(results)
        insights += self._nutrition_insights(results)
        return insights

    def _get(self, results: dict[str, ModelResult], name: str) -> Optional[ModelResult]:
        return results.get(name)

    def _route_insights(self, results: dict[str, ModelResult]) -> list[Insight]:
        r = self._get(results, "RouteDifficultyModel")
        if not r:
            return []
        cat = r.details.get("category", "Sconosciuta")
        sev = "info"
        if cat in ("Impegnativo", "Estremo"):
            sev = "warning"
        return [Insight(
            concept=f"Percorso: {cat}",
            detail=f"Difficoltà {r.value:.0f}/100 - superficie {r.details.get('surface')}",
            severity=sev,
        )]

    def _fatigue_insights(self, results: dict[str, ModelResult]) -> list[Insight]:
        r = self._get(results, "FatigueModel")
        if not r:
            return []
        rec = r.details.get("recommendation", "")
        sev = "warning" if r.value >= 6 else "info"
        return [Insight(concept=f"Fatica {r.value:.1f}/10", detail=rec, severity=sev)]

    def _performance_insights(self, results: dict[str, ModelResult]) -> list[Insight]:
        r = self._get(results, "PerformanceModel")
        if not r:
            return []
        return [Insight(
            concept=f"Prestazione {r.value:.0f}/100",
            detail=f"Velocità media {r.details.get('avg_speed_kmh', 0):.1f} km/h "
                   f"(riferimento {r.details.get('reference_speed_kmh', 0):.0f})",
            severity="info",
        )]

    def _recovery_insights(self, results: dict[str, ModelResult]) -> list[Insight]:
        r = self._get(results, "RecoveryModel")
        if not r:
            return []
        sev = "warning" if r.value < 40 else "info"
        return [Insight(
            concept=f"Prontenza {r.value:.0f}/100",
            detail=f"Recupero stimato {r.details.get('recovery_hours', 0):.0f} h",
            severity=sev,
        )]

    def _nutrition_insights(self, results: dict[str, ModelResult]) -> list[Insight]:
        r = self._get(results, "NutritionModel")
        if not r:
            return []
        d = r.details
        return [Insight(
            concept="Nutrizione",
            detail=f"{d.get('carbs_g', 0):.0f} g carboidrati, "
                   f"{d.get('water_L', 0):.1f} L acqua, "
                   f"{d.get('protein_g', 0):.0f} g proteine",
            severity="info",
        )]
