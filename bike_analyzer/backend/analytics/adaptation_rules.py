"""Pure, testable rules for the dynamic training-plan adaptation engine.

This module contains stateless functions only — no I/O, no imports from
infrastructure. Every function takes plain values (floats, dataclasses) and
returns plain values or dataclasses so the logic can be unit tested in
isolation and reused by the orchestrating services in ``adaptation_engine.py``.

Thresholds follow the BikeMaster adaptation spec:
- ACWR (Acute:Chronic Workload Ratio) > 1.5 -> reduce volume 20-30%
- TSB (Training Stress Balance) < -30 -> recovery priority
- Sudden load spike > 50% -> unsafe, rejected
"""

from __future__ import annotations

from dataclasses import dataclass

ACWR_SPIKE_UNSAFE = 0.50
ACWR_HIGH_RISK = 1.5
TSB_RECOVERY_PRIORITY = -30.0
TSB_FATIGUE_LOW = -10.0
OVERLOAD_REDUCTION_MIN = 0.20
OVERLOAD_REDUCTION_MAX = 0.30
SKIPPED_RECOVERY_PREFERENCE = 0.0


@dataclass
class WorkoutPlan:
    """A single future, not-yet-completed planned workout."""

    date: str
    workout_type: str
    distance_km: float = 0.0
    duration_minutes: float = 0.0
    intensity_factor: float = 0.6
    title: str = ""
    description: str = ""
    is_recovery: bool = False
    locked: bool = False


@dataclass
class AthleteState:
    """Current physiological state of the athlete used for adaptation."""

    fatigue_score: float = 0.0
    readiness: float = 100.0
    acwr: float = 1.0
    tsb: float = 0.0
    atl: float = 0.0
    ctl: float = 0.0


def missing_volume(planned: list[WorkoutPlan], skipped_index: int) -> tuple[float, float]:
    """Return (missing_km, missing_minutes) for a skipped workout."""
    if skipped_index < 0 or skipped_index >= len(planned):
        return 0.0, 0.0
    target = planned[skipped_index]
    return float(target.distance_km), float(target.duration_minutes)


def available_future_workouts(
    planned: list[WorkoutPlan], skipped_index: int
) -> list[WorkoutPlan]:
    """Future non-recovery, non-locked workouts that can absorb load."""
    return [
        w
        for i, w in enumerate(planned)
        if i > skipped_index and not w.locked and not w.is_recovery
    ]


def distribute_volume_evenly(
    total_km: float, total_min: float, targets: list[WorkoutPlan]
) -> dict[int, tuple[float, float]]:
    """Distribute missing km/min proportionally across targets by their capacity.

    Proportion uses each target's current distance_km (capacity-aware). Recovery
    and locked workouts are excluded by the caller.
    """
    if not targets:
        return {}
    capacity = [max(w.distance_km, 0.1) for w in targets]
    total_cap = sum(capacity) or 1.0
    out: dict[int, tuple[float, float]] = {}
    for idx, w in enumerate(targets):
        share = capacity[idx] / total_cap
        out[id(w)] = (round(total_km * share, 1), round(total_min * share, 1))
    return out


def evaluate_acwr(acute_load: float, chronic_load: float) -> float:
    """Compute Acute:Chronic Workload Ratio (ACWR)."""
    if chronic_load <= 0:
        return 1.0 if acute_load <= 0 else 2.0
    return round(acute_load / chronic_load, 3)


def is_sudden_load_spike(current_load: float, proposed_load: float) -> bool:
    """True if proposed load increases total acute load by > 50% at once."""
    if current_load <= 0:
        return False
    return (proposed_load - current_load) / current_load > ACWR_SPIKE_UNSAFE


def recommend_volume_reduction(acwr: float) -> float:
    """Return fraction (0-1) to reduce volume when ACWR exceeds safe ceiling."""
    if acwr <= ACWR_HIGH_RISK:
        return 0.0
    excess = (acwr - ACWR_HIGH_RISK) / ACWR_HIGH_RISK
    reduction = OVERLOAD_REDUCTION_MIN + min(excess, 1.0) * (
        OVERLOAD_REDUCTION_MAX - OVERLOAD_REDUCTION_MIN
    )
    return round(min(reduction, OVERLOAD_REDUCTION_MAX), 3)


def recovery_priority(state: AthleteState) -> bool:
    """True when athlete state demands recovery over volume accumulation."""
    return state.tsb < TSB_RECOVERY_PRIORITY or state.fatigue_score >= 7.0 or state.readiness < 50.0


def needs_intensity_cut(state: AthleteState) -> bool:
    """True when readiness is low but not yet full recovery priority."""
    return state.readiness < 70.0 and state.tsb < TSB_FATIGUE_LOW


def quality_swap_target(original: WorkoutPlan) -> WorkoutPlan:
    """Swap a long endurance workout for a short, high-quality interval session.

    Keeps total training stimulus comparable while cutting duration/volume so
    the athlete still trains even under time/energy pressure.
    """
    short_duration = max(40.0, original.duration_minutes * 0.6)
    return WorkoutPlan(
        date=original.date,
        workout_type="intervals",
        distance_km=round(original.distance_km * 0.5, 1),
        duration_minutes=round(short_duration, 1),
        intensity_factor=min(0.95, original.intensity_factor + 0.3),
        title="Qualità — intervalli brevi",
        description="Sostituzione volume con qualità: intervalli intensi al posto del fondo lungo.",
        is_recovery=False,
        locked=original.locked,
    )


def apply_overload_reduction(workout: WorkoutPlan, reduction: float) -> WorkoutPlan:
    """Return a copy of workout with volume reduced by ``reduction`` fraction."""
    return WorkoutPlan(
        date=workout.date,
        workout_type=workout.workout_type,
        distance_km=round(workout.distance_km * (1.0 - reduction), 1),
        duration_minutes=round(workout.duration_minutes * (1.0 - reduction), 1),
        intensity_factor=workout.intensity_factor,
        title=workout.title,
        description=workout.description,
        is_recovery=workout.is_recovery,
        locked=workout.locked,
    )


def enforce_recovery_day(workout: WorkoutPlan) -> WorkoutPlan:
    """Force a planned workout to become an active-recovery spin."""
    return WorkoutPlan(
        date=workout.date,
        workout_type="recovery",
        distance_km=round(max(10.0, workout.distance_km * 0.25), 1),
        duration_minutes=40.0,
        intensity_factor=0.4,
        title="Recupero attivo",
        description="Giorno di scarico imposto per recupero insufficiente.",
        is_recovery=True,
        locked=workout.locked,
    )
