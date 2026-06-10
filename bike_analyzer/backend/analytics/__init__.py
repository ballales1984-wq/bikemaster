"""Analytics module."""

from .analytics import (
    analyze_ride,
    calculate_summary,
    export_rides_csv,
    export_rides_json,
    generate_text_report,
)
from .badges import calculate_badges, get_heatmap_points
from .calories import (
    calculate_calories_met,
    calculate_calories_physics,
    estimate_calories,
)
from .fatigue import (
    calculate_fatigue_score,
    estimate_recovery_hours,
    get_recovery_recommendation,
)
from .granfondo_planner import generate_granfondo_plan
from .performance import (
    calculate_efficiency_score,
    calculate_endurance_score,
    calculate_performance_score,
    get_experience_level,
)

__all__ = [
    "calculate_summary",
    "analyze_ride",
    "estimate_calories",
    "calculate_calories_met",
    "calculate_calories_physics",
    "calculate_fatigue_score",
    "estimate_recovery_hours",
    "get_recovery_recommendation",
    "calculate_performance_score",
    "calculate_endurance_score",
    "calculate_efficiency_score",
    "get_experience_level",
    "export_rides_json",
    "export_rides_csv",
    "generate_text_report",
    "calculate_badges",
    "get_heatmap_points",
    "generate_granfondo_plan",
]
