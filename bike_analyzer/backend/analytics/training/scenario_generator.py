"""Scenario Generator - creates multiple versions of a training plan."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .adaptation_engine import AdaptationEngine
from .models import (
    AdaptationEvent,
    AdaptationEventType,
    PlanConstraints,
    Scenario,
    ScenarioType,
    TrainingGoal,
    WeeklyPlan,
    WorkoutType,
)
from .plan_distributor import PlanDistributor
from .workout_generator import WorkoutGenerator


class ScenarioGenerator:
    """Creates alternative plan scenarios from the same starting state.

    Scenarios:
    - A: recover volume (redistribute missed load)
    - B: maintain plan (keep as-is, possibly with minor tweaks)
    - C: change type (swap to different workout type)
    """

    def __init__(self, athlete: Any, ftp: float | None = None):
        self.athlete = athlete
        self.ftp = ftp or getattr(athlete, "ftp_watts", None) or 250.0
        self.generator = WorkoutGenerator(athlete, self.ftp)
        self.distributor = PlanDistributor(athlete, self.ftp)
        self.engine = AdaptationEngine(athlete, self.ftp)

    def generate_scenarios(
        self,
        goal: TrainingGoal,
        constraints: PlanConstraints,
        base_plan: WeeklyPlan,
        event: dict | None = None,
    ) -> list[Scenario]:
        """Generate A/B/C scenarios from base plan and optional event."""
        scenarios: list[Scenario] = []

        scenario_a = self._scenario_recover_volume(goal, constraints, base_plan, event)
        scenarios.append(scenario_a)

        scenario_b = self._scenario_maintain(goal, constraints, base_plan, event)
        scenarios.append(scenario_b)

        scenario_c = self._scenario_change_type(goal, constraints, base_plan, event)
        scenarios.append(scenario_c)

        for s in scenarios:
            s.score = self._score_scenario(s.plan)

        scenarios.sort(key=lambda s: s.score, reverse=True)
        return scenarios

    def _scenario_recover_volume(
        self, goal: TrainingGoal, constraints: PlanConstraints, base: WeeklyPlan, event: Any
    ) -> Scenario:
        plan = self.distributor.distribute(
            goal=goal,
            constraints=constraints,
            start_date=datetime.strptime(base.start_date, "%Y-%m-%d"),
            generator=self.generator,
        )
        return Scenario(
            scenario_type=ScenarioType.RECOVER_VOLUME,
            label="Scenario A: Recupera volume",
            description="Ridistribuisce il carico perso sui prossimi allenamenti mantenendo il tipo.",
            plan=plan,
            rationale="Il carico mancato viene redistribuito gradualmente per evitare picchi.",
        )

    def _scenario_maintain(
        self, goal: TrainingGoal, constraints: PlanConstraints, base: WeeklyPlan, event: Any
    ) -> Scenario:
        plan = base.model_copy(deep=True)
        if event:
            ev = AdaptationEvent(
                event_type=AdaptationEventType.SKIPPED,
                occurred_date=event.get("date", base.start_date),
                actual_data=event.get("actual_data", {}),
            )
            plan = self.engine.adapt(plan=plan, event=ev, constraints=constraints, goal=goal)
        return Scenario(
            scenario_type=ScenarioType.MAINTAIN_PLAN,
            label="Scenario B: Mantieni piano",
            description="Mantiene il piano originale con adattamenti minimi.",
            plan=plan,
            rationale="Preserva la struttura originale con aggiustamenti minori.",
        )

    def _scenario_change_type(
        self, goal: TrainingGoal, constraints: PlanConstraints, base: WeeklyPlan, event: Any
    ) -> Scenario:
        new_constraints = PlanConstraints(
            days_per_week=constraints.days_per_week,
            hours_per_session=constraints.hours_per_session,
            preferred_windows=constraints.preferred_windows,
            equipment=constraints.equipment,
            season=constraints.season,
            max_weekly_tss=constraints.max_weekly_tss,
        )
        modified_goal = goal.model_copy(deep=True)

        plan = self.distributor.distribute(
            goal=modified_goal,
            constraints=new_constraints,
            start_date=datetime.strptime(base.start_date, "%Y-%m-%d"),
            generator=self.generator,
        )
        for w in plan.days:
            if w.workout_type == WorkoutType.INTERVALS:
                w.workout_type = WorkoutType.SWEETSPOT
                w.title = "Sweet spot (sostituito)"
                w.estimated_tss = round(w.estimated_tss * 0.8, 1)
                w.notes = (w.notes or "") + " [cambiato da intervals]"
        return Scenario(
            scenario_type=ScenarioType.CHANGE_TYPE,
            label="Scenario C: Cambia tipo",
            description="Sostituisce gli allenamenti intensi con uscite piu dolci per recuperare.",
            plan=plan,
            rationale="Prioritizza il recupero modificando il tipo di allenamento.",
        )

    def _score_scenario(self, plan: WeeklyPlan) -> float:
        if not plan.days:
            return 0.0
        balance = 1.0 - abs(plan.total_tss / max(len(plan.days), 1) - 80.0) / 100.0
        balance = max(0.0, min(1.0, balance))
        recovery_ratio = sum(1 for d in plan.days if d.workout_type.value == "recovery") / max(len(plan.days), 1)
        recovery_score = min(recovery_ratio * 4, 1.0)
        return round(balance * 0.6 + recovery_score * 0.4, 2)


__all__ = ["ScenarioGenerator"]
