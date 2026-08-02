"""BikeMaster 2.0 — Simulation Engine demo.

Eseguibile con::

    cd bike_analyzer
    python -m bm2.simulation.demo

Mostra un confronto "before/after" applicando un preset di scenario
(predefinito) e stampa un'analisi di sensitivita' su un parametro.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..algorithms.power_model import PowerModel
from ..models import Activity, AnalysisContext, Athlete, Bike, GeoPoint, WorldObject
from ..simulation import ScenarioOverride, ScenarioPresets, SimulationEngine
from ..transformer import TransformerEngine
from ..units import q


def _build_context() -> AnalysisContext:
    t = TransformerEngine()
    athlete = Athlete(weight_kg=t.normalize(q(72.0, "kg")), ftp_w=t.normalize(q(260.0, "W")))
    bike = Bike(weight_kg=t.normalize(q(7.8, "kg")))
    world = WorldObject(avg_slope_percent=t.normalize(q(2.0, "%")))
    t0 = datetime(2024, 1, 1, 10, 0, 0)
    points = [
        GeoPoint(lat=45.0 + i * 0.001, lon=7.0 + i * 0.001, altitude=100.0 + i,
                 timestamp=t0 + timedelta(seconds=i * 10), speed=8.0)
        for i in range(20)
    ]
    activity = Activity(points=points, title="Demo ride")
    return AnalysisContext(athlete=athlete, activity=activity, bike=bike, world=world, transformer=t)


def main() -> None:
    ctx = _build_context()
    engine = SimulationEngine(algorithms=[PowerModel])

    print("=== BikeMaster 2.0 Simulation Engine demo ===\n")
    base = engine.compare(ctx, ScenarioOverride())  # baseline (nessun override)
    print(f"Scenario di base: power={base.scenario['PowerModel'].value:.1f} W")

    print("\nConfronto con preset 'light_bike' (bici -2 kg, CdA 0.33):")
    comparison = engine.compare_preset(ctx, "light_bike")
    summary = comparison.summary()
    try:
        print(summary)
    except UnicodeEncodeError:
        print(summary.encode("ascii", "replace").decode("ascii"))

    print("\nAnalisi di sensitivita' (pendenza 0% -> 8%):")
    sensitivity = engine.sensitivity(ctx, param="slope", values=list(range(0, 9, 2)))
    for point in sensitivity.points:
        power = point.results.get("PowerModel")
        if power is not None:
            print(f"  slope={point.param_value:.1f}% -> power={power:.1f} W")


if __name__ == "__main__":
    main()
