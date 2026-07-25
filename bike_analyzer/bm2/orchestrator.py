"""BikeMaster 2.0 - AI Orchestrator (the digital guide).

Does not calculate: it decides *which* agents and *which* algorithms to use based on the
question, assembles the context, and returns results + concepts + explanation.

Improvements over the base version:
    * robust question -> model routing (weighted keywords + IT synonyms),
      exposed as configurable via ``_select_models`` / constructor;
    * confidence scoring on the answer and ambiguous question handling
      ("tell me everything" -> all models);
    * ``explain_answer`` method that returns readable text in Italian;
    * reliable "what if" delta extraction (uses ``parse_override_from_text``:
      supports "weight -5 kg", "bike -1 kg", "+2% slope", "cda 0.3").
"""

from __future__ import annotations

from typing import Optional

from .algorithms import (
    ALL_ALGORITHMS, Algorithm, EnergyModel, FatigueModel, ModelResult,
    MovementModel, NutritionModel, PerformanceModel, RecoveryModel,
    RouteDifficultyModel, TrainingLoadModel, MetabolismModel,
)
from .knowledge import Insight, KnowledgeEngine
from .models import AnalysisContext, Athlete, Bike, Activity, WorldObject
from .simulation import ScenarioOverride, SimulationEngine, parse_override_from_text
from .transformer import TransformerEngine
from .agents import AthleteAgent, EnvironmentAgent, GPSAgent, MetabolismAgent, SensorAgent

__all__ = ["AIOrchestrator", "OrchestratorAnswer"]


# -- question -> model mapping (configurable) --------------------------------
# Each model has a {keyword: weight} dictionary. The weight discriminates
# weak/strong matches and orders the most relevant models.
DEFAULT_MODEL_KEYWORDS: dict[str, dict[str, float]] = {
    "EnergyModel": {
        "energy": 1.0, "calorie": 1.0, "calories": 1.0, "consumption": 1.0,
        "kcal": 1.0, "burn": 1.0, "expenditure": 1.0,
        "spent": 0.7, "spends": 0.7,
    },
    "NutritionModel": {
        "nutrition": 1.0, "eat": 1.0, "hydrat": 1.0, "hydrate": 1.0,
        "carb": 1.0, "food": 0.9, "drink": 0.9, "protein": 0.9,
        "sugar": 0.8, "supplement": 0.8,
    },
    "RouteDifficultyModel": {
        "difficult": 1.0, "difficulty": 1.0,
        "route": 1.0, "ride": 0.9, "track": 0.9,
        "climb": 1.0, "climbs": 1.0, "ascend": 0.8, "elevation": 1.0,
        "slope": 1.0, "gradient": 1.0,
    },
    "FatigueModel": {
        "fatigue": 1.0, "tired": 1.0, "tiredness": 0.9, "fatigued": 1.0,
        "exhaustion": 1.0, "effort": 0.8, "breakdown": 1.0,
    },
    "RecoveryModel": {
        "recovery": 1.0, "rest": 1.0, "resting": 0.9, "sleep": 0.9,
        "sleeping": 0.9, "recovery": 1.0, "regenerate": 1.0,
    },
    "MovementModel": {
        "movement": 1.0, "speed": 1.0,
        "pace": 1.0, "cadence": 0.9, "pedaling": 0.9, "motion": 0.8,
    },
    "PerformanceModel": {
        "performance": 1.0, "improve": 0.9,
        "efficiency": 0.9, "power": 0.8, "yield": 0.9,
        "ftp": 0.9, "improving": 0.8,
    },
    "PowerModel": {
        "power": 1.0, "watt": 1.0, "power": 1.0, "ftp": 0.6,
    },
    "TrainingLoadModel": {
        "load": 1.0, "training": 0.9, "workout": 1.0,
        "stress": 0.8, "ctl": 0.7, "tsb": 0.7,
    },
    "MetabolismModel": {
        "metabolism": 1.0, "metabolico": 1.0,
        "bmr": 1.0, "basal": 0.9, "tdee": 1.0,
        "calorie": 0.9, "calories": 0.9, "kcal": 0.9,
        "intake": 0.8, "food": 0.8, "diet": 0.8,
        "weight": 0.7, "fat": 0.7, "body_fat": 0.8,
        "energy_balance": 1.0, "bilancio": 0.9,
        "neat": 1.0, "eat": 0.9, "climb_bonus": 0.8,
    },
}

# Words signaling an "open" question -> use all models.
DEFAULT_AMBIGUOUS_KEYWORDS: frozenset[str] = frozenset({
    "everything", "complete", "general", "summary", "overview",
    "recap", "full analysis", "tell me everything", "explain everything",
})

# Keywords that trigger "what if" simulation.
_SIMULATION_KEYWORDS: tuple[str, ...] = (
    "if ", "what if", "simulate", "hypothes", "hypothesize",
    "se ", "simula", "ipotizz", "quanto risparmio", "come cambia",
)

# Minimum score threshold for a model to be considered relevant.
DEFAULT_ROUTE_THRESHOLD: float = 0.5


class AIOrchestrator:
    """The digital guide: decides which algorithms to use, assembles context, and explains results."""

    def __init__(self, transformer: Optional[TransformerEngine] = None,
                 model_keywords: Optional[dict[str, dict[str, float]]] = None,
                 ambiguous_keywords: Optional[frozenset[str]] = None,
                 route_threshold: float = DEFAULT_ROUTE_THRESHOLD) -> None:
        """Initialize the orchestrator with agents, keyword maps, and routing threshold."""
        self.t = transformer or TransformerEngine()
        self.gps = GPSAgent(self.t)
        self.athlete_agent = AthleteAgent(self.t)
        self.env_agent = EnvironmentAgent(self.t)
        self.sensor_agent = SensorAgent(self.t)
        self.metabolism_agent = MetabolismAgent(self.t)
        self.knowledge = KnowledgeEngine()

        self.model_keywords = model_keywords or DEFAULT_MODEL_KEYWORDS
        self.ambiguous_keywords = ambiguous_keywords or DEFAULT_AMBIGUOUS_KEYWORDS
        self.route_threshold = route_threshold

    # -- context assembly -------------------------------------------
    def build_context(self, raw: dict) -> AnalysisContext:
        """Build the full AnalysisContext from raw data (athlete, bike, GPS, world)."""
        athlete = self.athlete_agent.collect(raw.get("athlete", {}))
        bike = Bike.from_raw(raw.get("bike", {}), self.t)
        activity = self.gps.collect(raw.get("gps_points", []), raw.get("title", ""))
        if raw.get("sensors"):
            activity = self.sensor_agent.enrich_points(activity, raw["sensors"])
        world = self.env_agent.collect(raw.get("world", {}))
        return AnalysisContext(athlete=athlete, activity=activity, bike=bike,
                               world=world, transformer=self.t)

    # -- question -> model routing -------------------------------------
    def _is_simulation(self, question: str) -> bool:
        """Check if the question contains 'what if' simulation keywords."""
        q = question.lower()
        return any(k in q for k in _SIMULATION_KEYWORDS)

    def _is_ambiguous(self, question: str) -> bool:
        """Check if the question is open/ambiguous (e.g. 'tell me everything')."""
        q = question.lower()
        return any(k in q for k in self.ambiguous_keywords)

    def _select_models(self, question: str,
                       keywords: Optional[dict[str, dict[str, float]]] = None,
                       threshold: Optional[float] = None
                       ) -> list[type[Algorithm]]:
        """Map the question to relevant models via keyword scoring.

        The mapping is configurable: ``keywords`` overrides the default map
        (for tests or customizations), ``threshold`` the minimum score.
        Ambiguous questions or those without relevant match return all
        models (fallback "tell me everything").
        """
        kw_map = keywords if keywords is not None else self.model_keywords
        thr = threshold if threshold is not None else self.route_threshold
        q = question.lower()

        if self._is_ambiguous(q):
            return list(ALL_ALGORITHMS)

        scores: dict[str, float] = {}
        for model_name, kws in kw_map.items():
            score = 0.0
            for word, weight in kws.items():
                if word in q:
                    score += weight
            if score > 0:
                scores[model_name] = score

        if not scores:
            return list(ALL_ALGORITHMS)

        selected = [m for m, s in scores.items() if s >= thr]
        if not selected:
            selected = list(scores.keys())

        # maintain canonical order of ALL_ALGORITHMS for stability
        ordered = [a for a in ALL_ALGORITHMS if a.name in selected]
        return ordered

    # -- confidence scoring on response -------------------------------
    @staticmethod
    def _score_confidence(results: dict[str, ModelResult],
                          ambiguous: bool) -> float:
        """Calculate weighted average confidence on the response."""
        if not results:
            return 0.0
        avg = sum(r.confidence for r in results.values()) / len(results)
        # an open question (all models) has slightly reduced confidence
        # because results are less targeted to the request.
        return max(0.0, min(1.0, avg * (0.9 if ambiguous else 1.0)))

    # -- response --------------------------------------------------------
    def answer(self, question: str, raw: dict, extra: Optional[dict] = None) -> dict:
        """Answers a question by running selected models or a simulation."""
        ctx = self.build_context(raw)
        results: dict[str, ModelResult] = {}
        sim = None
        ambiguous = False

        if self._is_simulation(question):
            sim = self._run_simulation(ctx, question, extra)
        else:
            models = self._select_models(question)
            ambiguous = len(models) == len(ALL_ALGORITHMS)
            for algo_cls in models:
                results[algo_cls.name] = algo_cls().run(ctx, extra)

        if not results:
            results = {name: r for name, r in (sim.baseline if sim else {}).items()}

        insights = self.knowledge.explain(results)
        confidence = self._score_confidence(results, ambiguous)
        return {
            "question": question,
            "models_used": sorted(results.keys()),
            "results": {k: v.to_dict() for k, v in results.items()},
            "insights": [i.to_dict() for i in insights],
            "simulation": sim.to_dict() if sim else None,
            "confidence": round(confidence, 3),
            "ambiguous": ambiguous,
        }

    def _run_simulation(self, ctx: AnalysisContext, question: str,
                        extra: Optional[dict]) -> "SimulationComparison":
        """Runs a 'what if' simulation extracting deltas from the question."""
        # Robust delta extraction: supports "weight -5 kg", "bike -1 kg",
        # "+2% slope", "cda 0.3" via the shared helper.
        ov = parse_override_from_text(question)
        engine = SimulationEngine(ALL_ALGORITHMS)
        return engine.compare(ctx, ov, extra)

    # -- readable explanation (Italian) -------------------------------
    def explain_answer(self, answer: dict) -> str:
        """Generates a readable Italian explanation of results."""
        lines: list[str] = []
        lines.append(f"Domanda: {answer.get('question', '')}")

        ambiguous = answer.get("ambiguous", False)
        if ambiguous:
            lines.append("(domanda aperta: analisi completa su tutti i modelli)")

        conf = answer.get("confidence")
        if conf is not None:
            lines.append(f"Confidenza stimata: {conf * 100:.0f}%")

        models = answer.get("models_used", [])
        lines.append("Modelli usati: " + (", ".join(models) if models else "nessuno"))

        results = answer.get("results", {})
        if results:
            lines.append("Risultati chiave:")
            for name, r in results.items():
                unit = r.get("unit", "")
                value = r.get("value")
                prec = r.get("precision", 0)
                conf_r = r.get("confidence")
                detail = f"{value} {unit}".strip()
                if prec:
                    detail += f" (±{prec:.2f})"
                if conf_r is not None:
                    detail += f" [conf {conf_r * 100:.0f}%]"
                lines.append(f"  - {name}: {detail}")

        insights = answer.get("insights", [])
        if insights:
            lines.append("Concetti:")
            for i in insights:
                concept = i.get("concept", "")
                detail = i.get("detail", "")
                sev = i.get("severity", "")
                label = f" [{sev}]" if sev and sev != "info" else ""
                lines.append(f"  - {concept}{label}: {detail}")

        sim = answer.get("simulation")
        if sim:
            lines.append("Simulazione (risparmio/stima):")
            deltas = sim.get("deltas", {})
            results_for_unit = results or sim.get("baseline", {})
            shown = 0
            for name, delta in deltas.items():
                base = results_for_unit.get(name, {})
                unit = base.get("unit", "")
                base_val = base.get("value", 0)
                pct = (delta / base_val * 100.0) if base_val else 0.0
                arrow = "+" if delta > 0 else ("-" if delta < 0 else "=")
                verb = "consumo maggiore" if delta > 0 else ("risparmio" if delta < 0 else "invariato")
                lines.append(
                    f"  - {name}: {arrow}{abs(delta):.2f} {unit} "
                    f"({pct:+.1f}%) -> {verb}"
                )
                shown += 1
            if shown == 0:
                lines.append("  - nessuna variazione significativa")

        return "\n".join(lines)


# Type alias for simulation result
from .simulation import SimulationComparison as SimulationResultType  # noqa: E402

OrchestratorAnswer = dict
