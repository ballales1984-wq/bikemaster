"""Adaptation Rules - pure functions for plan adaptation logic."""

from __future__ import annotations

from typing import Any

from .models import AdaptationEvent, AdaptationEventType, WeeklyPlan, Workout


class AdaptationRules:
    """Pure rules that modify workout parameters based on adaptation events.

    Rules are stateless and deterministic - they do not depend on global state.
    """

    @staticmethod
    def apply(event: AdaptationEvent, plan: WeeklyPlan) -> WeeklyPlan:
        """Apply adaptation rule to plan and return modified plan."""
        if event.event_type == AdaptationEventType.SKIPPED:
            return AdaptationRules._rule_skipped(event, plan)
        if event.event_type == AdaptationEventType.MODIFIED:
            return AdaptationRules._rule_modified(event, plan)
        if event.event_type == AdaptationEventType.STRAVA:
            return AdaptationRules._rule_strava(event, plan)
        if event.event_type == AdaptationEventType.RECOVERY_INSUFFICIENT:
            return AdaptationRules._rule_recovery_insufficient(event, plan)
        if event.event_type == AdaptationEventType.IMPROVEMENT:
            return AdaptationRules._rule_improvement(event, plan)
        if event.event_type == AdaptationEventType.INJURY:
            return AdaptationRules._rule_injury(event, plan)
        return plan

    @staticmethod
    def _rule_skipped(event: AdaptationEvent, plan: WeeklyPlan) -> WeeklyPlan:
        missed_tss = 0.0
        if event.planned_workout:
            missed_tss = event.planned_workout.estimated_tss
        remaining_days = [d for d in plan.days if d.date >= event.occurred_date and d.workout_type.value != "recovery"]
        if not remaining_days:
            return plan
        extra_per_ride = missed_tss / len(remaining_days)
        new_days = []
        for d in plan.days:
            if d.date >= event.occurred_date and d.workout_type.value != "recovery":
                d = d.model_copy(update={
                    "duration_minutes": min(300, d.duration_minutes + int(extra_per_ride / 60.0 * 10)),
                    "estimated_tss": round(d.estimated_tss + extra_per_ride, 1),
                })
            new_days.append(d)
        return plan.model_copy(update={"days": new_days, "total_tss": round(sum(d.estimated_tss for d in new_days), 1)})

    @staticmethod
    def _rule_modified(event: AdaptationEvent, plan: WeeklyPlan) -> WeeklyPlan:
        actual = event.actual_data or {}
        actual_tss = float(actual.get("tss", 0))
        new_days = []
        for d in plan.days:
            if d.date == event.occurred_date:
                d = d.model_copy(update={
                    "duration_minutes": actual.get("duration_minutes", d.duration_minutes),
                    "estimated_tss": actual_tss,
                    "notes": (d.notes or "") + " [modificato]",
                })
            new_days.append(d)
        return plan.model_copy(update={"days": new_days, "total_tss": round(sum(d.estimated_tss for d in new_days), 1)})

    @staticmethod
    def _rule_strava(event: AdaptationEvent, plan: WeeklyPlan) -> WeeklyPlan:
        actual = event.actual_data or {}
        actual_tss = float(actual.get("tss", 0))
        extra = max(0.0, actual_tss - (event.planned_workout.estimated_tss if event.planned_workout else 0))
        new_days = []
        for d in plan.days:
            if d.date > event.occurred_date:
                if d.workout_type.value == "recovery":
                    d = d.model_copy(update={"duration_minutes": max(20, int(d.duration_minutes * 0.8)), "estimated_tss": round(d.estimated_tss * 0.8, 1), "notes": (d.notes or "") + " [scarico post-sforzo]"})
                else:
                    d = d.model_copy(update={"duration_minutes": max(20, d.duration_minutes - int(extra / 3)), "estimated_tss": round(max(0, d.estimated_tss - extra / 3), 1)})
            new_days.append(d)
        return plan.model_copy(update={"days": new_days, "total_tss": round(sum(d.estimated_tss for d in new_days), 1)})

    @staticmethod
    def _rule_recovery_insufficient(event: AdaptationEvent, plan: WeeklyPlan) -> WeeklyPlan:
        new_days = []
        for d in plan.days:
            if d.date >= event.occurred_date and d.workout_type.value not in ("recovery",):
                d = d.model_copy(update={"duration_minutes": max(20, int(d.duration_minutes * 0.7)), "estimated_tss": round(d.estimated_tss * 0.7, 1), "notes": (d.notes or "") + " [scarico forzato recupero]"})
            new_days.append(d)
        return plan.model_copy(update={"days": new_days, "total_tss": round(sum(d.estimated_tss for d in new_days), 1)})

    @staticmethod
    def _rule_improvement(event: AdaptationEvent, plan: WeeklyPlan) -> WeeklyPlan:
        actual = event.actual_data or {}
        boost = float(actual.get("tss", 0)) * 0.05
        new_days = []
        for d in plan.days:
            if d.date > event.occurred_date:
                d = d.model_copy(update={"duration_minutes": min(300, d.duration_minutes + 5), "estimated_tss": round(d.estimated_tss + boost, 1)})
            new_days.append(d)
        return plan.model_copy(update={"days": new_days, "total_tss": round(sum(d.estimated_tss for d in new_days), 1)})

    @staticmethod
    def _rule_injury(event: AdaptationEvent, plan: WeeklyPlan) -> WeeklyPlan:
        for d in plan.days:
            if d.date >= event.occurred_date:
                d.workout_type = d.workout_type.__class__.RECOVERY
                d.duration_minutes = 20
                d.estimated_tss = 15.0
                d.target_zone = "Z1"
                d.notes = (d.notes or "") + " [mantenimento senza impatto]"
        return plan.model_copy(update={"total_tss": round(sum(d.estimated_tss for d in plan.days), 1)})


__all__ = ["AdaptationRules"]
