"""Goal Analyzer - interprets athlete goals into structured training objectives."""

from __future__ import annotations

from typing import Any

from .models import GoalType, TrainingGoal


class GoalAnalyzer:
    """Transforms raw athlete goals into structured TrainingGoal objects.

    Supports structured input (TrainingGoal) and free-text parsing from
    athlete profile goals field.
    """

    def __init__(self, athlete: Any):
        self.athlete = athlete

    def analyze(self, goal: TrainingGoal | str | None = None) -> TrainingGoal:
        """Return a structured TrainingGoal.

        Priority:
        1. Explicit TrainingGoal if provided
        2. Parse free-text from athlete.goals
        3. Fallback to maintenance based on profile
        """
        if isinstance(goal, TrainingGoal):
            return self._apply_profile_defaults(goal)

        if isinstance(goal, str) and goal.strip():
            parsed = self._parse_free_text(goal.strip())
            return self._apply_profile_defaults(parsed)

        return self._fallback_from_profile()

    def target_weekly_tss(self, goal: TrainingGoal) -> float:
        """Estimate target weekly TSS based on goal type and athlete level."""
        level = (getattr(self.athlete, "experience_level", "Beginner") or "Beginner").lower()
        base = {
            "beginner": 150.0,
            "amateur": 250.0,
            "intermediate": 350.0,
            "advanced": 500.0,
            "elite": 700.0,
        }.get(level, 250.0)

        multipliers = {
            GoalType.GRANFONDO: 1.3,
            GoalType.FTP_IMPROVEMENT: 1.4,
            GoalType.WEIGHT_LOSS: 0.9,
            GoalType.MAINTENANCE: 1.0,
            GoalType.BEGINNER_BASE: 0.8,
        }
        return round(base * multipliers.get(goal.goal_type, 1.0), 1)

    def plan_duration_weeks(self, goal: TrainingGoal) -> int:
        """Calculate plan duration in weeks from goal and target date."""
        if goal.target_date:
            import datetime
            target = datetime.date.fromisoformat(goal.target_date)
            today = datetime.date.today()
            delta = (target - today).days
            return max(1, min(52, delta // 7))

        if goal.goal_type == GoalType.FTP_IMPROVEMENT and goal.ftp_timeframe_weeks:
            return max(1, min(26, goal.ftp_timeframe_weeks))

        return 8

    def taper_weeks(self, goal: TrainingGoal) -> int:
        """Return number of taper weeks before target event."""
        from .models import WorkoutType

        total = self.plan_duration_weeks(goal)
        if goal.goal_type == GoalType.GRANFONDO or getattr(goal, "event_type", None) == WorkoutType.RACE:
            return max(1, min(3, total // 6))
        return 1

    def _apply_profile_defaults(self, goal: TrainingGoal) -> TrainingGoal:
        if not goal.target_date and getattr(self.athlete, "goals", None):
            pass
        return goal

    def _parse_free_text(self, text: str) -> TrainingGoal:
        lowered = text.lower()
        if any(k in lowered for k in ("granfondo", "gran fondo", "gf", "evento", "gara")):
            return TrainingGoal(goal_type=GoalType.GRANFONDO, description=text)
        if any(k in lowered for k in ("ftp", "soglia", "threshold", "potenza")):
            return TrainingGoal(goal_type=GoalType.FTP_IMPROVEMENT, description=text)
        if any(k in lowered for k in ("peso", "dimagr", "weight", "grasso", "fat")):
            return TrainingGoal(goal_type=GoalType.WEIGHT_LOSS, description=text)
        if any(k in lowered for k in ("principiante", "beginner", "base", "iniziare")):
            return TrainingGoal(goal_type=GoalType.BEGINNER_BASE, description=text)
        return TrainingGoal(goal_type=GoalType.MAINTENANCE, description=text)

    def _fallback_from_profile(self) -> TrainingGoal:
        level = (getattr(self.athlete, "experience_level", "Beginner") or "Beginner").lower()
        if level in ("beginner",):
            return TrainingGoal(goal_type=GoalType.BEGINNER_BASE)
        return TrainingGoal(goal_type=GoalType.MAINTENANCE)


__all__ = ["GoalAnalyzer"]
