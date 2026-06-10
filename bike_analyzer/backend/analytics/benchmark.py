"""Benchmark engine for athlete comparison."""

from __future__ import annotations

from ..models.models import AthleteProfile

BENCHMARK_DATA = {
    "Beginner": {"total_km": (0, 100), "avg_speed": (0, 20), "weekly_hours": (0, 3)},
    "Amateur": {"total_km": (100, 500), "avg_speed": (20, 25), "weekly_hours": (3, 6)},
    "Intermediate": {"total_km": (500, 1500), "avg_speed": (25, 28), "weekly_hours": (6, 10)},
    "Advanced": {"total_km": (1500, 3000), "avg_speed": (28, 32), "weekly_hours": (10, 15)},
    "Elite": {"total_km": (3000, 10000), "avg_speed": (32, 40), "weekly_hours": (15, 30)},
}

AGE_CATEGORIES = {
    "Under25": (0, 25),
    "25-35": (25, 35),
    "35-45": (35, 45),
    "45-55": (45, 55),
    "Over55": (55, 100),
}
WEIGHT_CATEGORIES = {"Lightweight": (0, 65), "Medium": (65, 80), "Heavy": (80, 150)}
EXPERIENCE_CATEGORIES = {
    "Beginner": (0, 1),
    "Novice": (1, 3),
    "Experienced": (3, 7),
    "Veteran": (7, 20),
    "Legend": (20, 100),
}


def compare_athlete_to_benchmark(
    athlete: AthleteProfile, total_km: float, avg_speed: float, total_hours: float
) -> dict[str, float | None]:
    level = athlete.experience_level
    if level not in BENCHMARK_DATA:
        return {}
    bench = BENCHMARK_DATA[level]
    pct_km = (
        min(
            100,
            (total_km - bench["total_km"][0]) / (bench["total_km"][1] - bench["total_km"][0]) * 100,
        )
        if bench["total_km"][1] > bench["total_km"][0]
        else 50
    )
    pct_speed = (
        min(
            100,
            (avg_speed - bench["avg_speed"][0])
            / (bench["avg_speed"][1] - bench["avg_speed"][0])
            * 100,
        )
        if bench["avg_speed"][1] > bench["avg_speed"][0]
        else 50
    )
    pct_hours = (
        min(
            100,
            (total_hours - bench["weekly_hours"][0])
            / (bench["weekly_hours"][1] - bench["weekly_hours"][0])
            * 100,
        )
        if bench["weekly_hours"][1] > bench["weekly_hours"][0]
        else 50
    )
    return {
        "percentile_km": max(0, pct_km),
        "percentile_speed": max(0, pct_speed),
        "percentile_hours": max(0, pct_hours),
        "overall_percentile": round((pct_km + pct_speed + pct_hours) / 3, 1),
    }


compare_with_benchmark = compare_athlete_to_benchmark


def get_age_category(age: int) -> str:
    for cat, (low, high) in AGE_CATEGORIES.items():
        if low <= age < high:
            return cat
    return "Over55"


def get_weight_category(weight_kg: float) -> str:
    for cat, (low, high) in WEIGHT_CATEGORIES.items():
        if low <= weight_kg < high:
            return cat
    return "Heavy"


def get_experience_category(years: int) -> str:
    for cat, (low, high) in EXPERIENCE_CATEGORIES.items():
        if low <= years < high:
            return cat
    return "Legend"


def generate_benchmark_report(athlete: AthleteProfile, rides: list) -> str:
    total_km = sum(r.distance_km for r in rides) if rides else 0
    avg_speed = sum(r.avg_speed_kmh for r in rides) / len(rides) if rides else 0
    total_hours = sum(r.duration_hours for r in rides)
    comparison = compare_athlete_to_benchmark(athlete, total_km, avg_speed, total_hours)
    return f"Benchmark Report\nAtleta: {athlete.name}\nLevel: {athlete.experience_level}\nAge: {athlete.age} ({get_age_category(athlete.age)})\nWeight: {athlete.weight_kg}kg ({get_weight_category(athlete.weight_kg)})\nExperience: {athlete.years_active} years ({get_experience_category(athlete.years_active)})\nPercentile: {comparison.get('overall_percentile', 0)}%\nTotal km: {total_km:.0f} (level average: {BENCHMARK_DATA.get(athlete.experience_level, {}).get('total_km', (0, 0))})"
