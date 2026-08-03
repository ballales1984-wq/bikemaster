"""Dynamic training-plan adaptation engine for BikeMaster.

This package implements the five adaptation components described in the
Adaptation Engineer agent spec:

1. ``EventDetector``      — detects state changes (skipped/longer ride, low
                            recovery, goal change, calendar/weather).
2. ``LoadRedistributor``  — spreads missing volume across remaining workouts.
3. ``RecoveryAdjuster``   — modifies the plan to protect recovery.
4. ``QualitySwap``        — trades volume for intensity when needed.
5. ``ProactiveAlert``     — emits notifications for risk / plan changes.

The orchestrator is ``AdaptationEngine`` which wires the components together
and produces an immutable, auditable ``AdaptationPlan``.

Design notes / constraints (from the agent spec, MUST be respected):
- Only FUTURE, not-yet-completed workouts are modified.
- No dangerous adaptations: a single load increase > 50% is rejected.
- Recovery days are never silently removed without a reason.
- Every adaptation is logged for audit (see ``AdaptationPlan.audit``).
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from .adaptation_rules import (
    OVERLOAD_REDUCTION_MAX,
    OVERLOAD_REDUCTION_MIN,
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

logger = logging.getLogger(__name__)

OVERLOAD_REDUCTION_DEFAULT = 0.25


class EventType(StrEnum):
    SKIPPED_RIDE = "skipped_ride"
    PARTIAL_RIDE = "partial_ride"
    LONGER_RIDE = "longer_ride"
    LOW_RECOVERY = "low_recovery"
    GOAL_CHANGE = "goal_change"
    CALENDAR_BLOCK = "calendar_block"
    BAD_WEATHER = "bad_weather"


class AdaptationStrategy(StrEnum):
    RECOVER_VOLUME = "recover_volume"
    MAINTAIN = "maintain"
    QUALITY_SWAP = "quality_swap"
    RECOVERY_ONLY = "recovery_only"
    REDUCE_OVERLOAD = "reduce_overload"


@dataclass
class AdaptationEvent:
    """A single detected change in athlete/plan state."""

    event_type: EventType
    ride_date: str | None = None
    planned_km: float = 0.0
    planned_minutes: float = 0.0
    actual_km: float = 0.0
    actual_minutes: float = 0.0
    detail: str = ""
    detected_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class LoadRedistribution:
    """Result of spreading missing volume across future workouts."""

    missing_km: float
    missing_minutes: float
    affected_workouts: list[dict[str, Any]]
    resulting_acwr: float
    safe: bool
    note: str


@dataclass
class AdaptationPlan:
    """Immutable record of one adaptation decision, including audit trail."""

    triggered_by: AdaptationEvent
    strategy: AdaptationStrategy
    original_plan: list[WorkoutPlan]
    adapted_plan: list[WorkoutPlan]
    redistribution: LoadRedistribution | None = None
    alerts: list[str] = field(default_factory=list)
    rationale: str = ""
    audit: dict[str, Any] = field(
        default_factory=lambda: {
            "generated_at": datetime.now(UTC).isoformat(),
            "engine": "AdaptationEngine",
        }
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "triggered_by": self.triggered_by.event_type.value,
            "strategy": self.strategy.value,
            "rationale": self.rationale,
            "alerts": list(self.alerts),
            "redistribution": asdict(self.redistribution) if self.redistribution else None,
            "original_plan": [asdict(w) for w in self.original_plan],
            "adapted_plan": [asdict(w) for w in self.adapted_plan],
            "audit": self.audit,
        }


class EventDetector:
    """Detects adaptation-triggering events from athlete/plan signals."""

    def detect_skipped(self, ride_date: str, planned: WorkoutPlan) -> AdaptationEvent:
        return AdaptationEvent(
            event_type=EventType.SKIPPED_RIDE,
            ride_date=ride_date,
            planned_km=planned.distance_km,
            planned_minutes=planned.duration_minutes,
            actual_km=0.0,
            actual_minutes=0.0,
            detail=f"Uscita {ride_date} saltata ({planned.distance_km} km previsti).",
        )

    def detect_partial(
        self, ride_date: str, planned: WorkoutPlan, actual_km: float, actual_minutes: float
    ) -> AdaptationEvent:
        return AdaptationEvent(
            event_type=EventType.PARTIAL_RIDE,
            ride_date=ride_date,
            planned_km=planned.distance_km,
            planned_minutes=planned.duration_minutes,
            actual_km=actual_km,
            actual_minutes=actual_minutes,
            detail=f"Uscita {ride_date} parziale: {actual_km}/{planned.distance_km} km.",
        )

    def detect_longer(
        self, ride_date: str, planned: WorkoutPlan, actual_km: float, actual_minutes: float
    ) -> AdaptationEvent:
        return AdaptationEvent(
            event_type=EventType.LONGER_RIDE,
            ride_date=ride_date,
            planned_km=planned.distance_km,
            planned_minutes=planned.duration_minutes,
            actual_km=actual_km,
            actual_minutes=actual_minutes,
            detail=f"Uscita {ride_date} piu lunga del previsto: {actual_km} vs {planned.distance_km} km.",
        )

    def detect_low_recovery(self, state: AthleteState) -> AdaptationEvent:
        return AdaptationEvent(
            event_type=EventType.LOW_RECOVERY,
            planned_km=0.0,
            planned_minutes=0.0,
            detail=(
                f"Recupero insufficiente: fatigue={state.fatigue_score}, "
                f"readiness={state.readiness}, tsb={state.tsb}."
            ),
        )

    def detect_goal_change(self, detail: str) -> AdaptationEvent:
        return AdaptationEvent(
            event_type=EventType.GOAL_CHANGE,
            detail=detail,
        )

    def detect_calendar_block(self, ride_date: str, detail: str) -> AdaptationEvent:
        return AdaptationEvent(
            event_type=EventType.CALENDAR_BLOCK,
            ride_date=ride_date,
            detail=detail,
        )

    def detect_bad_weather(self, ride_date: str, detail: str) -> AdaptationEvent:
        return AdaptationEvent(
            event_type=EventType.BAD_WEATHER,
            ride_date=ride_date,
            detail=detail,
        )


class LoadRedistributor:
    """Spreads missing volume across future available workouts safely."""

    def redistribute(
        self,
        planned: list[WorkoutPlan],
        skipped_index: int,
        state: AthleteState,
        current_acute_load: float = 0.0,
    ) -> LoadRedistribution:
        miss_km, miss_min = missing_volume(planned, skipped_index)
        targets = available_future_workouts(planned, skipped_index)

        if not targets:
            return LoadRedistribution(
                missing_km=miss_km,
                missing_minutes=miss_min,
                affected_workouts=[],
                resulting_acwr=state.acwr,
                safe=True,
                note="Nessuna uscita futura disponibile: recupero preferito al recupero di volume.",
            )

        shares = distribute_volume_evenly(miss_km, miss_min, targets)
        affected: list[dict[str, Any]] = []
        extra_load = 0.0
        for w in targets:
            km, mins = shares[id(w)]
            extra_load += km
            affected.append({"date": w.date, "add_km": km, "add_minutes": mins, "workout_type": w.workout_type})

        proposed_acute = current_acute_load + extra_load
        safe = not is_sudden_load_spike(current_acute_load, proposed_acute)
        resulting_acwr = evaluate_acwr(proposed_acute, max(state.ctl, 1.0))

        return LoadRedistribution(
            missing_km=miss_km,
            missing_minutes=miss_min,
            affected_workouts=affected,
            resulting_acwr=resulting_acwr,
            safe=safe,
            note=("Ridistribuzione sicura." if safe else "Ridistribuzione rifiutata: incremento di carico > 50%."),
        )


class RecoveryAdjuster:
    """Modifies the plan to protect recovery given athlete state."""

    def adjust(
        self,
        planned: list[WorkoutPlan],
        state: AthleteState,
        from_index: int = 0,
    ) -> tuple[list[WorkoutPlan], list[str]]:
        alerts: list[str] = []
        adjusted = list(planned)

        if recovery_priority(state):
            alerts.append("Priorita recupero: TSB basso o fatica alta. Rimosso/ridotto carico futuro.")
            for i, w in enumerate(adjusted):
                if i >= from_index and not w.locked:
                    adjusted[i] = enforce_recovery_day(w)
            return adjusted, alerts

        reduction = recommend_volume_reduction(state.acwr)
        if reduction > 0:
            alerts.append(f"ACWR {state.acwr} alto: volume ridotto del {int(reduction * 100)}%.")
            for i, w in enumerate(adjusted):
                if i >= from_index and not w.locked and not w.is_recovery:
                    adjusted[i] = apply_overload_reduction(w, reduction)

        if needs_intensity_cut(state):
            alerts.append("Readiness bassa: intensita ridotta nelle uscite future.")
            for i, w in enumerate(adjusted):
                if i >= from_index and not w.locked and not w.is_recovery:
                    lowered = WorkoutPlan(**{**asdict(w), "intensity_factor": max(0.4, w.intensity_factor - 0.1)})
                    adjusted[i] = lowered

        return adjusted, alerts


class QualitySwap:
    """Trades volume for intensity instead of accumulating distance."""

    def swap(self, planned: list[WorkoutPlan], from_index: int) -> tuple[list[WorkoutPlan], WorkoutPlan | None]:
        for i, w in enumerate(planned):
            if i >= from_index and not w.locked and w.workout_type in ("endurance", "long_ride", "base"):
                swapped = quality_swap_target(w)
                new_plan = list(planned)
                new_plan[i] = swapped
                return new_plan, swapped
        return planned, None


class ProactiveAlert:
    """Generates notifications only when message value exceeds disturbance."""

    def check_overload(self, acwr: float) -> str | None:
        if acwr > 1.5:
            return f"Rischio sovraccarico: ACWR {acwr} oltre la soglia 1.5."
        return None

    def check_recovery(self, state: AthleteState) -> str | None:
        if state.tsb < -30:
            return f"Recupero insufficiente: TSB {state.tsb} sotto -30."
        if state.fatigue_score >= 7:
            return f"Fatica elevata ({state.fatigue_score}): previsto scarico."
        return None

    def check_plan_change(self, strategy: AdaptationStrategy) -> str | None:
        if strategy in (AdaptationStrategy.RECOVER_VOLUME, AdaptationStrategy.QUALITY_SWAP):
            return f"Modifica importante del piano proposta: strategia {strategy.value}."
        return None

    def collect(self, state: AthleteState, acwr: float, strategy: AdaptationStrategy) -> list[str]:
        alerts: list[str] = []
        for fn in (self.check_overload, self.check_recovery):
            msg = fn(state) if fn is self.check_recovery else self.check_overload(acwr)
            if msg:
                alerts.append(msg)
        plan_msg = self.check_plan_change(strategy)
        if plan_msg:
            alerts.append(plan_msg)
        return alerts


class AdaptationEngine:
    """Orchestrates the five components and emits an auditable AdaptationPlan."""

    def __init__(self) -> None:
        self.detector = EventDetector()
        self.redistributor = LoadRedistributor()
        self.recovery = RecoveryAdjuster()
        self.quality = QualitySwap()
        self.alerts = ProactiveAlert()

    def _clone(self, planned: list[WorkoutPlan]) -> list[WorkoutPlan]:
        return [WorkoutPlan(**asdict(w)) for w in planned]

    # --- Scenario 1: skipped ride -> three solutions -------------------------
    def adapt_skipped_ride(
        self,
        planned: list[WorkoutPlan],
        skipped_index: int,
        state: AthleteState,
        current_acute_load: float = 0.0,
    ) -> AdaptationPlan:
        event = self.detector.detect_skipped(planned[skipped_index].date, planned[skipped_index])
        original = self._clone(planned)
        redistribution = self.redistributor.redistribute(planned, skipped_index, state, current_acute_load)

        alerts = self.alerts.collect(state, redistribution.resulting_acwr, AdaptationStrategy.RECOVER_VOLUME)

        if recovery_priority(state):
            strategy = AdaptationStrategy.RECOVERY_ONLY
            adapted, rec_alerts = self.recovery.adjust(planned, state, skipped_index)
            alerts.extend(rec_alerts)
            rationale = "Recupero prioritario: volume non recuperato, piano convertito in scarico."
        elif not redistribution.safe:
            strategy = AdaptationStrategy.MAINTAIN
            adapted = self._clone(planned)
            rationale = "Ridistribuzione rifiutata (carico > 50%): piano mantenuto."
        else:
            strategy = AdaptationStrategy.RECOVER_VOLUME
            adapted = self._clone(planned)
            for w in adapted:
                if (
                    any(a["date"] == w.date for a in redistribution.affected_workouts)
                    and not w.locked
                    and not w.is_recovery
                ):
                    share = next(a for a in redistribution.affected_workouts if a["date"] == w.date)
                    w.distance_km = round(w.distance_km + share["add_km"], 1)
                    w.duration_minutes = round(w.duration_minutes + share["add_minutes"], 1)
            rationale = "Volume mancante ridistribuito sulle uscite future disponibili."

        return AdaptationPlan(
            triggered_by=event,
            strategy=strategy,
            original_plan=original,
            adapted_plan=adapted,
            redistribution=redistribution,
            alerts=alerts,
            rationale=rationale,
        )

    # --- Scenario 2: longer ride -> reduce next -----------------------------
    def adapt_longer_ride(
        self,
        planned: list[WorkoutPlan],
        index: int,
        actual_km: float,
        actual_minutes: float,
        state: AthleteState,
    ) -> AdaptationPlan:
        event = self.detector.detect_longer(planned[index].date, planned[index], actual_km, actual_minutes)
        original = self._clone(planned)
        overload = max(0.0, actual_km - planned[index].distance_km)
        reduction = min(max(OVERLOAD_REDUCTION_DEFAULT, OVERLOAD_REDUCTION_MIN), OVERLOAD_REDUCTION_MAX)

        adapted = self._clone(planned)
        for i, w in enumerate(adapted):
            if i > index and not w.locked and not w.is_recovery:
                adapted[i] = apply_overload_reduction(w, reduction)
                break

        alerts = self.alerts.collect(state, state.acwr, AdaptationStrategy.REDUCE_OVERLOAD)
        alerts.append(
            f"Uscita piu lunga del {round(overload, 1)} km: prossima uscita ridotta del {int(reduction * 100)}%."
        )
        rationale = "Sovraccarico aggiuntivo assorbito riducendo la prossima uscita del 20-30%."

        return AdaptationPlan(
            triggered_by=event,
            strategy=AdaptationStrategy.REDUCE_OVERLOAD,
            original_plan=original,
            adapted_plan=adapted,
            alerts=alerts,
            rationale=rationale,
        )

    # --- Scenario 3: insufficient recovery -> deload ------------------------
    def adapt_low_recovery(
        self,
        planned: list[WorkoutPlan],
        state: AthleteState,
        from_index: int = 0,
    ) -> AdaptationPlan:
        event = self.detector.detect_low_recovery(state)
        original = self._clone(planned)
        adapted, rec_alerts = self.recovery.adjust(planned, state, from_index)
        alerts = self.alerts.collect(state, state.acwr, AdaptationStrategy.RECOVERY_ONLY)
        alerts.extend(rec_alerts)
        rationale = "Recupero insufficiente: prossima uscita sostituita con scarico attivo, piano ricalcolato."

        return AdaptationPlan(
            triggered_by=event,
            strategy=AdaptationStrategy.RECOVERY_ONLY,
            original_plan=original,
            adapted_plan=adapted,
            alerts=alerts,
            rationale=rationale,
        )

    # --- Quality swap entrypoint -------------------------------------------
    def adapt_quality_swap(
        self,
        planned: list[WorkoutPlan],
        state: AthleteState,
        from_index: int = 0,
    ) -> AdaptationPlan:
        event = AdaptationEvent(
            event_type=EventType.LOW_RECOVERY,
            detail="Qualita al posto del volume per vincoli di tempo/energia.",
        )
        original = self._clone(planned)
        adapted, swapped = self.quality.swap(planned, from_index)
        alerts = self.alerts.collect(state, state.acwr, AdaptationStrategy.QUALITY_SWAP)
        rationale = (
            f"Sostituita uscita di volume con qualita: {swapped.workout_type} {swapped.distance_km} km."
            if swapped
            else "Nessuna uscita di volume sostituibile: piano mantenuto."
        )
        return AdaptationPlan(
            triggered_by=event,
            strategy=AdaptationStrategy.QUALITY_SWAP,
            original_plan=original,
            adapted_plan=adapted,
            alerts=alerts,
            rationale=rationale,
        )


OVERLOAD_REDUCTION_DEFAULT = 0.25


__all__ = [
    "EventType",
    "AdaptationStrategy",
    "AdaptationEvent",
    "LoadRedistribution",
    "AdaptationPlan",
    "EventDetector",
    "LoadRedistributor",
    "RecoveryAdjuster",
    "QualitySwap",
    "ProactiveAlert",
    "AdaptationEngine",
    "AthleteState",
    "WorkoutPlan",
]
