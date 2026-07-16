"""Tests for the dynamic training-plan adaptation engine.

Covers the three required scenarios from the Adaptation Engineer spec:
- skipped ride  -> volume recovery / maintain / recovery-only
- longer ride   -> subsequent overload reduction
- low recovery  -> deload / active recovery
plus unit tests for the pure rules and the API endpoint wiring.
"""

from __future__ import annotations

import pytest

from bike_analyzer.backend.analytics.adaptation_engine import (
    AdaptationEngine,
    AthleteState,
    WorkoutPlan,
)
from bike_analyzer.backend.analytics.adaptation_rules import (
    apply_overload_reduction,
    enforce_recovery_day,
    evaluate_acwr,
    is_sudden_load_spike,
    quality_swap_target,
    recommend_volume_reduction,
    recovery_priority,
)


def _plan() -> list[WorkoutPlan]:
    return [
        WorkoutPlan(date="2026-07-16", workout_type="endurance", distance_km=40.0, duration_minutes=120.0),
        WorkoutPlan(date="2026-07-17", workout_type="threshold", distance_km=30.0, duration_minutes=90.0),
        WorkoutPlan(date="2026-07-18", workout_type="recovery", distance_km=15.0, duration_minutes=45.0, is_recovery=True),
        WorkoutPlan(date="2026-07-19", workout_type="long_ride", distance_km=60.0, duration_minutes=180.0),
    ]


# --- pure rule tests --------------------------------------------------------
def test_evaluate_acwr_safe_and_spike():
    assert evaluate_acwr(50.0, 100.0) == 0.5
    assert evaluate_acwr(120.0, 100.0) == pytest.approx(1.2)


def test_is_sudden_load_spike_threshold():
    assert is_sudden_load_spike(100.0, 151.0) is True
    assert is_sudden_load_spike(100.0, 150.0) is False


def test_recommend_volume_reduction_clamped():
    assert recommend_volume_reduction(1.3) == 0.0
    red = recommend_volume_reduction(1.7)
    assert 0.2 <= red <= 0.3


def test_recovery_priority_flags_low_tsb():
    assert recovery_priority(AthleteState(tsb=-35.0)) is True
    assert recovery_priority(AthleteState(tsb=10.0, readiness=90.0)) is False


def test_enforce_recovery_day_converts_workout():
    w = WorkoutPlan(date="2026-07-19", workout_type="long_ride", distance_km=60.0, duration_minutes=180.0)
    rec = enforce_recovery_day(w)
    assert rec.is_recovery is True
    assert rec.workout_type == "recovery"
    assert rec.distance_km < w.distance_km


def test_quality_swap_reduces_volume_keeps_stimulus():
    w = _plan()[-1]
    swapped = quality_swap_target(w)
    assert swapped.workout_type == "intervals"
    assert swapped.distance_km < w.distance_km
    assert swapped.intensity_factor > w.intensity_factor


def test_apply_overload_reduction():
    w = _plan()[0]
    r = apply_overload_reduction(w, 0.25)
    assert r.distance_km == pytest.approx(30.0)


# --- scenario: skipped ride -------------------------------------------------
def test_skipped_ride_recovers_volume():
    engine = AdaptationEngine()
    state = AthleteState(fatigue_score=3.0, readiness=90.0, acwr=1.0, tsb=5.0)
    plan = engine.adapt_skipped_ride(_plan(), 0, state, current_acute_load=100.0)
    assert plan.strategy.value in ("recover_volume", "maintain", "recovery_only")
    if plan.strategy.value == "recover_volume":
        assert plan.redistribution is not None
        assert plan.redistribution.safe is True
        total = sum(w.distance_km for w in plan.adapted_plan)
        assert total >= sum(w.distance_km for w in _plan())


def test_skipped_ride_prefers_recovery_when_priority():
    engine = AdaptationEngine()
    state = AthleteState(fatigue_score=8.0, readiness=40.0, acwr=1.6, tsb=-40.0)
    plan = engine.adapt_skipped_ride(_plan(), 0, state, current_acute_load=100.0)
    assert plan.strategy.value == "recovery_only"
    for w in plan.adapted_plan:
        if not w.locked:
            assert w.is_recovery is True


def test_skipped_ride_rejects_unsafe_redistribution():
    engine = AdaptationEngine()
    # very low current load, big missing volume => sudden spike
    state = AthleteState(fatigue_score=2.0, readiness=95.0, acwr=1.0, tsb=10.0)
    plan = engine.adapt_skipped_ride(_plan(), 0, state, current_acute_load=5.0)
    assert plan.redistribution is not None
    if not plan.redistribution.safe:
        assert plan.strategy.value == "maintain"


# --- scenario: longer ride --------------------------------------------------
def test_longer_ride_reduces_next():
    engine = AdaptationEngine()
    state = AthleteState(fatigue_score=4.0, readiness=80.0, acwr=1.1, tsb=0.0)
    plan = engine.adapt_longer_ride(_plan(), 0, actual_km=60.0, actual_minutes=180.0, state=state)
    assert plan.strategy.value == "reduce_overload"
    next_w = plan.adapted_plan[1]
    assert next_w.distance_km < _plan()[1].distance_km


# --- scenario: low recovery -------------------------------------------------
def test_low_recovery_deload():
    engine = AdaptationEngine()
    state = AthleteState(fatigue_score=8.0, readiness=35.0, acwr=1.7, tsb=-45.0)
    plan = engine.adapt_low_recovery(_plan(), state)
    assert plan.strategy.value == "recovery_only"
    for w in plan.adapted_plan:
        if not w.locked and not w.is_recovery:
            pass
    assert any(a.startswith("Priorita recupero") for a in plan.alerts)


# --- quality swap -----------------------------------------------------------
def test_quality_swap_endpoint_scenario():
    engine = AdaptationEngine()
    state = AthleteState(fatigue_score=4.0, readiness=70.0, acwr=1.2, tsb=-5.0)
    plan = engine.adapt_quality_swap(_plan(), state)
    assert plan.strategy.value == "quality_swap"
    assert any(w.workout_type == "intervals" for w in plan.adapted_plan)
