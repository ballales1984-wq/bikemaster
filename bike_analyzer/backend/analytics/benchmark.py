"""Athlete benchmark comparison system."""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from ..models.models import Ride, AthleteProfile

BENCHMARK_DATA = {
    "Male": {
        "Beginner": {"avg_speed": 20, "weekly_km": 50, "annual_km": 1000},
        "Amateur": {"avg_speed": 25, "weekly_km": 100, "annual_km": 2500},
        "Intermediate": {"avg_speed": 28, "weekly_km": 150, "annual_km": 5000},
        "Advanced": {"avg_speed": 32, "weekly_km": 250, "annual_km": 10000},
        "Elite": {"avg_speed": 35, "weekly_km": 400, "annual_km": 15000}
    },
    "Female": {
        "Beginner": {"avg_speed": 18, "weekly_km": 40, "annual_km": 800},
        "Amateur": {"avg_speed": 22, "weekly_km": 80, "annual_km": 2000},
        "Intermediate": {"avg_speed": 25, "weekly_km": 120, "annual_km": 4000},
        "Advanced": {"avg_speed": 28, "weekly_km": 200, "annual_km": 8000},
        "Elite": {"avg_speed": 32, "weekly_km": 350, "annual_km": 12000}
    }
}

def calculate_percentile(value: float, benchmark: float) -> float:
    if value >= benchmark * 1.2: return 95.0
    if value >= benchmark * 1.1: return 85.0
    if value >= benchmark: return 70.0
    if value >= benchmark * 0.9: return 55.0
    if value >= benchmark * 0.8: return 40.0
    if value >= benchmark * 0.7: return 25.0
    return 10.0

def compare_with_benchmark(ride: Ride, athlete: Optional[AthleteProfile] = None) -> Dict[str, Any]:
    gender = "Male" if not athlete or athlete.weight_kg >= 70 else "Female"
    level = athlete.experience_level if athlete else "Amateur"
    bench = BENCHMARK_DATA.get(gender, {}).get(level, BENCHMARK_DATA["Male"]["Amateur"])
    speed_pct = calculate_percentile(ride.avg_speed_kmh, bench["avg_speed"])
    return {"speed_percentile": speed_pct, "benchmark_speed": bench["avg_speed"], "speed_vs_benchmark": (ride.avg_speed_kmh / bench["avg_speed"] * 100) if bench["avg_speed"] else 0}

def get_age_category(age: int) -> str:
    if age < 25: return "Under25"
    if age < 35: return "Age25-34"
    if age < 45: return "Age35-44"
    if age < 55: return "Age45-54"
    return "Over55"

def get_weight_category(weight_kg: float) -> str:
    if weight_kg < 60: return "Light"
    if weight_kg < 75: return "Medium"
    if weight_kg < 90: return "Heavy"
    return "VeryHeavy"

def generate_benchmark_report(rides: List[Ride], athlete: Optional[AthleteProfile] = None) -> str:
    if not rides: return "No rides to analyze"
    avg_speed = sum(r.avg_speed_kmh for r in rides) / len(rides)
    total_km = sum(r.distance_km for r in rides)
    comp = compare_with_benchmark(rides[0], athlete)
    return f"BikeMaster Benchmark Report\nAvg Speed: {avg_speed:.1f} km/h (Percentile: {comp['speed_percentile']}%)\nTotal Distance: {total_km:.1f} km"