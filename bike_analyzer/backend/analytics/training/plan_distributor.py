"""Plan Distributor - distributes weekly load with periodization and tapering."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from .models import PlanConstraints, TrainingGoal, WeeklyPlan, Workout


class PlanDistributor:
    """Distributes training load across microcycles with periodization logic.

    Handles:
    - Hard/easy day balancing
    - Recovery weeks every 3-4 microcycles
    - Tapering toward target event
    - Volume vs intensity balance
    """

    def __init__(self, athlete: Any, ftp: float | None = None):
        self.athlete = athlete
        self.ftp = ftp or getattr(athlete, "ftp_watts", None) or 250.0

    def distribute(
        self,
        goal: TrainingGoal,
        constraints: PlanConstraints,
        start_date: datetime,
        generator: Any,
        current_tss: float = 0.0,
        fatigue_score: float = 0.0,
    ) -> WeeklyPlan:
        """Generate a full WeeklyPlan with periodization applied."""
        total_weeks = self._plan_weeks(goal)
        phase = self._determine_phase(total_weeks, goal)

        plan_start = start_date.strftime("%Y-%m-%d")
        plan_end = (start_date + timedelta(days=7 * total_weeks - 1)).strftime("%Y-%m-%d")

        all_workouts: list[Workout] = []
        for week_idx in range(total_weeks):
            week_start = start_date + timedelta(days=week_idx * 7)
            week_mult = self._week_multiplier(week_idx, total_weeks, goal)
            recovery_week = self._is_recovery_week(week_idx, total_weeks)

            week_constraints = PlanConstraints(
                days_per_week=constraints.days_per_week,
                hours_per_session=constraints.hours_per_session * week_mult,
                preferred_windows=constraints.preferred_windows,
                equipment=constraints.equipment,
                season=constraints.season,
                max_weekly_tss=constraints.max_weekly_tss * week_mult if constraints.max_weekly_tss else None,
                available_dates=constraints.available_dates,
            )
            if recovery_week:
                week_constraints.hours_per_session *= 0.6
                if week_constraints.max_weekly_tss:
                    week_constraints.max_weekly_tss *= 0.6

            weekly = generator.generate_for_week(
                goal=goal,
                constraints=week_constraints,
                start_date=week_start,
                fitness_tss=current_tss,
                fatigue_score=fatigue_score,
            )
            all_workouts.extend(weekly)

        total_tss = sum(w.estimated_tss for w in all_workouts)
        total_dist = sum(w.distance_target_km or 0 for w in all_workouts)
        total_dur = sum(w.duration_minutes for w in all_workouts)

        return WeeklyPlan(
            plan_name=f"Piano {goal.goal_type.value} - {total_weeks} settimane",
            start_date=plan_start,
            end_date=plan_end,
            days=all_workouts,
            total_tss=round(total_tss, 1),
            total_distance_km=round(total_dist, 1),
            total_duration_min=total_dur,
            microcycle_weeks=total_weeks,
            phase=phase,
            generated_at=datetime.now(UTC).isoformat(),
            parameters={
                "goal_type": goal.goal_type.value,
                "ftp": self.ftp,
                "days_per_week": constraints.days_per_week,
                "hours_per_session": constraints.hours_per_session,
            },
        )

    def _plan_weeks(self, goal: TrainingGoal) -> int:
        if goal.target_date:
            import datetime as dt
            target = dt.date.fromisoformat(goal.target_date)
            today = dt.date.today()
            delta = (target - today).days
            return max(1, min(52, delta // 7))
        if goal.goal_type.value == "ftp_improvement" and goal.ftp_timeframe_weeks:
            return max(1, min(26, goal.ftp_timeframe_weeks))
        return 8

    def _determine_phase(self, weeks: int, goal: TrainingGoal) -> str:
        if weeks <= 2:
            return "peak"
        if weeks <= 4:
            return "build"
        return "base"

    def _week_multiplier(self, week_idx: int, total_weeks: int, goal: TrainingGoal) -> float:
        weeks_to_event = total_weeks - week_idx
        if goal.goal_type.value in ("granfondo",) and weeks_to_event <= 2:
            taper = {1: 0.6, 2: 0.75}.get(weeks_to_event, 1.0)
            return taper
        return 1.0

    def _is_recovery_week(self, week_idx: int, total_weeks: int) -> bool:
        if total_weeks < 3:
            return False
        return (week_idx + 1) % 3 == 0


__all__ = ["PlanDistributor"]
