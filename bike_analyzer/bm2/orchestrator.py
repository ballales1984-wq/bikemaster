"""BikeMaster 2.0 - AI Orchestrator (il cicerone digitale).

Non calcola: decide *quali* agenti e *quali* algoritmi usare in base alla
domanda, assembla il contesto e restituisce risultati + concetti + spiegazione.

Miglioramenti rispetto alla versione base:
    * routing domanda -> modelli robusto (keyword con peso + sinonimi IT),
      esposto come configurabile via ``_select_models`` / costruttore;
    * scoring di confidence sulla risposta e gestione domande ambigue
      ("dimmi tutto" -> tutti i modelli);
    * metodo ``explain_answer`` che restituisce un testo leggibile in italiano;
    * estrazione delta "what if" affidabile (usa ``parse_override_from_text``:
      supporta "peso -5 kg", "bici -1 kg", "+2% pendenza", "cda 0.3").
"""

from __future__ import annotations

from typing import Optional

from .algorithms import (
    ALL_ALGORITHMS, Algorithm, EnergyModel, FatigueModel, ModelResult,
    MovementModel, NutritionModel, PerformanceModel, RecoveryModel,
    RouteDifficultyModel,
)
from .knowledge import Insight, KnowledgeEngine
from .models import AnalysisContext, Athlete, Bike, Activity, WorldObject
from .simulation import ScenarioOverride, SimulationEngine, parse_override_from_text
from .transformer import TransformerEngine
from .agents import AthleteAgent, EnvironmentAgent, GPSAgent, SensorAgent

__all__ = ["AIOrchestrator", "OrchestratorAnswer"]


# -- mappatura domanda -> modelli (configurabile) -------------------------
# Ogni modello ha un dizionario {parola_chiave: peso}. Il peso serve a
# discriminare match deboli/forti e a ordinare i modelli piu' rilevanti.
DEFAULT_MODEL_KEYWORDS: dict[str, dict[str, float]] = {
    "EnergyModel": {
        "energia": 1.0, "calorie": 1.0, "caloria": 1.0, "consumo": 1.0,
        "kcal": 1.0, "brucio": 1.0, "bruci": 1.0, "dispendio": 1.0,
        "speso": 0.7, "spendi": 0.7,
    },
    "NutritionModel": {
        "nutrizione": 1.0, "mangi": 1.0, "idrata": 1.0, "idratare": 1.0,
        "carboidrat": 1.0, "cibo": 0.9, "bere": 0.9, "proteine": 0.9,
        "zuccheri": 0.8, "integraz": 0.8,
    },
    "RouteDifficultyModel": {
        "difficile": 1.0, "difficoltà": 1.0, "difficolta": 1.0,
        "percorso": 1.0, "percorri": 0.9, "tracciato": 0.9,
        "salita": 1.0, "salite": 1.0, "sali": 0.8, "dislivello": 1.0,
        "pendenza": 1.0, "pendenze": 1.0,
    },
    "FatigueModel": {
        "fatica": 1.0, "stanco": 1.0, "stanca": 0.9, "affatic": 1.0,
        "stanchezza": 1.0, "sforzo": 0.8, "cedimento": 1.0,
    },
    "RecoveryModel": {
        "recupero": 1.0, "riposo": 1.0, "riposa": 0.9, "dormi": 0.9,
        "sonno": 0.9, "recovery": 1.0, "rigenera": 1.0,
    },
    "MovementModel": {
        "movimento": 1.0, "velocità": 1.0, "velocita": 1.0,
        "andatura": 1.0, "cadenza": 0.9, "pedalata": 0.9, "moto": 0.8,
    },
    "PerformanceModel": {
        "prestazione": 1.0, "performance": 1.0, "miglior": 0.9,
        "efficienza": 0.9, "potenza": 0.8, "rendimento": 0.9,
        "ftp": 0.9, "migliora": 0.8,
    },
    "PowerModel": {
        "potenza": 1.0, "watt": 1.0, "power": 1.0, "ftp": 0.6,
    },
    "TrainingLoadModel": {
        "carico": 1.0, "allenamento": 0.9, "training": 1.0,
        "stress": 0.8, "ctl": 0.7, "tsb": 0.7,
    },
}

# Parole che segnalano una domanda "aperta" -> usa tutti i modelli.
DEFAULT_AMBIGUOUS_KEYWORDS: frozenset[str] = frozenset({
    "tutto", "complet", "generale", "sommario", "panoramica", "overview",
    "riassunto", "analisi completa", "dimmi tutto", "spiegami tutto",
})

# Parole che attivano la simulazione "what if".
_SIMULATION_KEYWORDS: tuple[str, ...] = ("se ", "what if", "simula", "ipotizz", "ipotizzo")

# Soglia minima di score perchè un modello sia considerato rilevante.
DEFAULT_ROUTE_THRESHOLD: float = 0.5


class AIOrchestrator:
    def __init__(self, transformer: Optional[TransformerEngine] = None,
                 model_keywords: Optional[dict[str, dict[str, float]]] = None,
                 ambiguous_keywords: Optional[frozenset[str]] = None,
                 route_threshold: float = DEFAULT_ROUTE_THRESHOLD) -> None:
        self.t = transformer or TransformerEngine()
        self.gps = GPSAgent(self.t)
        self.athlete_agent = AthleteAgent(self.t)
        self.env_agent = EnvironmentAgent(self.t)
        self.sensor_agent = SensorAgent(self.t)
        self.knowledge = KnowledgeEngine()

        self.model_keywords = model_keywords or DEFAULT_MODEL_KEYWORDS
        self.ambiguous_keywords = ambiguous_keywords or DEFAULT_AMBIGUOUS_KEYWORDS
        self.route_threshold = route_threshold

    # -- assemblaggio contesto -------------------------------------------
    def build_context(self, raw: dict) -> AnalysisContext:
        athlete = self.athlete_agent.collect(raw.get("athlete", {}))
        bike = Bike.from_raw(raw.get("bike", {}), self.t)
        activity = self.gps.collect(raw.get("gps_points", []), raw.get("title", ""))
        if raw.get("sensors"):
            activity = self.sensor_agent.enrich_points(activity, raw["sensors"])
        world = self.env_agent.collect(raw.get("world", {}))
        return AnalysisContext(athlete=athlete, activity=activity, bike=bike,
                               world=world, transformer=self.t)

    # -- routing domanda -> modelli -------------------------------------
    def _is_simulation(self, question: str) -> bool:
        q = question.lower()
        return any(k in q for k in _SIMULATION_KEYWORDS)

    def _is_ambiguous(self, question: str) -> bool:
        q = question.lower()
        return any(k in q for k in self.ambiguous_keywords)

    def _select_models(self, question: str,
                       keywords: Optional[dict[str, dict[str, float]]] = None,
                       threshold: Optional[float] = None
                       ) -> list[type[Algorithm]]:
        """Mappa la domanda ai modelli rilevanti tramite keyword scoring.

        Il mapping e' configurabile: ``keywords`` sovrascrive la mappa di
        default (per test o personalizzazioni), ``threshold`` la soglia minima
        di score. Domande ambigue o senza match rilevante restituiscono tutti
        i modelli (fallback "dimmi tutto").
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

        # mantieni l'ordine canonico di ALL_ALGORITHMS per stabilità
        ordered = [a for a in ALL_ALGORITHMS if a.name in selected]
        return ordered

    # -- scoring di confidence sulla risposta ---------------------------
    @staticmethod
    def _score_confidence(results: dict[str, ModelResult],
                          ambiguous: bool) -> float:
        if not results:
            return 0.0
        avg = sum(r.confidence for r in results.values()) / len(results)
        # una domanda aperta (tutti i modelli) ha confidenza leggermente
        # ridotta perchè i risultati sono meno mirati alla richiesta.
        return max(0.0, min(1.0, avg * (0.9 if ambiguous else 1.0)))

    # -- risposta --------------------------------------------------------
    def answer(self, question: str, raw: dict, extra: Optional[dict] = None) -> dict:
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
        # Estrazione robusta del delta: supporta "peso -5 kg", "bici -1 kg",
        # "+2% pendenza", "cda 0.3" tramite l'helper condiviso.
        ov = parse_override_from_text(question)
        engine = SimulationEngine(ALL_ALGORITHMS)
        return engine.compare(ctx, ov, extra)

    # -- spiegazione leggibile (italiano) -------------------------------
    def explain_answer(self, answer: dict) -> str:
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
            lines.append("Insights:")
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
                verb = "maggior consumo" if delta > 0 else ("risparmio" if delta < 0 else "invariato")
                lines.append(
                    f"  - {name}: {arrow}{abs(delta):.2f} {unit} "
                    f"({pct:+.1f}%) -> {verb}"
                )
                shown += 1
            if shown == 0:
                lines.append("  - nessuna variazione rilevante")

        return "\n".join(lines)


# Alias di tipo per il risultato simulazione
from .simulation import SimulationComparison as SimulationResultType  # noqa: E402

OrchestratorAnswer = dict
