"""Constraint Solver - collects and validates real-world training constraints."""

from __future__ import annotations

from typing import Any

from .models import PlanConstraints


class ConstraintSolver:
    """Validates and enriches athlete constraints for plan generation."""

    def __init__(self, athlete: Any):
        self.athlete = athlete

    def solve(self, overrides: PlanConstraints | None = None) -> PlanConstraints:
        """Build constraints from athlete profile with optional overrides."""
        defaults = self._from_profile()
        if overrides:
            data = defaults.model_dump()
            data.update(overrides.model_dump(exclude_none=True))
            return PlanConstraints(**data)
        return defaults

    def validate(self, constraints: PlanConstraints) -> list[str]:
        """Return list of validation warnings (empty if valid)."""
        warnings = []
        if constraints.days_per_week < 1:
            warnings.append("days_per_week must be at least 1")
        if constraints.hours_per_session < 0.5:
            warnings.append("hours_per_session too low for effective training")
        if constraints.days_per_week > 7:
            warnings.append("days_per_week exceeds 7")
        if constraints.max_weekly_tss is not None and constraints.max_weekly_tss < 50:
            warnings.append("max_weekly_tss very low - risk of undertraining")
        return warnings

    def _from_profile(self) -> PlanConstraints:
        weekly_sessions = getattr(self.athlete, "weekly_sessions", None) or 3
        monthly_hours = getattr(self.athlete, "monthly_hours", None) or 0.0
        hours_per_session = (monthly_hours / 4.0 / weekly_sessions) if weekly_sessions > 0 else 1.5
        hours_per_session = max(0.5, min(8.0, hours_per_session))

        equipment_str = getattr(self.athlete, "equipment", None) or "road_bike"
        equipment = [e.strip().lower() for e in equipment_str.split(",") if e.strip()]
        if not equipment:
            equipment = ["road_bike"]

        return PlanConstraints(
            days_per_week=min(weekly_sessions, 7),
            hours_per_session=round(hours_per_session, 1),
            equipment=equipment,
        )


__all__ = ["ConstraintSolver"]
