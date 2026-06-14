"""Analytics package."""

from typing import Any

_ANALYTICS_ATTRS = {
    "analyze_ride": ("analytics", "analyze_ride"),
    "calculate_summary": ("analytics", "calculate_summary"),
    "export_rides_csv": ("analytics", "export_rides_csv"),
    "export_rides_json": ("analytics", "export_rides_json"),
    "generate_text_report": ("analytics", "generate_text_report"),
    "calculate_badges": ("badges", "calculate_badges"),
    "get_heatmap_points": ("badges", "get_heatmap_points"),
    "calculate_calories_met": ("calories", "calculate_calories_met"),
    "calculate_calories_physics": ("calories", "calculate_calories_physics"),
    "estimate_calories": ("calories", "estimate_calories"),
    "calculate_fatigue_score": ("fatigue", "calculate_fatigue_score"),
    "estimate_recovery_hours": ("fatigue", "estimate_recovery_hours"),
    "get_recovery_recommendation": ("fatigue", "get_recovery_recommendation"),
    "generate_granfondo_plan": ("granfondo_planner", "generate_granfondo_plan"),
    "calculate_efficiency_score": ("performance", "calculate_efficiency_score"),
    "calculate_endurance_score": ("performance", "calculate_endurance_score"),
    "calculate_performance_score": ("performance", "calculate_performance_score"),
    "get_experience_level": ("performance", "get_experience_level"),
}


def __getattr__(name: str) -> Any:
    if name not in _ANALYTICS_ATTRS:
        raise AttributeError(name)
    module_name, attr_name = _ANALYTICS_ATTRS[name]
    module = __import__(f"bike_analyzer.backend.analytics.{module_name}", fromlist=[attr_name])
    return getattr(module, attr_name)


__all__ = sorted(_ANALYTICS_ATTRS)
