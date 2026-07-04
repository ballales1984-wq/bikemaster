"""
Standalone trend analysis module for cycling data
==================================================
Implements fitness trend analysis using ride data.

Usage:
    from analytics_trends import calculate_fitness_trends, calculate_monthly_progression

    trends = calculate_fitness_trends(rides)  # rides: list of dicts
    progression = calculate_monthly_progression(rides)
"""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any


def _to_date(d) -> date:
    """Convert ride date field to date object."""
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        # Handle ISO format strings
        s = d.strip()
        try:
            return date.fromisoformat(s[:10])
        except (ValueError, IndexError):
            return None
    if isinstance(d, datetime):
        return d.date()
    return None


def _safe_float(val) -> float | None:
    """Safely convert value to float."""
    if val is None:
        return None
    try:
        f = float(val)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _filter_valid_rides(rides: list) -> list:
    """Filter rides with valid dates and numeric values."""
    result = []
    for r in rides:
        if not isinstance(r, dict):
            continue
        s = _safe_float(r.get("distance_km") or r.get("distance"))
        a = _safe_float(r.get("avg_speed_kmh") or r.get("avg_speed") or r.get("average_speed"))
        dur = _safe_float(r.get("duration_minutes") or r.get("duration"))
        d = _to_date(r.get("date") or r.get("start_date") or r.get("startTimeLocal"))
        has_date = d is not None
        has_numeric = s is not None and a is not None and dur is not None and s > 0 and a > 0 and dur > 0
        if has_date and has_numeric:
            result.append(r)
    return result


def _duration_hours(ride: dict) -> float:
    d = _safe_float(ride.get("duration_minutes") or ride.get("duration"))
    return d / 60.0 if d else 0.0


def _fit_linear(values: list[float]) -> dict:
    """Ordinary Least Squares linear regression on index→value pairs."""
    n = len(values)
    if n < 2:
        last = values[-1] if values else 0.0
        return {"slope": 0.0, "intercept": last, "r2": 0.0}

    x = list(range(n))
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n

    ss_xy = sum((xi - x_mean) * (values[i] - y_mean) for i, xi in enumerate(x))
    ss_xx = sum((xi - x_mean) ** 2 for xi in x)
    ss_yy = sum((v - y_mean) ** 2 for v in values)

    slope = ss_xy / ss_xx if ss_xx != 0 else 0.0
    intercept = y_mean - slope * x_mean

    if ss_yy > 0 and n > 1:
        r2 = (ss_xy**2) / (ss_xx * ss_yy)
        r2 = max(0.0, min(1.0, r2))
    else:
        r2 = 0.0

    return {"slope": round(slope, 6), "intercept": round(intercept, 6), "r2": round(r2, 4)}


def _rolling_average(values: list, window: int = 7) -> list:
    """Simple moving average."""
    if not values or window <= 0:
        return []
    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        segment = values[start : i + 1]
        result.append(sum(segment) / len(segment))
    return result


def calculate_fitness_trends(rides: list, metric: str = "distance_km", window: int = 7) -> dict[str, Any]:
    """
    Calculate fitness trends from ride data.

    Args:
        rides: list of ride dicts with at least 'date' and metric fields
        metric: which metric to analyze ('distance_km', 'avg_speed_kmh', etc.)
        window: rolling average window size (default 7 for weekly)

    Returns:
        {
            'ready': bool,
            'total_rides': int,
            'metric': str,
            'trend': str,  # 'improving', 'declining', 'stable'
            'slope': float,
            'r2': float,
            'first_value': float,
            'last_value': float,
            'mean': float,
            'std': float,
            'rolling_avg': list,
            'dates': list,
            'values': list,
        }
    """
    valid = _filter_valid_rides(rides)

    if not valid:
        return {
            "ready": False,
            "total_rides": 0,
            "metric": metric,
            "trend": "insufficient_data",
            "slope": 0.0,
            "r2": 0.0,
            "first_value": 0.0,
            "last_value": 0.0,
            "mean": 0.0,
            "std": 0.0,
            "rolling_avg": [],
            "dates": [],
            "values": [],
        }

    # Sort by date
    valid.sort(key=lambda r: _to_date(r.get("date")))

    values = []
    dates = []
    for r in valid:
        v = _safe_float(r.get(metric))
        if v is not None:
            values.append(v)
            dates.append(str(_to_date(r.get("date"))))

    if not values:
        return {
            "ready": False,
            "total_rides": len(valid),
            "metric": metric,
            "trend": "no_valid_data",
            "slope": 0.0,
            "r2": 0.0,
            "first_value": 0.0,
            "last_value": 0.0,
            "mean": 0.0,
            "std": 0.0,
            "rolling_avg": [],
            "dates": [],
            "values": [],
        }

    n = len(values)
    mean_val = sum(values) / n
    variance = sum((v - mean_val) ** 2 for v in values) / n
    std_val = math.sqrt(variance)

    regression = _fit_linear(values)

    slope = regression["slope"]
    if slope > 0.01:
        trend = "improving"
    elif slope < -0.01:
        trend = "declining"
    else:
        trend = "stable"

    rolling = _rolling_average(values, window)

    return {
        "ready": True,
        "total_rides": n,
        "metric": metric,
        "trend": trend,
        "slope": regression["slope"],
        "intercept": regression["intercept"],
        "r2": regression["r2"],
        "first_value": round(values[0], 4),
        "last_value": round(values[-1], 4),
        "mean": round(mean_val, 4),
        "std": round(std_val, 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "rolling_avg": [round(v, 4) for v in rolling],
        "dates": dates,
        "values": [round(v, 4) for v in values],
    }


def calculate_monthly_progression(rides: list) -> dict[str, Any]:
    """
    Calculate monthly aggregated metrics.

    Returns:
        {
            'ready': bool,
            'months': list of month keys,
            'total_distance_km': list,
            'avg_speed_kmh': list,
            'total_duration_hours': list,
            'ride_count': list,
            'avg_calories': list,
        }
    """
    valid = _filter_valid_rides(rides)
    if not valid:
        return {
            "ready": False,
            "months": [],
            "total_distance_km": [],
            "avg_speed_kmh": [],
            "total_duration_hours": [],
            "ride_count": [],
            "avg_calories": [],
        }

    # Group by month (YYYY-MM)
    months_data: dict[str, dict] = {}
    for r in valid:
        d = _to_date(r.get("date"))
        key = f"{d.year:04d}-{d.month:02d}"
        if key not in months_data:
            months_data[key] = {
                "distances": [],
                "speeds": [],
                "durations": [],
                "calories": [],
            }
        m = months_data[key]
        m["distances"].append(_safe_float(r.get("distance_km") or r.get("distance")))
        m["speeds"].append(_safe_float(r.get("avg_speed_kmh") or r.get("avg_speed")))
        m["durations"].append(_duration_hours(r))
        cal = _safe_float(r.get("calories"))
        if cal is not None:
            m["calories"].append(cal)

    sorted_months = sorted(months_data.keys())

    result = {
        "ready": True,
        "months": sorted_months,
        "total_distance_km": [],
        "avg_speed_kmh": [],
        "total_duration_hours": [],
        "ride_count": [],
        "avg_calories": [],
    }

    for key in sorted_months:
        m = months_data[key]
        cleaned_dist = [v for v in m["distances"] if v is not None]
        cleaned_speed = [v for v in m["speeds"] if v is not None]
        cal_values = m["calories"]

        result["total_distance_km"].append(round(sum(cleaned_dist), 2) if cleaned_dist else 0.0)
        result["avg_speed_kmh"].append(round(sum(cleaned_speed) / len(cleaned_speed), 2) if cleaned_speed else 0.0)
        result["total_duration_hours"].append(round(sum(m["durations"]), 2))
        result["ride_count"].append(len(cleaned_dist) if cleaned_dist else 0)
        result["avg_calories"].append(round(sum(cal_values) / len(cal_values), 1) if cal_values else 0.0)

    return result


def calculate_period_comparison(rides: list, period_days: int = 7) -> dict[str, Any]:
    """
    Compare recent period vs previous period.

    Args:
        rides: list of ride dicts
        period_days: number of days per period (default 7 for weekly)

    Returns:
        {
            'ready': bool,
            'recent_rides': int,
            'previous_rides': int,
            'recent_distance_km': float,
            'previous_distance_km': float,
            'recent_avg_speed': float,
            'previous_avg_speed': float,
            'distance_change_pct': float,
            'speed_change_pct': float,
        }
    """
    valid = _filter_valid_rides(rides)
    if not valid or period_days <= 0:
        return {
            "ready": False,
            "recent_rides": 0,
            "previous_rides": 0,
            "recent_distance_km": 0.0,
            "previous_distance_km": 0.0,
            "recent_avg_speed": 0.0,
            "previous_avg_speed": 0.0,
            "distance_change_pct": 0.0,
            "speed_change_pct": 0.0,
        }

    # Get most recent date
    dates = [_to_date(r.get("date")) for r in valid]
    max_date = max(d for d in dates if d is not None)

    # Use actual max_date from dates
    cutoff_recent = max_date

    recent = []
    previous = []

    for r in valid:
        d = _to_date(r.get("date"))
        if d is None:
            continue
        days_ago = (cutoff_recent - d).days
        if days_ago < period_days:
            recent.append(r)
        elif days_ago < period_days * 2:
            previous.append(r)

    def _avg(values: list) -> float:
        cleaned = [v for v in values if v is not None]
        return sum(cleaned) / len(cleaned) if cleaned else 0.0

    def _sum(values: list) -> float:
        cleaned = [v for v in values if v is not None]
        return sum(cleaned) if cleaned else 0.0

    recent_dist = []
    recent_speed = []
    for r in recent:
        recent_dist.append(_safe_float(r.get("distance_km") or r.get("distance")))
        recent_speed.append(_safe_float(r.get("avg_speed_kmh") or r.get("avg_speed")))

    prev_dist = []
    prev_speed = []
    for r in previous:
        prev_dist.append(_safe_float(r.get("distance_km") or r.get("distance")))
        prev_speed.append(_safe_float(r.get("avg_speed_kmh") or r.get("avg_speed")))

    rd = _sum(recent_dist)
    rs = _avg(recent_speed)
    pd = _sum(prev_dist)
    ps = _avg(prev_speed)

    dist_change = ((rd - pd) / pd * 100) if pd > 0 else 0.0
    speed_change = ((rs - ps) / ps * 100) if ps > 0 else 0.0

    return {
        "ready": True,
        "recent_rides": len(recent),
        "previous_rides": len(previous),
        "recent_distance_km": round(rd, 2),
        "previous_distance_km": round(pd, 2),
        "recent_avg_speed": round(rs, 2),
        "previous_avg_speed": round(ps, 2),
        "distance_change_pct": round(dist_change, 1),
        "speed_change_pct": round(speed_change, 1),
    }


def calculate_training_volume_projection(rides: list, target_days: int = 30) -> dict[str, Any]:
    """
    Project future training volume based on trend.

    Args:
        rides: list of ride dicts
        target_days: days to project forward

    Returns:
        {
            'ready': bool,
            'projected_distance_km': float,
            'projected_duration_hours': float,
            'projected_rides': int,
            'confidence': str,  # 'high', 'medium', 'low'
            'avg_daily_distance_km': float,
            'avg_ride_duration_min': float,
        }
    """
    valid = _filter_valid_rides(rides)
    if not valid:
        return {
            "ready": False,
            "projected_distance_km": 0.0,
            "projected_duration_hours": 0.0,
            "projected_rides": 0,
            "confidence": "none",
            "avg_daily_distance_km": 0.0,
            "avg_ride_duration_min": 0.0,
        }

    dates = sorted({_to_date(r.get("date")) for r in valid if _to_date(r.get("date"))})
    min_date = dates[0]
    max_date = dates[-1]
    days_span = (max_date - min_date).days + 1

    total_dist = sum(_safe_float(r.get("distance_km") or r.get("distance") or 0) for r in valid)
    total_dur = sum(_duration_hours(r) for r in valid)

    avg_daily_dist = total_dist / days_span if days_span > 0 else 0
    avg_daily_dur = total_dur / days_span if days_span > 0 else 0
    avg_ride_dur = (total_dur * 60) / len(valid) if valid else 0

    proj_dist = avg_daily_dist * target_days
    proj_dur = avg_daily_dur * target_days
    proj_rides = len(valid) / days_span * target_days if days_span > 0 else 0

    n = len(valid)
    if n >= 10 and days_span >= 14:
        confidence = "high"
    elif n >= 5 and days_span >= 7:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "ready": True,
        "projected_distance_km": round(proj_dist, 1),
        "projected_duration_hours": round(proj_dur, 1),
        "projected_rides": round(proj_rides, 0),
        "confidence": confidence,
        "avg_daily_distance_km": round(avg_daily_dist, 2),
        "avg_ride_duration_min": round(avg_ride_dur, 1),
        "data_span_days": days_span,
        "total_rides": n,
    }


def get_ride_metrics(ride: dict) -> dict[str, Any]:
    """
    Extract all numeric metrics from a single ride dict.
    Returns a flat dict of {metric_name: value}.
    """
    metrics = {}
    numeric_fields = [
        "distance_km",
        "duration_minutes",
        "avg_speed_kmh",
        "weight_kg",
        "calories",
        "heart_rate_avg",
        "elevation_gain_m",
        "power_avg_w",
        "power_per_kg_w",
    ]
    for field in numeric_fields:
        v = _safe_float(ride.get(field))
        if v is not None:
            metrics[field] = v
    return metrics


# Public API
__all__ = [
    "calculate_fitness_trends",
    "calculate_monthly_progression",
    "calculate_period_comparison",
    "calculate_training_volume_projection",
    "get_ride_metrics",
    "_safe_float",
    "_to_date",
    "_filter_valid_rides",
]
