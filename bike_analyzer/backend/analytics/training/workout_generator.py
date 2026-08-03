"""Workout Generator - produces concrete workout instances from goals and constraints."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .models import GoalType, PlanConstraints, TrainingGoal, Workout, WorkoutBlock, WorkoutType


class WorkoutGenerator:
    """Generates concrete Workout objects for a given goal, constraints, and fitness state."""

    def __init__(self, athlete: Any, ftp: float | None = None):
        self.athlete = athlete
        self.ftp = ftp or getattr(athlete, "ftp_watts", None) or 250.0

    def generate_for_week(
        self,
        goal: TrainingGoal,
        constraints: PlanConstraints,
        start_date: datetime,
        fitness_tss: float = 0.0,
        fatigue_score: float = 0.0,
    ) -> list[Workout]:
        """Generate a list of Workout objects for one microcycle."""
        days = constraints.days_per_week
        target_weekly_tss = self._target_weekly_tss(goal, constraints)
        tss_per_ride = target_weekly_tss / max(days, 1)
        duration_per_ride = constraints.hours_per_session * 60

        workouts: list[Workout] = []
        session_types = self._select_week_template(goal, days)

        for i in range(days):
            day = start_date + timedelta(days=i)
            wtype = session_types[i % len(session_types)]
            fatigue_factor = self._fatigue_adjustment(fatigue_score, i, days)
            adjusted_duration = int(duration_per_ride * fatigue_factor)
            workout = self._build_workout(
                date=day.strftime("%Y-%m-%d"),
                workout_type=wtype,
                duration_minutes=adjusted_duration,
                tss_target=tss_per_ride * fatigue_factor,
                goal=goal,
                constraints=constraints,
            )
            workouts.append(workout)

        return workouts

    def _target_weekly_tss(self, goal: TrainingGoal, constraints: PlanConstraints) -> float:
        level = (getattr(self.athlete, "experience_level", "Beginner") or "Beginner").lower()
        base = {
            "beginner": 150.0,
            "amateur": 250.0,
            "intermediate": 350.0,
            "advanced": 500.0,
            "elite": 700.0,
        }.get(level, 250.0)
        mult = {
            GoalType.GRANFONDO: 1.3,
            GoalType.FTP_IMPROVEMENT: 1.4,
            GoalType.WEIGHT_LOSS: 0.9,
            GoalType.MAINTENANCE: 1.0,
            GoalType.BEGINNER_BASE: 0.8,
        }.get(goal.goal_type, 1.0)
        user_max = constraints.max_weekly_tss
        calculated = base * mult
        if user_max is not None and user_max > 0:
            calculated = min(calculated, user_max)
        return round(calculated, 1)

    def _select_week_template(self, goal: TrainingGoal, days: int) -> list[WorkoutType]:
        if goal.goal_type == GoalType.GRANFONDO:
            return [
                WorkoutType.ENDURANCE,
                WorkoutType.SWEETSPOT,
                WorkoutType.RECOVERY,
                WorkoutType.THRESHOLD,
                WorkoutType.LONG_RIDE,
            ][: max(days, 1)]
        if goal.goal_type == GoalType.FTP_IMPROVEMENT:
            return [
                WorkoutType.THRESHOLD,
                WorkoutType.INTERVALS,
                WorkoutType.SWEETSPOT,
                WorkoutType.ENDURANCE,
                WorkoutType.RECOVERY,
            ][: max(days, 1)]
        if goal.goal_type == GoalType.WEIGHT_LOSS:
            return [WorkoutType.ENDURANCE, WorkoutType.SWEETSPOT, WorkoutType.ENDURANCE, WorkoutType.RECOVERY][
                : max(days, 1)
            ]
        if goal.goal_type == GoalType.BEGINNER_BASE:
            return [WorkoutType.ENDURANCE, WorkoutType.RECOVERY, WorkoutType.ENDURANCE][: max(days, 1)]
        return [WorkoutType.ENDURANCE, WorkoutType.THRESHOLD, WorkoutType.RECOVERY, WorkoutType.LONG_RIDE][
            : max(days, 1)
        ]

    def _fatigue_adjustment(self, fatigue: float, position: int, total_days: int) -> float:
        if fatigue >= 8:
            return 0.6
        if fatigue >= 5:
            return 0.8
        if position == total_days - 1:
            return 1.1
        if position == 0:
            return 0.9
        return 1.0

    def _build_workout(
        self,
        date: str,
        workout_type: WorkoutType,
        duration_minutes: int,
        tss_target: float,
        goal: TrainingGoal,
        constraints: PlanConstraints,
    ) -> Workout:
        intensity = self._intensity_for_type(workout_type)
        zone = self._zone_for_intensity(intensity)
        blocks = self._build_blocks(workout_type, duration_minutes, intensity)
        distance = self._estimate_distance(workout_type, duration_minutes, intensity)

        title_map = {
            WorkoutType.ENDURANCE: "Fondo aerobico",
            WorkoutType.THRESHOLD: "Soglia controllata",
            WorkoutType.SWEETSPOT: "Sweet spot",
            WorkoutType.INTERVALS: "Interval training",
            WorkoutType.RECOVERY: "Recupero attivo",
            WorkoutType.LONG_RIDE: "Uscita lunga",
            WorkoutType.RACE: "Gara / simulazione",
            WorkoutType.OPENERS: "Apertura pre-gara",
        }
        notes = ""
        if goal.goal_type == GoalType.GRANFONDO and workout_type == WorkoutType.LONG_RIDE:
            notes = "Costruisci resistenza per la granfondo"
        elif goal.goal_type == GoalType.FTP_IMPROVEMENT and workout_type == WorkoutType.THRESHOLD:
            notes = "Lavora alla soglia per aumentare FTP"

        return Workout(
            date=date,
            title=title_map.get(workout_type, "Allenamento"),
            workout_type=workout_type,
            duration_minutes=duration_minutes,
            distance_target_km=distance,
            elevation_gain_m=int(distance * 4.0)
            if workout_type in (WorkoutType.THRESHOLD, WorkoutType.LONG_RIDE)
            else 0,
            intensity_pct_ftp=intensity,
            target_zone=zone,
            blocks=blocks,
            notes=notes,
            estimated_tss=round(tss_target, 1),
        )

    def _intensity_for_type(self, wtype: WorkoutType) -> float:
        return {
            WorkoutType.RECOVERY: 0.55,
            WorkoutType.ENDURANCE: 0.68,
            WorkoutType.SWEETSPOT: 0.84,
            WorkoutType.THRESHOLD: 0.90,
            WorkoutType.INTERVALS: 0.98,
            WorkoutType.LONG_RIDE: 0.72,
            WorkoutType.RACE: 0.95,
            WorkoutType.OPENERS: 0.80,
        }.get(wtype, 0.70)

    def _zone_for_intensity(self, intensity: float) -> str:
        if intensity < 0.60:
            return "Z1-Z2"
        if intensity < 0.75:
            return "Z2"
        if intensity < 0.87:
            return "Z3"
        if intensity < 0.93:
            return "Z4"
        return "Z5"

    def _build_blocks(self, wtype: WorkoutType, duration: int, intensity: float) -> list[WorkoutBlock]:
        warmup = WorkoutBlock(
            block_type="warmup",
            duration_minutes=10,
            intensity_pct_ftp=0.55,
            target_zone="Z1-Z2",
            description="Riscaldamento progressivo",
        )
        cooldown = WorkoutBlock(
            block_type="cooldown",
            duration_minutes=10,
            intensity_pct_ftp=0.50,
            target_zone="Z1-Z2",
            description="Defaticamento",
        )

        if wtype == WorkoutType.RECOVERY:
            return [
                warmup,
                WorkoutBlock(
                    block_type="main",
                    duration_minutes=max(5, duration - 20),
                    intensity_pct_ftp=0.55,
                    target_zone="Z1-Z2",
                    description="Pedalata molto leggera",
                ),
                cooldown,
            ]

        if wtype == WorkoutType.ENDURANCE:
            main_dur = max(10, duration - 20)
            return [
                warmup,
                WorkoutBlock(
                    block_type="main",
                    duration_minutes=main_dur,
                    intensity_pct_ftp=intensity,
                    target_zone=self._zone_for_intensity(intensity),
                    description="Fondo costante",
                ),
                cooldown,
            ]

        if wtype == WorkoutType.LONG_RIDE:
            main_dur = max(20, duration - 20)
            return [
                warmup,
                WorkoutBlock(
                    block_type="main",
                    duration_minutes=main_dur,
                    intensity_pct_ftp=intensity,
                    target_zone=self._zone_for_intensity(intensity),
                    description="Uscita lunga sostenuta",
                ),
                cooldown,
            ]

        if wtype == WorkoutType.THRESHOLD:
            main_dur = max(15, duration - 20)
            return [
                warmup,
                WorkoutBlock(
                    block_type="main",
                    duration_minutes=main_dur,
                    intensity_pct_ftp=intensity,
                    target_zone="Z4",
                    description="Soglia controllata",
                ),
                cooldown,
            ]

        if wtype == WorkoutType.SWEETSPOT:
            main_dur = max(10, duration - 20)
            return [
                warmup,
                WorkoutBlock(
                    block_type="main",
                    duration_minutes=main_dur,
                    intensity_pct_ftp=intensity,
                    target_zone="Z3",
                    description="Sweet spot sostenuto",
                ),
                cooldown,
            ]

        if wtype == WorkoutType.INTERVALS:
            main_dur = max(10, duration - 20)
            reps = max(1, main_dur // 5)
            rep_dur = main_dur // reps
            return [
                warmup,
                WorkoutBlock(
                    block_type="main",
                    duration_minutes=main_dur,
                    intensity_pct_ftp=intensity,
                    target_zone="Z5",
                    description=f"{reps} ripetizioni ad alta intensita",
                    repetition_count=reps,
                    repetition_duration_min=rep_dur,
                    repetition_rest_min=2,
                ),
                cooldown,
            ]

        main_dur = max(10, duration - 20)
        return [
            warmup,
            WorkoutBlock(
                block_type="main",
                duration_minutes=main_dur,
                intensity_pct_ftp=intensity,
                target_zone=self._zone_for_intensity(intensity),
                description="Parte principale",
            ),
            cooldown,
        ]

    def _estimate_distance(self, wtype: WorkoutType, duration_min: int, intensity: float) -> float | None:
        speed_map = {
            WorkoutType.RECOVERY: 18.0,
            WorkoutType.ENDURANCE: 24.0,
            WorkoutType.SWEETSPOT: 28.0,
            WorkoutType.THRESHOLD: 30.0,
            WorkoutType.INTERVALS: 32.0,
            WorkoutType.LONG_RIDE: 22.0,
            WorkoutType.RACE: 33.0,
            WorkoutType.OPENERS: 26.0,
        }
        speed = speed_map.get(wtype, 24.0) * (0.7 + intensity * 0.4)
        return round(speed * duration_min / 60.0, 1)


__all__ = ["WorkoutGenerator"]
