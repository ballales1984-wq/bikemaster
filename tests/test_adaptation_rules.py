"""Unit tests for the pure adaptation rules engine (no I/O, no infra)."""


from bike_analyzer.backend.analytics.adaptation_rules import (
    AthleteState,
    WorkoutPlan,
    apply_overload_reduction,
    available_future_workouts,
    distribute_volume_evenly,
    enforce_recovery_day,
    evaluate_acwr,
    is_sudden_load_spike,
    missing_volume,
    needs_intensity_cut,
    quality_swap_target,
    recommend_volume_reduction,
    recovery_priority,
)


def _plan(distance_km=50.0, duration_minutes=120.0, workout_type="endurance", **kw):
    return WorkoutPlan(date="2024-06-01", workout_type=workout_type, distance_km=distance_km, duration_minutes=duration_minutes, **kw)


def test_missing_volume_out_of_range():
    plans = [_plan()]
    assert missing_volume(plans, -1) == (0.0, 0.0)
    assert missing_volume(plans, 5) == (0.0, 0.0)


def test_missing_volume_returns_target():
    plans = [_plan(distance_km=40.0, duration_minutes=90.0)]
    assert missing_volume(plans, 0) == (40.0, 90.0)


def test_available_future_workouts_excludes_recovery_and_locked():
    plans = [
        _plan(workout_type="endurance"),
        _plan(workout_type="recovery", is_recovery=True),
        _plan(workout_type="endurance", locked=True),
        _plan(workout_type="endurance"),
    ]
    future = available_future_workouts(plans, skipped_index=0)
    assert [w.workout_type for w in future] == ["endurance"]


def test_available_future_workouts_empty_when_none():
    plans = [_plan()]
    assert available_future_workouts(plans, skipped_index=0) == []


def test_distribute_volume_evenly_capacity_aware():
    targets = [_plan(distance_km=100.0), _plan(distance_km=50.0)]
    out = distribute_volume_evenly(30.0, 60.0, targets)
    assert len(out) == 2
    total_km = sum(v[0] for v in out.values())
    total_min = sum(v[1] for v in out.values())
    assert round(total_km, 1) == 30.0
    assert round(total_min, 1) == 60.0


def test_distribute_volume_evenly_empty():
    assert distribute_volume_evenly(10.0, 20.0, []) == {}


def test_evaluate_acwr_safe_and_spike():
    assert evaluate_acwr(0.0, 0.0) == 1.0
    assert evaluate_acwr(0.0, 100.0) == 0.0
    assert evaluate_acwr(150.0, 100.0) == 1.5
    assert evaluate_acwr(250.0, 100.0) > 1.5


def test_is_sudden_load_spike():
    assert not is_sudden_load_spike(0.0, 100.0)
    assert not is_sudden_load_spike(100.0, 140.0)
    assert is_sudden_load_spike(100.0, 160.0)


def test_recommend_volume_reduction_zero_when_safe():
    assert recommend_volume_reduction(1.2) == 0.0
    assert recommend_volume_reduction(1.5) == 0.0
    assert 0.2 <= recommend_volume_reduction(2.0) <= 0.3


def test_recovery_priority_thresholds():
    assert recovery_priority(AthleteState(tsb=-35.0)) is True
    assert recovery_priority(AthleteState(fatigue_score=8.0)) is True
    assert recovery_priority(AthleteState(readiness=40.0)) is True
    assert recovery_priority(AthleteState(tsb=0.0, fatigue_score=2.0, readiness=90.0)) is False


def test_needs_intensity_cut():
    assert needs_intensity_cut(AthleteState(readiness=60.0, tsb=-20.0)) is True
    assert needs_intensity_cut(AthleteState(readiness=80.0, tsb=0.0)) is False


def test_quality_swap_target_shortens_and_intensifies():
    original = _plan(distance_km=80.0, duration_minutes=200.0, intensity_factor=0.6)
    swapped = quality_swap_target(original)
    assert swapped.workout_type == "intervals"
    assert swapped.distance_km < original.distance_km
    assert swapped.duration_minutes < original.duration_minutes
    assert swapped.intensity_factor > original.intensity_factor


def test_apply_overload_reduction_scales_volume():
    w = _plan(distance_km=100.0, duration_minutes=100.0)
    reduced = apply_overload_reduction(w, 0.25)
    assert reduced.distance_km == 75.0
    assert reduced.duration_minutes == 75.0


def test_enforce_recovery_day_forces_recovery():
    w = _plan(distance_km=100.0, duration_minutes=180.0)
    rec = enforce_recovery_day(w)
    assert rec.is_recovery is True
    assert rec.workout_type == "recovery"
    assert rec.distance_km < w.distance_km
