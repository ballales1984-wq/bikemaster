"""Adaptation Engine - modifies training plans in real time based on events."""

from __future__ import annotations

from typing import Any

from .adaptation_rules import AdaptationRules
from .models import AdaptationEvent, AdaptationEventType, PlanConstraints, TrainingGoal, WeeklyPlan


class AdaptationEngine:
    """Orchestrates plan adaptation when real-world events occur.

    Takes a current plan, an event, and the updated fitness state,
    applies the appropriate rule, and returns the modified plan.
    """

    def __init__(self, athlete: Any, ftp: float | None = None):
        self.athlete = athlete
        self.ftp = ftp or getattr(athlete, "ftp_watts", None) or 250.0

    def adapt(
        self,
        plan: WeeklyPlan,
        event: AdaptationEvent,
        constraints: PlanConstraints,
        goal: TrainingGoal,
    ) -> WeeklyPlan:
        """Apply adaptation to plan based on event.

        Returns the modified WeeklyPlan. Future-only: only dates >= event
        date are modified; past workouts remain unchanged.
        """
        return AdaptationRules.apply(event, plan)

    def should_notify(self, plan: WeeklyPlan, event: AdaptationEvent) -> tuple[bool, str]:
        """Return (should_notify, message) if the event requires athlete notification."""
        if event.event_type == AdaptationEventType.INJURY:
            return True, "Attenzione: modificato il piano per mantenimento senza impatto."
        if event.event_type == AdaptationEventType.RECOVERY_INSUFFICIENT:
            return True, "Recupero insufficiente: ridotto il carico per i prossimi allenamenti."
        if event.event_type == AdaptationEventType.STRAVA:
            extra_tss = event.actual_data.get("tss", 0) - (event.planned_workout.estimated_tss if event.planned_workout else 0)
            if extra_tss > 50:
                return True, f"Sforzo aggiuntivo di {extra_tss:.0f} TSS: ridotto il carico successivo."
        return False, ""

    def rebuild_remaining_week(
        self,
        plan: WeeklyPlan,
        event: AdaptationEvent,
        goal: TrainingGoal,
        constraints: PlanConstraints,
        generator: Any,
    ) -> WeeklyPlan:
        """Rebuild workouts from event date onward using generator."""
        remaining_dates = [d.date for d in plan.days if d.date >= event.occurred_date]
        if not remaining_dates:
            return plan

        start = __import__("datetime").datetime.strptime(remaining_dates[0], "%Y-%m-%d")
        new_workouts = generator.generate_for_week(goal=goal, constraints=constraints, start_date=start)
        combined = []
        for d in plan.days:
            if d.date < event.occurred_date:
                combined.append(d)
        combined.extend(new_workouts)
        return plan.model_copy(update={"days": combined, "total_tss": round(sum(d.estimated_tss for d in combined), 1)})


__all__ = ["AdaptationEngine"]
