"""Granfondo training plan generator with tapering."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass
class PlannedWorkout:
    date: str
    title: str
    workout_type: str
    duration_minutes: int
    target_intensity: float
    description: str = ""


def generate_granfondo_plan(
    start_date: str, target_weeks: int = 8, ftp: float = 200.0
) -> list[dict]:
    """Generate an 8-12 week granfondo training plan with tapering.

    Tapering starts 2 weeks before event:
    - Week before: reduce volume by 40%
    - Final week: reduce volume by 60%
    """
    plan = []
    start = datetime.fromisoformat(start_date)

    workout_templates = [
        ("Base Aerobica", "endurance", 0.5),
        ("Progressivo", "sweetspot", 0.65),
        ("Base Aerobica", "endurance", 0.55),
        ("Thresholds", "threshold", 0.75),
        ("Recupero", "recovery", 0.4),
        ("Base Aerobica", "endurance", 0.55),
        ("Progressivo", "sweetspot", 0.7),
        ("Recupero", "recovery", 0.45),
        ("Base Aerobica", "endurance", 0.5),
        ("Thresholds", "threshold", 0.7),
        ("Pre-Gara", "openers", 0.6),
        ("Giorno Gara", "race", 0.9),
    ]

    def get_taper_multiplier(week_offset: int, total_weeks: int) -> float:
        weeks_to_event = total_weeks - week_offset
        if weeks_to_event <= 0:
            return 0.4
        if weeks_to_event == 1:
            return 0.6
        if weeks_to_event == 2:
            return 0.7
        return 1.0

    for w in range(target_weeks):
        taper_mult = get_taper_multiplier(w, target_weeks)
        for d in range(3):
            day_offset = w * 7 + d
            workout_date = (start + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            title, wtype, intensity = workout_templates[(w * 3 + d) % len(workout_templates)]
            duration = int(90 * taper_mult)
            plan.append(
                {
                    "date": workout_date,
                    "title": f"{title} (S{w + 1}W{d + 1})",
                    "workout_type": wtype,
                    "duration_minutes": duration,
                    "target_intensity": round(intensity * taper_mult, 2),
                    "description": f"Week {w + 1}, Day {d + 1}",
                }
            )

    event_date = (start + timedelta(days=target_weeks * 7)).strftime("%Y-%m-%d")
    plan.append(
        {
            "date": event_date,
            "title": "Granfondo",
            "workout_type": "race",
            "duration_minutes": int(180 * get_taper_multiplier(target_weeks, target_weeks)),
            "target_intensity": 0.9,
            "description": "Event day",
        }
    )

    return plan


def calculate_granfondo_workouts_from_goal(goal: dict) -> list[dict]:
    """Generate granfondo workouts based on training goal data."""
    start_date = goal.get("start_date") or datetime.now(UTC).strftime("%Y-%m-%d")
    weeks = goal.get("weeks", 8)
    ftp = goal.get("ftp", 200.0)

    plan = generate_granfondo_plan(start_date, weeks, ftp)

    for _i, workout in enumerate(plan):
        workout["goal_id"] = goal.get("id")

    return plan


__all__ = ["generate_granfondo_plan", "PlannedWorkout"]
