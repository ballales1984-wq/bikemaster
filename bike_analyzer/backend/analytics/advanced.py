"""Advanced mathematical models and algorithms for cycling performance analysis.

Implements:
1. Pace Consistency Model - Coefficient of variation and pacing strategy analysis
2. Power Estimation Model - Physics-based power meter estimation
3. Climb Category Classifier - Tour de France style climb categorization
4. VO2max Estimation - Aerobic capacity from ride data
5. Route Difficulty Score - Multi-factor route classification
6. Elevation Profile Analysis - Grade distribution and hardship index
7. Speed Profile Analysis - Acceleration patterns and speed variability
8. Progress Trend Analysis - Linear regression improvement metrics
9. Training Stress Balance - ATL/CTL/TSB model with EWMA
10. Ideal Weight Estimation - Power-to-weight optimization
11. Heart Rate Zones - Five-zone training model
12. Garmin Power Factor - NP/IF/TSS estimation
13. Ride Recommendation Score - Training load classification
14. Speed Surge Detection - Acceleration event detection
"""

from __future__ import annotations

import math
from typing import Any

from ..models.models import GPSPoint, Ride, Segment, haversine_distance_m

try:
    import importlib.util as _ilu

    _available = all(
        _ilu.find_spec(m) is not None
        for m in (
            "endurance_metrics.advanced",
            "endurance_metrics.decoupling",
            "endurance_metrics.fitness",
            "endurance_metrics.workload",
        )
    )
    if _available:
        from endurance_metrics.advanced import (  # noqa: F401
            detect_overtraining_risk,
            detect_training_peaks,
        )
        from endurance_metrics.decoupling import calculate_decoupling  # noqa: F401
        from endurance_metrics.fitness import calculate_tsb  # noqa: F401
        from endurance_metrics.workload import calculate_ramp_rate  # noqa: F401
        ENDURANCE_METRICS_AVAILABLE = True
    else:
        ENDURANCE_METRICS_AVAILABLE = False
except ImportError:
    ENDURANCE_METRICS_AVAILABLE = False

POWER_CONSTANTS = {
    "g": 9.81,
    "crr_road": 0.004,
    "crr_gravel": 0.006,
    "crr_offroad": 0.012,
    "air_density": 1.225,
    "cd_a_road": 0.32,
    "cd_a_aero": 0.24,
    "cd_a_time_trial": 0.18,
    "neuromuscular_efficiency": 0.25,
}

CLIMB_CATEGORIES = [
    ("HC", 15.0),
    ("1", 12.0),
    ("2", 9.0),
    ("3", 6.0),
    ("4", 3.0),
]

_CLIMB_COLORS = {"4": "#4CAF50", "3": "#FFC107", "2": "#FF9800", "1": "#F44336", "HC": "#D32F2F"}
_CLIMB_POINTS = {"4": 1, "3": 2, "2": 3, "1": 4, "HC": 5}


def _get_climb_color(cat: str) -> str:
    return _CLIMB_COLORS.get(cat, "#999")


def calculate_pace_consistency(segments: list[Segment]) -> dict[str, float]:
    speeds = [s.avg_speed_km_h for s in segments if s.avg_speed_km_h > 0]
    if not speeds or len(speeds) < 2:
        return {
            "cv_percent": 0.0,
            "min_speed": 0.0,
            "max_speed": 0.0,
            "pace_strategy": "unknown",
            "negative_split": False,
        }
    mean_spd = sum(speeds) / len(speeds)
    variance = sum((s - mean_spd) ** 2 for s in speeds) / len(speeds)
    std_dev = math.sqrt(variance)
    cv = std_dev / mean_spd * 100 if mean_spd > 0 else 0.0
    if cv < 10:
        strategy = "steady"
    elif cv < 25:
        strategy = "variable"
    else:
        strategy = "erratic"
    mid = len(speeds) // 2
    first_half = sum(speeds[:mid]) / mid if mid > 0 else 0
    second_half = sum(speeds[mid:]) / (len(speeds) - mid) if (len(speeds) - mid) > 0 else 0
    negative_split = second_half > first_half * 1.02
    return {
        "cv_percent": round(cv, 1),
        "min_speed": round(min(speeds), 1),
        "max_speed": round(max(speeds), 1),
        "pace_strategy": strategy,
        "negative_split": negative_split,
        "first_half_avg": round(first_half, 1),
        "second_half_avg": round(second_half, 1),
        "pace_diff_percent": round((second_half - first_half) / first_half * 100, 1)
        if first_half > 0
        else 0,
    }


def calculate_power_estimate(
    ride: Ride,
    rider_weight_kg: float | None = None,
    bike_weight_kg: float = 8.0,
    cda: float = POWER_CONSTANTS["cd_a_road"],
    crr: float = POWER_CONSTANTS["crr_road"],
) -> dict[str, float]:
    weight = rider_weight_kg or ride.weight_kg
    total_kg = weight + bike_weight_kg
    v_ms = ride.avg_speed_kmh * 1000 / 3600
    if v_ms <= 0 or ride.duration_minutes <= 0:
        return {
            "power_avg_w": 0.0,
            "power_per_kg_w": 0.0,
            "w_prime_j": 0.0,
            "cd_wind": 0.0,
            "cd_rolling": 0.0,
            "cd_gravity": 0.0,
        }
    w_n = total_kg * POWER_CONSTANTS["g"]
    grade = (
        (ride.elevation_gain_m / (ride.distance_km * 1000))
        if ride.elevation_gain_m and ride.distance_km and ride.distance_km > 0
        else 0
    )
    gravity = w_n * grade
    rolling = crr * w_n
    air_drag = 0.5 * POWER_CONSTANTS["air_density"] * cda * v_ms**2
    total_force = gravity + rolling + air_drag
    power = total_force * v_ms
    watts_per_kg = power / weight if weight > 0 else 0
    duration_s = ride.duration_minutes * 60
    w_prime = power * duration_s if power > 0 else 0
    if total_force > 0:
        grav_pct = gravity / total_force * 100
        roll_pct = rolling / total_force * 100
        air_pct = air_drag / total_force * 100
    else:
        grav_pct = roll_pct = air_pct = 0.0
    return {
        "power_avg_w": round(power, 0),
        "power_per_kg_w": round(watts_per_kg, 1),
        "w_prime_j": round(w_prime, 0),
        "cd_wind": round(air_pct, 1),
        "cd_rolling": round(roll_pct, 1),
        "cd_gravity": round(grav_pct, 1),
        "grade_percent": round(grade * 100, 1),
        "speed_ms": round(v_ms, 2),
    }


def classify_climb(segment_length_km: float, avg_gradient_percent: float) -> dict[str, Any]:
    if segment_length_km < 0.3 or avg_gradient_percent < 2:
        return {"category": "none", "difficulty_score": 0, "color": "#999", "points": 0}
    for cat, threshold in CLIMB_CATEGORIES:
        if avg_gradient_percent >= threshold:
            return {
                "category": cat,
                "difficulty_score": round(avg_gradient_percent, 1),
                "color": _get_climb_color(cat),
                "points": _CLIMB_POINTS.get(cat, 0),
            }
    return {"category": "none", "difficulty_score": 0, "color": "#999", "points": 0}


def estimate_vo2max(
    avg_speed_kmh: float, avg_gradient_percent: float, weight_kg: float, age: int = 35
) -> dict[str, float]:
    speed_match_kmh = 21.0 - (age - 30) * 0.1
    speed_factor = avg_speed_kmh / speed_match_kmh if speed_match_kmh > 0 else 1.0
    gradient_factor = 1.0 + avg_gradient_percent * 0.03
    base_vo2 = 42.0 - (age - 30) * 0.5
    vo2 = base_vo2 * speed_factor * gradient_factor
    vo2 = max(30.0, min(75.0, vo2))
    if vo2 < 40:
        level = "Below Average"
    elif vo2 < 50:
        level = "Average"
    elif vo2 < 58:
        level = "Good"
    elif vo2 < 65:
        level = "Very Good"
    else:
        level = "Excellent"
    return {
        "vo2_max_ml_kg_min": round(vo2, 1),
        "fitness_level": level,
        "age": age,
        "speed_match_kmh": round(speed_match_kmh, 1),
    }


def classify_ride_difficulty(ride: Ride) -> dict[str, Any]:
    if ride.distance_km <= 0:
        return {"score": 0, "level": "unknown", "factors": {}}
    grade_factor = (
        min((ride.elevation_gain_m / ride.distance_km) / 30.0, 1.0)
        if ride.elevation_gain_m and ride.distance_km > 0
        else 0
    )
    dist_factor = min(ride.distance_km / 150.0, 1.0)
    dur_factor = min(ride.duration_hours / 5.0, 1.0)
    speed_factor = min(ride.avg_speed_kmh / 35.0, 1.0)
    hr_factor = min((ride.heart_rate_avg / 180) if ride.heart_rate_avg else 0.5, 1.0)
    score = (
        grade_factor * 0.30
        + dist_factor * 0.20
        + dur_factor * 0.20
        + speed_factor * 0.15
        + hr_factor * 0.15
    )
    if score < 0.2:
        level = "Easy"
    elif score < 0.4:
        level = "Moderate"
    elif score < 0.6:
        level = "Challenging"
    elif score < 0.8:
        level = "Hard"
    else:
        level = "Extreme"
    return {
        "score": round(score * 10, 1),
        "level": level,
        "factors": {
            "grade": round(grade_factor * 30, 1),
            "distance": round(dist_factor * 20, 1),
            "duration": round(dur_factor * 20, 1),
            "speed": round(speed_factor * 15, 1),
            "heart_rate": round(hr_factor * 15, 1),
        },
    }


def analyze_elevation_profile(points: list[GPSPoint]) -> dict[str, Any]:
    if not points or len(points) < 2:
        return {"grade_distribution": {}, "hardship_index": 0.0, "max_grade": 0.0, "min_grade": 0.0}
    grades: dict[str, int] = {"flat": 0, "easy": 0, "moderate": 0, "steep": 0, "extreme": 0}
    max_grade = 0.0
    for i in range(1, len(points)):
        if points[i].altitude is not None and points[i - 1].altitude is not None:
            dist_m = haversine_distance_m(
                points[i - 1].lat, points[i - 1].lon, points[i].lat, points[i].lon
            )
            elev_change = points[i].altitude - points[i - 1].altitude
            if dist_m > 0:
                grade_pct = (elev_change / dist_m) * 100
                max_grade = max(max_grade, abs(grade_pct))
                if abs(grade_pct) < 3:
                    grades["flat"] += 1
                elif abs(grade_pct) < 6:
                    grades["easy"] += 1
                elif abs(grade_pct) < 10:
                    grades["moderate"] += 1
                elif abs(grade_pct) < 15:
                    grades["steep"] += 1
                else:
                    grades["extreme"] += 1
    total = sum(grades.values()) or 1
    hardship = (
        (grades.get("steep", 0) * 3 + grades.get("extreme", 0) * 5 + grades.get("moderate", 0) * 1)
        / total
        * 100
    )
    return {
        "grade_distribution": {k: round(v / total * 100, 1) for k, v in grades.items()},
        "hardship_index": round(hardship, 1),
        "total_sampled": total,
    }


def analyze_speed_profile(points: list[GPSPoint]) -> dict[str, Any]:
    speeds = [p.speed for p in points if p.speed is not None and p.speed > 0]
    if not speeds or len(speeds) < 2:
        return {
            "acceleration_events": 0,
            "deceleration_events": 0,
            "speed_variance": 0.0,
            "coasting_time_pct": 0.0,
        }
    thr_acc = 2.0
    thr_dec = -2.0
    accels = sum(1 for i in range(1, len(speeds)) if speeds[i] - speeds[i - 1] >= thr_acc)
    decels = sum(1 for i in range(1, len(speeds)) if speeds[i] - speeds[i - 1] <= thr_dec)
    mean_spd = sum(speeds) / len(speeds)
    variance = sum((s - mean_spd) ** 2 for s in speeds) / len(speeds)
    coasting = sum(1 for s in speeds if abs(s - mean_spd) < 1.0) / len(speeds) * 100
    return {
        "acceleration_events": accels,
        "deceleration_events": decels,
        "speed_variance": round(variance, 2),
        "coasting_time_pct": round(coasting, 1),
        "speed_range": round(max(speeds) - min(speeds), 1),
    }


def calculate_progress_trend(rides: list[Ride], metric: str = "avg_speed_kmh") -> dict[str, Any]:
    if not rides or len(rides) < 2:
        return {
            "trend": "insufficient_data",
            "slope": 0.0,
            "r_squared": 0.0,
            "improvement_pct": 0.0,
        }
    sorted_rides = sorted(rides, key=lambda r: r.date)
    values = []
    for r in sorted_rides:
        v = getattr(r, metric)
        if v is not None and isinstance(v, (int, float)):
            values.append(v)
    if len(values) < 2:
        return {
            "trend": "insufficient_data",
            "slope": 0.0,
            "r_squared": 0.0,
            "improvement_pct": 0.0,
        }
    n = len(values)
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    ss_xy = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    ss_xx = sum((i - x_mean) ** 2 for i in range(n))
    ss_yy = sum((v - y_mean) ** 2 for v in values)
    slope = ss_xy / ss_xx if ss_xx != 0 else 0
    r_squared = ss_xy ** 2 / (ss_xx * ss_yy) if ss_yy > 0 and ss_xx > 0 else 0.0
    improvement = ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0
    if slope > 0.05:
        trend = "improving"
    elif slope < -0.05:
        trend = "declining"
    else:
        trend = "stable"
    return {
        "trend": trend,
        "slope": round(slope, 4),
        "r_squared": round(r_squared, 3),
        "improvement_pct": round(improvement, 1),
        "first_value": round(values[0], 2),
        "last_value": round(values[-1], 2),
        "data_points": n,
    }


def calculate_training_stress_balance(
    rides: list[Ride], atl_tau_days: float = 7.0, ctl_tau_days: float = 42.0
) -> dict[str, Any]:
    if not rides:
        return {"atl": 0.0, "ctl": 0.0, "tsb": 0.0, "form": "no_data", "daily_load": []}
    sorted_rides = sorted(rides, key=lambda r: r.date)
    daily_tss: dict[str, float] = {}
    for ride in sorted_rides:
        date_key = ride.date[:10] if len(ride.date) >= 10 else ride.date
        from .training_load import calculate_rss

        tss = calculate_rss(ride)
        daily_tss[date_key] = daily_tss.get(date_key, 0.0) + tss
    if not daily_tss:
        return {"atl": 0.0, "ctl": 0.0, "tsb": 0.0, "form": "no_data", "daily_load": []}
    from datetime import datetime, timedelta

    dates = sorted(daily_tss.keys())
    first = datetime.fromisoformat(dates[0])
    end = datetime.now()
    all_dates: list[str] = []
    cur = first
    while cur <= end:
        all_dates.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    alpha_atl = 1.0 - math.exp(-1.0 / atl_tau_days)
    alpha_ctl = 1.0 - math.exp(-1.0 / ctl_tau_days)
    result: list[dict[str, Any]] = []
    atl, ctl = 0.0, 0.0
    for _i, date in enumerate(all_dates):
        tss = daily_tss.get(date, 0.0)
        atl = alpha_atl * tss + (1 - alpha_atl) * atl
        ctl = alpha_ctl * tss + (1 - alpha_ctl) * ctl
        tsb = ctl - atl
        if tsb > 10:
            form = "fresh"
        elif tsb > 0:
            form = "optimal"
        elif tsb > -10:
            form = "fatigued"
        elif tsb > -20:
            form = "overreached"
        else:
            form = "burnout_risk"
        result.append(
            {
                "date": date,
                "tss": round(tss, 1),
                "atl": round(atl, 1),
                "ctl": round(ctl, 1),
                "tsb": round(tsb, 1),
                "form": form,
            }
        )
    latest = result[-1]
    return {
        "atl": latest["atl"],
        "ctl": latest["ctl"],
        "tsb": latest["tsb"],
        "form": latest["form"],
        "daily_load": result[-14:],
    }


def estimate_ideal_weight(ftp: float, height_cm: float, experience: str = "Intermediate") -> float:
    if ftp <= 0 or height_cm <= 0:
        return 70.0
    ftp_per_kg = ftp / 70.0
    if ftp_per_kg >= 5:
        ideal_w_per_kg = 4.2
    elif ftp_per_kg >= 4:
        ideal_w_per_kg = 4.5
    elif ftp_per_kg >= 3:
        ideal_w_per_kg = 4.8
    else:
        ideal_w_per_kg = 5.2
    return round(ftp / ideal_w_per_kg, 1)


def calculate_garmin_power_factor(ride: Ride, weight_kg: float | None = None) -> dict[str, float]:
    w = weight_kg or ride.weight_kg
    if ride.avg_speed_kmh <= 0 or w <= 0:
        return {"pf": 0.0, "np_w": 0.0, "if": 0.0}
    v_ms = ride.avg_speed_kmh * 1000 / 3600
    grade = (
        ride.elevation_gain_m / (ride.distance_km * 1000)
        if ride.elevation_gain_m and ride.distance_km and ride.distance_km > 0
        else 0
    )
    total_w = w + 8.0
    w_n = total_w * POWER_CONSTANTS["g"]
    p_roll = POWER_CONSTANTS["crr_road"] * w_n * v_ms
    p_grav = w_n * grade * v_ms
    p_air = 0.5 * POWER_CONSTANTS["air_density"] * POWER_CONSTANTS["cd_a_road"] * v_ms**3
    p_total = p_roll + p_grav + p_air
    duration_h = ride.duration_hours
    tss = duration_h * 100 * (min(ride.avg_speed_kmh / 35.0, 1.0) ** 2) if duration_h > 0 else 0
    np = p_total * 1.05
    if_val = np / (w * POWER_CONSTANTS["neuromuscular_efficiency"] * 3600) if w > 0 else 0
    pf = min(np / (w * 2.5), 6.0) if w > 0 else 1.0
    return {
        "pf": round(pf, 2),
        "np_w": round(np, 0),
        "if": round(if_val, 2),
        "tss_est": round(tss, 0),
    }


def calculate_heart_rate_zones(
    max_hr: int = 180, lthr: int = 155, current_avg_hr: float | None = None
) -> dict[str, dict[str, Any]]:
    zones: dict[str, dict[str, Any]] = {
        "Z1 (Recovery)": {
            "min": int(max_hr * 0.55),
            "max": int(max_hr * 0.64),
            "benefit": "Active recovery, warm-up",
        },
        "Z2 (Endurance)": {
            "min": int(max_hr * 0.64),
            "max": int(max_hr * 0.74),
            "benefit": "Aerobic base, fat burning",
        },
        "Z3 (Tempo)": {
            "min": int(max_hr * 0.74),
            "max": int(max_hr * 0.84),
            "benefit": "Sustained threshold effort",
        },
        "Z4 (Threshold)": {
            "min": int(max_hr * 0.84),
            "max": int(max_hr * 0.94),
            "benefit": "Lactate threshold, FTP improvement",
        },
        "Z5 (VO2max)": {
            "min": int(max_hr * 0.94),
            "max": max_hr,
            "benefit": "VO2max intervals, anaerobic",
        },
    }
    if current_avg_hr is not None:
        for z in zones.values():
            z["in_zone"] = z["min"] <= current_avg_hr <= z["max"]
    return zones


def calculate_ride_recommendation_score(
    ride: Ride, athlete_weekly_km: float = 50.0
) -> dict[str, Any]:
    volume_score = (
        min(ride.distance_km / (athlete_weekly_km / 7 * 0.5) * 10, 10)
        if athlete_weekly_km > 0
        else 5
    )
    intensity_score = min(ride.avg_speed_kmh / 25.0 * 10, 10)
    elevation_score = (
        min((ride.elevation_gain_m / ride.distance_km) / 20.0 * 10, 10)
        if ride.elevation_gain_m and ride.distance_km and ride.distance_km > 0
        else 0
    )
    total = volume_score * 0.35 + intensity_score * 0.35 + elevation_score * 0.30
    if total < 5:
        label = "Recovery Ride"
    elif total < 7:
        label = "Tempo Ride"
    elif total < 9:
        label = "Hard Training"
    else:
        label = "Race / Peak Effort"
    return {
        "overall_score": round(total, 1),
        "label": label,
        "volume_score": round(volume_score, 1),
        "intensity_score": round(intensity_score, 1),
        "elevation_score": round(elevation_score, 1),
    }


def detect_speed_surges(
    points: list[GPSPoint], threshold_kmh: float = 5.0, min_speed_kmh: float = 15.0
) -> list[dict[str, Any]]:
    if len(points) < 2:
        return []
    surges = []
    for i in range(1, len(points)):
        prev, curr = points[i - 1], points[i]
        if prev.speed is not None and curr.speed is not None:
            delta = curr.speed - prev.speed
            if delta >= threshold_kmh and curr.speed >= min_speed_kmh:
                surges.append(
                    {
                        "index": i,
                        "speed_jump_kmh": round(delta, 1),
                        "speed_kmh": round(curr.speed, 1),
                    }
                )
    return surges


if ENDURANCE_METRICS_AVAILABLE:

    def compute_ctl_atl_tsb_external(rides: list[Ride]) -> dict[str, Any]:
        activities = []
        for ride in rides:
            date = ride.date[:10] if len(ride.date) >= 10 else ride.date
            activities.append({"date": date, "load": ride.calories / 100.0})
        ctl, atl, tsb = calculate_tsb(activities)
        return {"ctl": round(ctl, 1), "atl": round(atl, 1), "tsb": round(tsb, 1)}
else:

    def compute_ctl_atl_tsb_external(rides: list[Ride]) -> dict[str, Any]:
        return calculate_training_stress_balance(rides)


__all__ = [
    "calculate_pace_consistency",
    "calculate_power_estimate",
    "classify_climb",
    "estimate_vo2max",
    "classify_ride_difficulty",
    "analyze_elevation_profile",
    "analyze_speed_profile",
    "calculate_progress_trend",
    "calculate_training_stress_balance",
    "estimate_ideal_weight",
    "calculate_garmin_power_factor",
    "calculate_heart_rate_zones",
    "calculate_ride_recommendation_score",
    "detect_speed_surges",
    "compute_ctl_atl_tsb_external",
    "ENDURANCE_METRICS_AVAILABLE",
    "POWER_CONSTANTS",
    "CLIMB_CATEGORIES",
]
