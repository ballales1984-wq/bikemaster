"""BikeMaster 2.0 - Simulation Engine (domande "what if").

Permette di modificare uno scenario (es. "peso -5 kg", "cambio bici",
"pendenza +2%") e ricalcolare gli algoritmi per confrontare prima/dopo.

Estensioni rispetto alla versione base:
    * preset di scenario predefiniti (``ScenarioPresets``);
    * analisi di sensitività ``SimulationEngine.sensitivity``;
    * override multi-parametrici combinati (già supportati da
      ``ScenarioOverride``) e metodo leggibile ``SimulationComparison.summary``;
    * helper ``parse_override_from_text`` per estrarre un override dal testo
      (riusabile dall'orchestrator al posto della regex inline).
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import ClassVar, Optional

from ..models import AnalysisContext, Athlete, Bike, WorldObject
from ..transformer import GeoPoint
from ..algorithms.base import Algorithm, ModelResult

__all__ = [
    "ScenarioOverride",
    "ScenarioPresets",
    "SensitivityPoint",
    "SensitivityResult",
    "SimulationEngine",
    "SimulationComparison",
    "parse_override_from_text",
]


@dataclass
class ScenarioOverride:
    """Modifiche da applicare a un contesto per simulare uno scenario.

    Tutti i campi sono combinabili: un singolo override può variare peso
    atleta, peso bici, pendenza, CdA e livello di esperienza contemporaneamente
    (override multi-parametrico).
    """

    athlete_weight_delta_kg: float = 0.0
    bike_weight_delta_kg: float = 0.0
    slope_delta_percent: float = 0.0
    cda_override: Optional[float] = None
    experience_override: Optional[str] = None


@dataclass
class SimulationComparison:
    """Confronto quantitativo tra risultati baseline e risultati scenario.

    Attributes:
        baseline: Risultati degli algoritmi sul contesto originale.
        scenario: Risultati degli algoritmi sul contesto modificato.
        deltas: Dizionario nome_algoritmo -> differenza (scenario - baseline).
    """

    baseline: dict[str, ModelResult]
    scenario: dict[str, ModelResult]
    deltas: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "baseline": {k: v.to_dict() for k, v in self.baseline.items()},
            "scenario": {k: v.to_dict() for k, v in self.scenario.items()},
            "deltas": {k: round(v, 4) for k, v in self.deltas.items()},
        }

    def summary(self) -> str:
        """Rappresentazione leggibile del confronto baseline -> scenario."""
        lines: list[str] = []
        for name in self.baseline:
            base = self.baseline[name]
            scen = self.scenario[name]
            delta = self.deltas.get(name, 0.0)
            pct = (delta / base.value * 100.0) if base.value else 0.0
            arrow = "\u25b2" if delta > 0 else ("\u25bc" if delta < 0 else "=")
            lines.append(
                f"{name}: {base.value:.2f} -> {scen.value:.2f} {base.unit} "
                f"({arrow}{delta:+.2f}, {pct:+.1f}%)"
            )
        return "\n".join(lines)


@dataclass
class ScenarioPresets:
    """Preset di scenario predefiniti, espressi come ``ScenarioOverride``."""

    PRESETS: ClassVar[dict[str, ScenarioOverride]] = {
        "race": ScenarioOverride(
            athlete_weight_delta_kg=-2.0,
            bike_weight_delta_kg=-1.0,
            cda_override=0.28,
            experience_override="Elite",
        ),
        "training": ScenarioOverride(
            slope_delta_percent=1.0,
            cda_override=0.34,
            experience_override="Intermediate",
        ),
        "light_bike": ScenarioOverride(
            bike_weight_delta_kg=-2.0,
            cda_override=0.33,
        ),
    }

    @classmethod
    def names(cls) -> list[str]:
        return list(cls.PRESETS.keys())

    @classmethod
    def get(cls, name: str) -> ScenarioOverride:
        if name not in cls.PRESETS:
            raise KeyError(
                f"preset sconosciuto {name!r}; disponibili: {cls.names()}"
            )
        return deepcopy(cls.PRESETS[name])

    @classmethod
    def build(cls, name: str, **overrides: float | str) -> ScenarioOverride:
        """Restituisce una copia del preset ``name`` con campi sovrascritti."""
        ov = cls.get(name)
        for key, value in overrides.items():
            if not hasattr(ov, key):
                raise AttributeError(f"campo ScenarioOverride sconosciuto: {key!r}")
            setattr(ov, key, value)
        return ov


@dataclass
class SensitivityPoint:
    """Punto singolo di un'analisi di sensitivita'.

    Attributes:
        param_value: Valore del parametro testato in questo punto.
        results: Dizionario nome_algoritmo -> valore del risultato scenario.
    """

    param_value: float
    results: dict[str, float]


@dataclass
class SensitivityResult:
    """Curva di risposta di uno o piu' algoritmi al variare di un parametro."""

    param: str
    values: list[float]
    points: list[SensitivityPoint] = field(default_factory=list)

    def curve(self, algorithm_name: str) -> list[tuple[float, Optional[float]]]:
        return [(p.param_value, p.results.get(algorithm_name)) for p in self.points]

    def to_dict(self) -> dict:
        return {
            "param": self.param,
            "values": self.values,
            "points": [
                {"param_value": p.param_value, "results": p.results}
                for p in self.points
            ],
        }


_PARAM_ALIASES = {
    "athlete_weight": "athlete_weight_delta_kg",
    "weight": "athlete_weight_delta_kg",
    "mass": "athlete_weight_delta_kg",
    "bike_weight": "bike_weight_delta_kg",
    "bike": "bike_weight_delta_kg",
    "slope": "slope_delta_percent",
    "pendenza": "slope_delta_percent",
    "cda": "cda_override",
    "experience": "experience_override",
    "exp": "experience_override",
}


def parse_override_from_text(text: str) -> ScenarioOverride:
    """Estrae un ``ScenarioOverride`` dal testo di una domanda.

    Riconosce: delta di peso (``-5 kg`` / ``bici -2 kg``), delta di pendenza
    (``+2%``), override CdA (``cda 0.3`` / ``cda=0.3``) ed esperienza
    (``experience Elite``). L'orchestrator puo' usare questo helper al posto
    della regex inline per coprire piu' casi (peso bici, CdA, pendenza) con un
    unico punto di estrazione documentato.
    """
    ov = ScenarioOverride()
    t = text.lower()

    if "bici" in t or "bike" in t:
        m = re.search(r"(-?\d+(?:\.\d+)?)\s*kg", t)
        if m:
            ov.bike_weight_delta_kg = float(m.group(1))
    else:
        m = re.search(r"(-?\d+(?:\.\d+)?)\s*kg", t)
        if m:
            ov.athlete_weight_delta_kg = float(m.group(1))

    mp = re.search(r"(-?\d+(?:\.\d+)?)\s*%", t)
    if mp:
        ov.slope_delta_percent = float(mp.group(1))

    mc = re.search(r"cda\s*=?\s*(\d+(?:\.\d+)?)", t)
    if mc:
        ov.cda_override = float(mc.group(1))

    me = re.search(r"experience\s*=?\s*([a-z]+)", t)
    if me:
        ov.experience_override = me.group(1).capitalize()
    return ov


class SimulationEngine:
    """Motore di simulazione che applica override di scenario e confronta algoritmi.

    Riceve una lista di classi Algorithm; per ciascuna esegue il run su baseline
    e su scenario, producendo un ``SimulationComparison`` con deltas.

    Attributes:
        algorithms: Lista di classi Algorithm da eseguire in ogni confronto.
    """

    def __init__(self, algorithms: Optional[list[type[Algorithm]]] = None) -> None:
        """Inizializza il motore con la lista di algoritmi da usare.

        Args:
            algorithms: Classi Algorithm da registrare. Se None, usa lista vuota.
        """
        self.algorithms = algorithms or []

    def _apply(self, ctx: AnalysisContext, ov: ScenarioOverride) -> AnalysisContext:
        """Applica un override allo scenario producendo un nuovo contesto deep-copiato.

        Modifica peso atleta, peso bici, pendenza e/o CdA secondo l'override,
        poi adegua le altitudini della traccia GPS per rendere effettivo il delta
        di pendenza (gli algoritmi leggono la pendenza dalla traccia, non da world).

        Args:
            ctx: Contesto di analisi originale (non modificato).
            ov: Override di scenario da applicare.

        Returns:
            Nuovo AnalysisContext con i parametri modificati.
        """
        new = deepcopy(ctx)
        if ov.athlete_weight_delta_kg:
            w = new.athlete.weight_kg
            new.athlete = Athlete(
                weight_kg=type(w)(w.value + ov.athlete_weight_delta_kg, w.unit,
                                  w.precision, w.source, w.timestamp),
                age=new.athlete.age, height_m=new.athlete.height_m,
                ftp_w=new.athlete.ftp_w, max_hr_bpm=new.athlete.max_hr_bpm,
                resting_hr_bpm=new.athlete.resting_hr_bpm,
                experience_level=ov.experience_override or new.athlete.experience_level,
                weekly_hours=new.athlete.weekly_hours, name=new.athlete.name,
            )
        if ov.bike_weight_delta_kg:
            b = new.bike.weight_kg
            new.bike = Bike(
                weight_kg=type(b)(b.value + ov.bike_weight_delta_kg, b.unit,
                                  b.precision, b.source, b.timestamp),
                crr=new.bike.crr,
                cda=ov.cda_override if ov.cda_override is not None else new.bike.cda,
                drivetrain_efficiency=new.bike.drivetrain_efficiency,
                name=new.bike.name,
            )
        if ov.slope_delta_percent and new.world.avg_slope_percent is not None:
            s = new.world.avg_slope_percent
            new.world = WorldObject(
                surface=new.world.surface, roughness_index=new.world.roughness_index,
                avg_slope_percent=type(s)(s.value + ov.slope_delta_percent, s.unit,
                                          s.precision, s.source, s.timestamp),
                wind_speed_ms=new.world.wind_speed_ms, temperature_c=new.world.temperature_c,
            )
        elif ov.slope_delta_percent:
            new.world = WorldObject(
                surface=new.world.surface, roughness_index=new.world.roughness_index,
                avg_slope_percent=None, wind_speed_ms=new.world.wind_speed_ms,
                temperature_c=new.world.temperature_c,
            )
        # Gli algoritmi ricavano la pendenza dalla traccia GPS (activity.metrics),
        # non da world: per rendere effettivo il delta di pendenza adeguiamo le
        # altitudini dei punti in modo progressivo lungo la distanza orizzontale.
        if ov.slope_delta_percent:
            self._apply_slope_to_track(new, ov.slope_delta_percent)
        # Override CdA senza cambio peso bici (i rami sopra lo applicano gia'
        # quando bike_weight_delta_kg e' impostato).
        if ov.cda_override is not None and not ov.bike_weight_delta_kg \
                and new.bike.cda != ov.cda_override:
            new.bike = Bike(
                weight_kg=new.bike.weight_kg,
                crr=new.bike.crr,
                cda=ov.cda_override,
                drivetrain_efficiency=new.bike.drivetrain_efficiency,
                name=new.bike.name,
            )
        return new

    @staticmethod
    def _apply_slope_to_track(ctx: AnalysisContext, delta_percent: float) -> None:
        """Aggiunge ``delta_percent`` alla pendenza media alzando le altitudini.

        L'incremento di quota applicato a ogni punto e' proporzionale alla
        distanza orizzontale cumulata dall'inizio della traccia, cosi' la
        pendenza media (net/run) aumenta esattamente di ``delta_percent``.
        """
        pts = ctx.activity.points
        if len(pts) < 2:
            return
        geo = ctx.transformer.geo
        metric = geo.to_metric_points(pts)
        frac = delta_percent / 100.0
        cum = 0.0
        prev = None
        new_pts = []
        for orig, mp in zip(pts, metric):
            if prev is not None:
                cum += geo.distance_2d_m(prev, mp)
            prev = mp
            new_pts.append(replace(orig, altitude=orig.altitude + frac * cum))
        ctx.activity.points = new_pts

    def compare(self, ctx: AnalysisContext, override: ScenarioOverride,
                extra: Optional[dict] = None) -> SimulationComparison:
        """Esegue tutti gli algoritmi su baseline e scenario e calcola i deltas.

        Args:
            ctx: Contesto di analisi originale (non modificato).
            override: Override di scenario da applicare.
            extra: Dati aggiuntivi passati a ogni Algorithm.run().

        Returns:
            SimulationComparison con baseline, scenario e deltas per ogni algoritmo.
        """
        baseline_res: dict[str, ModelResult] = {}
        scenario_res: dict[str, ModelResult] = {}
        for algo_cls in self.algorithms:
            algo = algo_cls()
            baseline_res[algo.name] = algo.run(ctx, extra)
            scenario = self._apply(ctx, override)
            scenario_res[algo.name] = algo.run(scenario, extra)
        deltas = {name: scenario_res[name].value - baseline_res[name].value
                  for name in baseline_res}
        return SimulationComparison(baseline=baseline_res, scenario=scenario_res, deltas=deltas)

    def compare_preset(self, ctx: AnalysisContext, preset_name: str,
                       extra: Optional[dict] = None) -> SimulationComparison:
        """Confronta il contesto con uno scenario predefinito."""
        return self.compare(ctx, ScenarioPresets.get(preset_name), extra)

    def _override_for_param(self, param: str, value: object) -> ScenarioOverride:
        """Crea uno ScenarioOverride per un singolo parametro di sensitivita'.

        Risolve l'alias del parametro tramite ``_PARAM_ALIASES`` e imposta
        il valore corrispondente.

        Args:
            param: Nome del parametro (es. ``"athlete_weight"``, ``"slope"``).
            value: Valore da assegnare al parametro.

        Returns:
            ScenarioOverride con un solo campo impostato.

        Raises:
            ValueError: Se il parametro non e' un alias riconosciuto.
        """
        key = _PARAM_ALIASES.get(param.lower())
        if key is None:
            raise ValueError(
                f"parametro di sensitivita' sconosciuto {param!r}; "
                f"disponibili: {sorted(_PARAM_ALIASES)}"
            )
        ov = ScenarioOverride()
        setattr(ov, key, value)
        return ov

    def sensitivity(self, ctx: AnalysisContext, param: str, values: list,
                    extra: Optional[dict] = None) -> SensitivityResult:
        """Curva di risposta degli algoritmi al variare di ``param``.

        ``param`` puo' essere un qualsiasi alias in ``_PARAM_ALIASES`` (es.
        ``"athlete_weight"``, ``"slope"``, ``"cda"``, ``"experience"``).
        ``values`` e' la lista dei valori da testare. Restituisce un
        ``SensitivityResult`` con, per ogni valore, i risultati di scenario di
        tutti gli algoritmi registrati.
        """
        result = SensitivityResult(param=param, values=list(values))
        for v in values:
            ov = self._override_for_param(param, v)
            comp = self.compare(ctx, ov, extra)
            point = SensitivityPoint(
                param_value=float(v),
                results={name: res.value for name, res in comp.scenario.items()},
            )
            result.points.append(point)
        return result
