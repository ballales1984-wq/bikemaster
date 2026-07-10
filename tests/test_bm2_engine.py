"""Test BikeMaster 2.0 - modello, algoritmi, simulazione, knowledge, orchestrator."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from bike_analyzer.bm2 import (
    AIOrchestrator, AnalysisContext, Athlete, Bike, EnergyModel, FatigueModel,
    MovementModel, PowerModel, RecoveryModel, RouteDifficultyModel,
    SimulationEngine, TrainingLoadModel, TransformerEngine, WorldObject, q,
)
from bike_analyzer.bm2.algorithms import ALL_ALGORITHMS, MODEL_REGISTRY
from bike_analyzer.bm2.orchestrator import ScenarioOverride
from bike_analyzer.bm2.simulation import (
    ScenarioPresets, SensitivityResult, parse_override_from_text,
)
from bike_analyzer.bm2.transformer import GeoPoint


def _ctx():
    t = TransformerEngine()
    athlete = Athlete(
        weight_kg=t.normalize(q(75.0, "kg", source="manual")),
        age=34, max_hr_bpm=t.normalize(q(190.0, "bpm")), experience_level="Intermediate",
    )
    bike = Bike(weight_kg=t.normalize(q(8.0, "kg", source="manual")))
    pts = [
        GeoPoint(45.0, 9.0, 200, datetime(2026, 7, 10, 8, 0, 0, tzinfo=timezone.utc)),
        GeoPoint(45.005, 9.005, 360, datetime(2026, 7, 10, 9, 0, 0, tzinfo=timezone.utc)),
    ]
    activity = __import__("bike_analyzer.bm2.models", fromlist=["Activity"]).Activity(points=pts)
    world = WorldObject(surface="asphalt", avg_slope_percent=t.normalize(q(5.0, "%", source="dem")))
    return AnalysisContext(athlete=athlete, activity=activity, bike=bike, world=world, transformer=t)


def test_all_algorithms_registered():
    assert len(ALL_ALGORITHMS) == 9
    assert "PowerModel" in MODEL_REGISTRY
    assert "TrainingLoadModel" in MODEL_REGISTRY


def test_energy_model_runs_and_reports_provenance():
    r = EnergyModel().run(_ctx())
    assert r.unit == "kcal"
    assert r.value > 0
    assert r.formula
    assert "massa_totale" in r.data_used
    assert 0.0 <= r.confidence <= 1.0
    assert r.precision > 0


def test_movement_model_zero_duration_safe():
    t = TransformerEngine()
    a = Athlete(weight_kg=q(70, "kg"), age=30)
    b = Bike(weight_kg=q(8, "kg"))
    act = __import__("bike_analyzer.bm2.models", fromlist=["Activity"]).Activity(points=[])
    w = WorldObject()
    ctx = AnalysisContext(a, act, b, w, t)
    r = MovementModel().run(ctx)
    assert r.value == 0.0
    assert r.confidence < 0.5


def test_fatigue_and_recovery_consistency():
    f = FatigueModel().run(_ctx())
    rec = RecoveryModel().run(_ctx(), {"sleep_hours": 8, "hrv_rmssd": 60})
    assert 0.0 <= f.value <= 10.0
    assert 0.0 <= rec.value <= 100.0
    assert "recovery_hours" in rec.details


def test_route_difficulty_categories():
    r = RouteDifficultyModel().run(_ctx())
    assert r.details["category"] in {"Facile", "Moderato", "Impegnativo", "Estremo"}


def test_simulation_weight_delta_changes_energy():
    ctx = _ctx()
    engine = SimulationEngine(ALL_ALGORITHMS)
    comp = engine.compare(ctx, ScenarioOverride(athlete_weight_delta_kg=-5.0))
    base_e = comp.baseline["EnergyModel"].value
    scen_e = comp.scenario["EnergyModel"].value
    assert scen_e < base_e  # meno massa -> meno energia
    assert comp.deltas["EnergyModel"] < 0


def test_orchestrator_routes_energy_question():
    orc = AIOrchestrator()
    raw = _raw()
    ans = orc.answer("Quanta energia consumo?", raw)
    assert "EnergyModel" in ans["models_used"]
    assert ans["simulation"] is None
    assert "results" in ans and "insights" in ans


def test_orchestrator_runs_simulation_question():
    orc = AIOrchestrator()
    ans = orc.answer("Se peso -5 kg quanto risparmio?", _raw())
    assert ans["simulation"] is not None
    assert ans["simulation"]["deltas"]["EnergyModel"] < 0


def test_orchestrator_routes_energy_question_robust():
    orc = AIOrchestrator()
    ans = orc.answer("Quante calorie brucio in salita?", _raw())
    assert "EnergyModel" in ans["models_used"]
    assert ans["ambiguous"] is False
    assert 0.0 <= ans["confidence"] <= 1.0


def test_orchestrator_routes_synonyms():
    orc = AIOrchestrator()
    ans = orc.answer("Quanto dispendio energetico ho?", _raw())
    assert "EnergyModel" in ans["models_used"]


def test_orchestrator_ambiguous_uses_all_models():
    orc = AIOrchestrator()
    ans = orc.answer("Dimmi tutto della mia uscita", _raw())
    assert ans["ambiguous"] is True
    assert set(ans["models_used"]) == {a.name for a in ALL_ALGORITHMS}


def test_orchestrator_route_threshold_filters_weak_match():
    orc = AIOrchestrator()
    models = orc._select_models("Parlami del meteo oggi", threshold=0.5)
    # nessun match rilevante -> fallback a tutti i modelli
    assert set(m.name for m in models) == {a.name for a in ALL_ALGORITHMS}


def test_orchestrator_select_models_configurable():
    orc = AIOrchestrator()
    custom = {"EnergyModel": {"calorie": 1.0}}
    models = orc._select_models("calorie", keywords=custom, threshold=0.5)
    assert [m.name for m in models] == ["EnergyModel"]


def test_orchestrator_whatif_bike_and_slope():
    orc = AIOrchestrator()
    ans = orc.answer("Se bici -1 kg e pendenza +2% come cambia?", _raw())
    sim = ans["simulation"]
    assert sim is not None
    assert sim["deltas"]["EnergyModel"] != 0.0


def test_orchestrator_explain_answer_includes_sections():
    orc = AIOrchestrator()
    ans = orc.answer("Quante calorie brucio?", _raw())
    text = orc.explain_answer(ans)
    assert "Domanda:" in text
    assert "Modelli usati:" in text
    assert "Risultati chiave:" in text
    assert "EnergyModel" in text
    assert "Confidenza stimata:" in text


def test_orchestrator_explain_answer_simulation():
    orc = AIOrchestrator()
    ans = orc.answer("Se peso -5 kg quanto risparmio?", _raw())
    text = orc.explain_answer(ans)
    assert "Simulazione" in text
    assert "risparmio" in text


def _raw():
    return {
        "athlete": {"weight": 75, "age": 34, "experience_level": "Intermediate", "max_hr": 190},
        "bike": {"weight": 8},
        "world": {"surface": "asphalt", "avg_slope": 5.0},
        "gps_points": [
            {"lat": 45.0, "lon": 9.0, "altitude": 200, "timestamp": "2026-07-10T08:00:00Z"},
            {"lat": 45.005, "lon": 9.005, "altitude": 360, "timestamp": "2026-07-10T09:00:00Z"},
        ],
        "sensors": [
            {"heart_rate": 140, "power": 180},
            {"heart_rate": 165, "power": 240},
        ],
    }


def test_power_model_with_ftp():
    t = TransformerEngine()
    athlete = Athlete(
        weight_kg=t.normalize(q(75.0, "kg", source="manual")),
        age=34, ftp_w=t.normalize(q(250.0, "W", source="manual")),
        experience_level="Intermediate",
    )
    bike = Bike(weight_kg=t.normalize(q(8.0, "kg", source="manual")))
    pts = [
        GeoPoint(45.0, 9.0, 200, datetime(2026, 7, 10, 8, 0, 0, tzinfo=timezone.utc)),
        GeoPoint(45.005, 9.005, 360, datetime(2026, 7, 10, 9, 0, 0, tzinfo=timezone.utc)),
    ]
    activity = __import__("bike_analyzer.bm2.models", fromlist=["Activity"]).Activity(points=pts)
    world = WorldObject(surface="asphalt", avg_slope_percent=t.normalize(q(5.0, "%", source="dem")))
    ctx = AnalysisContext(athlete=athlete, activity=activity, bike=bike, world=world, transformer=t)
    r = PowerModel().run(ctx)
    assert r.unit == "W"
    assert r.value > 0
    assert r.precision > 0
    assert 0.0 <= r.confidence <= 1.0
    assert "ftp_w" in r.details


def test_power_model_with_sensor_power():
    t = TransformerEngine()
    athlete = Athlete(
        weight_kg=t.normalize(q(75.0, "kg", source="manual")),
        age=34, ftp_w=t.normalize(q(250.0, "W", source="manual")),
        experience_level="Intermediate",
    )
    bike = Bike(weight_kg=t.normalize(q(8.0, "kg", source="manual")))
    pts = [
        GeoPoint(45.0, 9.0, 200, datetime(2026, 7, 10, 8, 0, 0, tzinfo=timezone.utc),
                 power=200.0),
        GeoPoint(45.005, 9.005, 360, datetime(2026, 7, 10, 9, 0, 0, tzinfo=timezone.utc),
                 power=220.0),
    ]
    activity = __import__("bike_analyzer.bm2.models", fromlist=["Activity"]).Activity(points=pts)
    world = WorldObject(surface="asphalt", avg_slope_percent=t.normalize(q(5.0, "%", source="dem")))
    ctx = AnalysisContext(athlete=athlete, activity=activity, bike=bike, world=world, transformer=t)
    r = PowerModel().run(ctx)
    assert r.value == pytest.approx(210.0, abs=1.0)
    assert r.confidence == pytest.approx(0.855, abs=0.01)


def test_training_load_with_history():
    t = TransformerEngine()
    athlete = Athlete(
        weight_kg=t.normalize(q(75.0, "kg", source="manual")),
        age=34, ftp_w=t.normalize(q(250.0, "W", source="manual")),
        experience_level="Intermediate",
    )
    bike = Bike(weight_kg=t.normalize(q(8.0, "kg", source="manual")))
    pts = [
        GeoPoint(45.0, 9.0, 200, datetime(2026, 7, 10, 8, 0, 0, tzinfo=timezone.utc)),
        GeoPoint(45.005, 9.005, 360, datetime(2026, 7, 10, 9, 0, 0, tzinfo=timezone.utc)),
    ]
    activity = __import__("bike_analyzer.bm2.models", fromlist=["Activity"]).Activity(points=pts)
    world = WorldObject(surface="asphalt", avg_slope_percent=t.normalize(q(5.0, "%", source="dem")))
    ctx = AnalysisContext(athlete=athlete, activity=activity, bike=bike, world=world, transformer=t)
    history = [
        {"duration_s": 3600, "avg_power_w": 200},
        {"duration_s": 3600, "avg_power_w": 210},
    ] * 5
    r = TrainingLoadModel().run(ctx, {"activity_history": history})
    assert r.unit == "score"
    assert "ctl" in r.details
    assert "atl" in r.details
    assert "tsb" in r.details
    assert r.details["tss_history_count"] == 10


def test_training_load_no_history():
    t = TransformerEngine()
    athlete = Athlete(
        weight_kg=t.normalize(q(75.0, "kg", source="manual")),
        age=34, ftp_w=t.normalize(q(250.0, "W", source="manual")),
        experience_level="Intermediate",
    )
    bike = Bike(weight_kg=t.normalize(q(8.0, "kg", source="manual")))
    pts = [
        GeoPoint(45.0, 9.0, 200, datetime(2026, 7, 10, 8, 0, 0, tzinfo=timezone.utc)),
        GeoPoint(45.005, 9.005, 360, datetime(2026, 7, 10, 9, 0, 0, tzinfo=timezone.utc)),
    ]
    activity = __import__("bike_analyzer.bm2.models", fromlist=["Activity"]).Activity(points=pts)
    world = WorldObject(surface="asphalt", avg_slope_percent=t.normalize(q(5.0, "%", source="dem")))
    ctx = AnalysisContext(athlete=athlete, activity=activity, bike=bike, world=world, transformer=t)
    r = TrainingLoadModel().run(ctx, {})
    assert r.value <= 0
    assert r.confidence < 0.6


def test_model_result_uncertainty_bounds():
    from bike_analyzer.bm2.algorithms.base import ModelResult
    r = ModelResult(value=100.0, unit="W", formula="test", data_used=[],
                    precision=5.0, confidence=0.8, source="test")
    lo, hi = r.uncertainty_bounds()
    assert lo == pytest.approx(95.0)
    assert hi == pytest.approx(105.0)


def test_model_result_compare_with():
    from bike_analyzer.bm2.algorithms.base import ModelResult
    a = ModelResult(value=100.0, unit="W", formula="f1", data_used=[],
                    precision=5.0, confidence=0.8, source="A")
    b = ModelResult(value=120.0, unit="W", formula="f2", data_used=[],
                    precision=3.0, confidence=0.9, source="B")
    comp = a.compare_with(b)
    assert comp["delta_value"] == -20.0
    assert comp["comparable_units"] is True
    assert comp["self"] == "A"
    assert comp["other"] == "B"


# --- Simulation Engine: preset, override combinati, sensitivita' -----------

def test_scenario_presets_are_valid_overrides():
    for name in ScenarioPresets.names():
        ov = ScenarioPresets.get(name)
        assert isinstance(ov, ScenarioOverride)
    race = ScenarioPresets.get("race")
    assert race.cda_override is not None
    assert race.experience_override == "Elite"
    # build() ritorna una copia modificata senza alterare il preset originale
    light = ScenarioPresets.build("light_bike", bike_weight_delta_kg=-3.0)
    assert light.bike_weight_delta_kg == -3.0
    assert ScenarioPresets.get("light_bike").bike_weight_delta_kg == -2.0


def test_compare_preset_changes_energy_and_summary_is_readable():
    ctx = _ctx()
    engine = SimulationEngine(ALL_ALGORITHMS)
    comp = engine.compare_preset(ctx, "race")
    assert comp.deltas["EnergyModel"] < 0  # meno massa + cda -> meno energia
    text = comp.summary()
    assert "EnergyModel:" in text
    assert "->" in text
    assert "%" in text
    assert comp.to_dict()["deltas"]["EnergyModel"] < 0


def test_compare_combined_override():
    ctx = _ctx()
    engine = SimulationEngine(ALL_ALGORITHMS)
    ov = ScenarioOverride(athlete_weight_delta_kg=-3.0, bike_weight_delta_kg=-1.0,
                          slope_delta_percent=1.0, cda_override=0.30,
                          experience_override="Elite")
    comp = engine.compare(ctx, ov)
    assert comp.deltas["EnergyModel"] < 0
    # il contratto to_dict resta valido con baseline/scenario/deltas
    d = comp.to_dict()
    assert set(d.keys()) == {"baseline", "scenario", "deltas"}


def test_sensitivity_athlete_weight_monotonic_energy():
    ctx = _ctx()
    engine = SimulationEngine(ALL_ALGORITHMS)
    sens = engine.sensitivity(ctx, "athlete_weight", [-10.0, -5.0, 0.0, 5.0])
    assert isinstance(sens, SensitivityResult)
    assert sens.param == "athlete_weight"
    assert len(sens.points) == 4
    values = [v for _, v in sens.curve("EnergyModel")]
    assert values[0] < values[1] < values[2] < values[3]  # piu' peso -> piu' energia
    assert sens.to_dict()["values"] == [-10.0, -5.0, 0.0, 5.0]


def test_sensitivity_slope_changes_energy():
    ctx = _ctx()
    engine = SimulationEngine(ALL_ALGORITHMS)
    sens = engine.sensitivity(ctx, "slope", [0.0, 2.0, 5.0, 10.0])
    energy = [v for _, v in sens.curve("EnergyModel")]
    # pendenza maggiore -> piu' lavoro gravitazionale -> piu' energia
    assert energy[0] < energy[-1]


def test_parse_override_from_text_recognizes_multiple_deltas():
    ov = parse_override_from_text("Se peso -5 kg e pendenza +2% quanto risparmio?")
    assert ov.athlete_weight_delta_kg == -5.0
    assert ov.slope_delta_percent == 2.0
    bike_ov = parse_override_from_text("con bici -1 kg e cda 0.32")
    assert bike_ov.bike_weight_delta_kg == -1.0
    assert bike_ov.cda_override == 0.32
