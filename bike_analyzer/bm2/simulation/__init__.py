"""BikeMaster 2.0 - Simulation Engine ("what if" questions).

Allows modifying a scenario (e.g. "weight -5 kg", "bike change",
"slope +2%") and recalculating algorithms to compare before/after.

Extensions over the base version:
    * predefined scenario presets (``ScenarioPresets``);
    * sensitivity analysis ``SimulationEngine.sensitivity``;
    * combined multi-parameter overrides (already supported by
      ``ScenarioOverride``) and readable method ``SimulationComparison.summary``;
    * ``parse_override_from_text`` helper to extract an override from text
      (reusable by the orchestrator instead of inline regex).
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
    """Changes to apply to a context to simulate a scenario.

    All fields are combinable: a single override can change athlete
    weight, bike weight, slope, CdA and experience level simultaneously
    (multi-parameter override).
    """

    athlete_weight_delta_kg: float = 0.0
    bike_weight_delta_kg: float = 0.0
    slope_delta_percent: float = 0.0
    cda_override: Optional[float] = None
    experience_override: Optional[str] = None


@dataclass
class SimulationComparison:
    """Quantitative comparison between baseline and scenario results.

    Attributes:
        baseline: Algorithm results on the original context.
        scenario: Algorithm results on the modified context.
        deltas: Algorithm name -> difference (scenario - baseline).
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
        """Readable representation of the baseline -> scenario comparison."""
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
    """Predefined scenario presets, expressed as ``ScenarioOverride``."""

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
                f"unknown preset {name!r}; available: {cls.names()}"
            )
        return deepcopy(cls.PRESETS[name])

    @classmethod
    def build(cls, name: str, **overrides: float | str) -> ScenarioOverride:
        """Returns a copy of preset ``name`` with overridden fields."""
        ov = cls.get(name)
        for key, value in overrides.items():
            if not hasattr(ov, key):
                raise AttributeError(f"unknown ScenarioOverride field: {key!r}")
            setattr(ov, key, value)
        return ov


@dataclass
class SensitivityPoint:
    """Single point of a sensitivity analysis.

    Attributes:
        param_value: Value of the tested parameter at this point.
        results: Algorithm name -> scenario result value.
    """

    param_value: float
    results: dict[str, float]


@dataclass
class SensitivityResult:
    """Response curve of one or more algorithms as a parameter varies."""

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
    """Extracts a ``ScenarioOverride`` from question text.

    Recognizes: weight delta (``-5 kg`` / ``bike -2 kg``), slope delta
    (``+2%``), CdA override (``cda 0.3`` / ``cda=0.3``) and experience
    (``experience Elite``). The orchestrator can use this helper instead of
    inline regex to cover more cases (bike weight, CdA, slope) with a
    single documented extraction point.
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
    """Simulation engine that applies scenario overrides and compares algorithms.

    Receives a list of Algorithm classes; for each it runs on baseline
    and on scenario, producing a ``SimulationComparison`` with deltas.

    Attributes:
        algorithms: List of Algorithm classes to execute in each comparison.
    """

    def __init__(self, algorithms: Optional[list[type[Algorithm]]] = None) -> None:
        """Initialize the engine with the list of algorithms to use.

        Args:
            algorithms: Algorithm classes to register. If None, uses empty list.
        """
        self.algorithms = algorithms or []

    def _apply(self, ctx: AnalysisContext, ov: ScenarioOverride) -> AnalysisContext:
        """Applies an override to the scenario producing a new deep-copied context.

        Modifies athlete weight, bike weight, slope and/or CdA per the override,
        then adjusts GPS track altitudes to make the slope delta effective
        (algorithms read slope from the track, not from world).

        Args:
            ctx: Original analysis context (not modified).
            ov: Scenario override to apply.

        Returns:
            New AnalysisContext with modified parameters.
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
        # Algorithms derive slope from the GPS track (activity.metrics),
        # not from world: to make the slope delta effective we adjust track
        # altitudes progressively along horizontal distance.
        if ov.slope_delta_percent:
            self._apply_slope_to_track(new, ov.slope_delta_percent)
        # CdA override without bike weight change (the branches above already
        # apply it when bike_weight_delta_kg is set).
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
        """Adds ``delta_percent`` to average slope by raising altitudes.

        The elevation increment applied to each point is proportional to the
        cumulative horizontal distance from the start of the track, so the
        average slope (net/run) increases exactly by ``delta_percent``.
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
        """Runs all algorithms on baseline and scenario and calculates deltas.

        Args:
            ctx: Original analysis context (not modified).
            override: Scenario override to apply.
            extra: Additional data passed to each Algorithm.run().

        Returns:
            SimulationComparison with baseline, scenario and deltas per algorithm.
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
        """Compares the context with a predefined scenario."""
        return self.compare(ctx, ScenarioPresets.get(preset_name), extra)

    def _override_for_param(self, param: str, value: object) -> ScenarioOverride:
        """Creates a ScenarioOverride for a single sensitivity parameter.

        Resolves the parameter alias via ``_PARAM_ALIASES`` and sets the
        corresponding value.

        Args:
            param: Parameter name (e.g. ``"athlete_weight"``, ``"slope"``).
            value: Value to assign to the parameter.

        Returns:
            ScenarioOverride with a single field set.

        Raises:
            ValueError: If the parameter is not a recognized alias.
        """
        key = _PARAM_ALIASES.get(param.lower())
        if key is None:
            raise ValueError(
                f"unknown sensitivity parameter {param!r}; "
                f"available: {sorted(_PARAM_ALIASES)}"
            )
        ov = ScenarioOverride()
        setattr(ov, key, value)
        return ov

    def sensitivity(self, ctx: AnalysisContext, param: str, values: list,
                    extra: Optional[dict] = None) -> SensitivityResult:
        """Response curve of algorithms as ``param`` varies.

        ``param`` can be any alias in ``_PARAM_ALIASES`` (e.g.
        ``"athlete_weight"``, ``"slope"``, ``"cda"``, ``"experience"``).
        ``values`` is the list of values to test. Returns a
        ``SensitivityResult`` with, for each value, the scenario results of
        all registered algorithms.
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
