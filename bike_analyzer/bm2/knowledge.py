"""BikeMaster 2.0 - Knowledge Engine (numbers -> concepts).

Transforms raw algorithm results into understandable concepts,
e.g. "Challenging climb - requires high aerobic capacity". Does not calculate:
it classifies and explains.
"""

from __future__ import annotations

from dataclasses import dataclass

from .algorithms.base import ModelResult

__all__ = ["Insight", "KnowledgeEngine"]


@dataclass
class Insight:
    """Cycling concept generated from algorithm results.

    Attributes:
        concept: Short concept label (e.g. ``"Route: Challenging"``).
        detail: Numeric or descriptive detail.
        severity: Severity level (``"info"``, ``"note"``,
            ``"warning"``, ``"critical"``).
    """

    concept: str
    detail: str
    severity: str = "info"  # info | note | warning | critical

    def to_dict(self) -> dict:
        return {"concept": self.concept, "detail": self.detail, "severity": self.severity}


class KnowledgeEngine:
    """Transforms raw algorithm results into understandable insights.

    For each algorithm it produces an ``Insight`` that classifies and explains the
    result in natural language, with adaptive severity.

    Generated insights cover: route difficulty, fatigue, performance,
    recovery and nutrition.
    """

    def explain(self, results: dict[str, ModelResult]) -> list[Insight]:
        """Generates insights from all algorithm results.

        Args:
            results: Dictionary of algorithm_name -> ModelResult.

        Returns:
            List of ``Insight`` sorted by category (route, fatigue,
            performance, recovery, nutrition).
        """
        insights: list[Insight] = []
        insights += self._route_insights(results)
        insights += self._fatigue_insights(results)
        insights += self._performance_insights(results)
        insights += self._recovery_insights(results)
        insights += self._nutrition_insights(results)
        return insights

    def _get(self, results: dict[str, ModelResult], name: str) -> ModelResult | None:
        """Helper to extract a ModelResult by algorithm name.

        Args:
            results: Dictionary of results.
            name: Name of the algorithm to look up.

        Returns:
            ModelResult if found, otherwise None.
        """
        return results.get(name)

    def _route_insights(self, results: dict[str, ModelResult]) -> list[Insight]:
        """Generates insights on route difficulty.

        Reads the ``RouteDifficultyModel`` and assigns severity ``"warning"``
        if the category is ``"Challenging"`` or ``"Extreme"``.

        Args:
            results: Dictionary of algorithm results.

        Returns:
            List with one ``Insight`` or empty if the model is absent.
        """
        r = self._get(results, "RouteDifficultyModel")
        if not r:
            return []
        cat = r.details.get("category", "Unknown")
        sev = "info"
        if cat in ("Challenging", "Extreme"):
            sev = "warning"
        return [Insight(
            concept=f"Route: {cat}",
            detail=f"Difficulty {r.value:.0f}/100 - surface {r.details.get('surface')}",
            severity=sev,
        )]

    def _fatigue_insights(self, results: dict[str, ModelResult]) -> list[Insight]:
        """Generates insights on estimated fatigue level.

        Severity ``"warning"`` if fatigue >= 6/10.

        Args:
            results: Dictionary of algorithm results.

        Returns:
            List with one ``Insight`` or empty if the model is absent.
        """
        r = self._get(results, "FatigueModel")
        if not r:
            return []
        rec = r.details.get("recommendation", "")
        sev = "warning" if r.value >= 6 else "info"
        return [Insight(concept=f"Fatigue {r.value:.1f}/10", detail=rec, severity=sev)]

    def _performance_insights(self, results: dict[str, ModelResult]) -> list[Insight]:
        """Generates insights on athlete performance.

        Compares average speed with reference speed.

        Args:
            results: Dictionary of algorithm results.

        Returns:
            List with one ``Insight`` or empty if the model is absent.
        """
        r = self._get(results, "PerformanceModel")
        if not r:
            return []
        return [Insight(
            concept=f"Performance {r.value:.0f}/100",
            detail=f"Avg speed {r.details.get('avg_speed_kmh', 0):.1f} km/h "
                   f"(reference {r.details.get('reference_speed_kmh', 0):.0f})",
            severity="info",
        )]

    def _recovery_insights(self, results: dict[str, ModelResult]) -> list[Insight]:
        """Generates insights on recovery readiness.

        Severity ``"warning"`` if readiness < 40/100.

        Args:
            results: Dictionary of algorithm results.

        Returns:
            List with one ``Insight`` or empty if the model is absent.
        """
        r = self._get(results, "RecoveryModel")
        if not r:
            return []
        sev = "warning" if r.value < 40 else "info"
        return [Insight(
            concept=f"Readiness {r.value:.0f}/100",
            detail=f"Estimated recovery {r.details.get('recovery_hours', 0):.0f} h",
            severity=sev,
        )]

    def _nutrition_insights(self, results: dict[str, ModelResult]) -> list[Insight]:
        """Generates insights on estimated nutritional needs.

        Args:
            results: Dictionary of algorithm results.

        Returns:
            List with one ``Insight`` or empty if the model is absent.
        """
        r = self._get(results, "NutritionModel")
        if not r:
            return []
        d = r.details
        return [Insight(
            concept="Nutrition",
            detail=f"{d.get('carbs_g', 0):.0f} g carbs, "
                   f"{d.get('water_L', 0):.1f} L water, "
                   f"{d.get('protein_g', 0):.0f} g protein",
            severity="info",
        )]
