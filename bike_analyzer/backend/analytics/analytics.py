"""Analytics engine for ride analysis."""
from __future__ import annotations
from typing import List
import json
import csv
from datetime import datetime, timezone
from ..models.models import Ride, Segment
from .calories import estimate_calories
from .fatigue import calculate_fatigue_score, estimate_recovery_hours, get_recovery_recommendation

def calculate_summary(rides: List[Ride]) -> dict:
    if not rides: return {"total_rides": 0, "total_km": 0.0, "total_calories": 0.0, "avg_speed": 0.0, "avg_fatigue": 0.0}
    return {"total_rides": len(rides), "total_km": round(sum(r.distance_km for r in rides), 1), "total_calories": round(sum(r.calories for r in rides), 0), "avg_speed": round(sum(r.avg_speed_kmh for r in rides) / len(rides), 1), "avg_fatigue": round(sum(calculate_fatigue_score(r) for r in rides) / len(rides), 1)}

def analyze_ride(ride: Ride) -> dict:
    fatigue = calculate_fatigue_score(ride)
    return {"ride_id": ride.id, "date": ride.date, "distance_km": ride.distance_km, "duration_minutes": ride.duration_minutes, "avg_speed_kmh": ride.avg_speed_kmh, "calories": ride.calories, "fatigue_score": round(fatigue, 1), "recovery_hours": estimate_recovery_hours(fatigue), "recovery_recommendation": get_recovery_recommendation(fatigue)}

def export_rides_json(rides: List[Ride], output_path: str = "rides_export.json") -> str:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([r.to_dict() for r in rides], f, indent=2)
    return output_path

def export_rides_csv(rides: List[Ride], output_path: str = "rides_export.csv") -> str:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "distance_km", "duration_minutes", "avg_speed_kmh", "calories", "heart_rate_avg", "elevation_gain_m"])
        for r in rides:
            writer.writerow([r.date, r.distance_km, r.duration_minutes, r.avg_speed_kmh, r.calories, r.heart_rate_avg or "", r.elevation_gain_m or ""])
    return output_path

def generate_text_report(ride: Ride) -> str:
    a = analyze_ride(ride)
    return f"BikeMaster Report\nData: {a['date']}\nDistanza: {a['distance_km']} km\nDurata: {a['duration_minutes']} min\nVelocità Media: {a['avg_speed_kmh']} km/h\nCalorie: {a['calories']}\nFatigue Score: {a['fatigue_score']}/10\nRecupero: {a['recovery_hours']}h - {a['recovery_recommendation']}"

def create_speed_chart(segments: List[Segment], output_path: str = "speed_chart.png") -> str:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    speeds = [s.avg_speed_km_h for s in segments] if segments else [0]
    plt.figure(figsize=(10, 4))
    plt.plot(speeds, color='#4ecca3', linewidth=2)
    plt.title('Velocità nel Percorso')
    plt.ylabel('km/h')
    plt.xlabel('Segmento')
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return output_path

def create_elevation_chart(segments: List[Segment], output_path: str = "elevation_chart.png") -> str:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    elev = [s.elevation_gain_m for s in segments] if segments else [0]
    plt.figure(figsize=(10, 4))
    plt.fill_between(range(len(elev)), elev, color='#4ecca3', alpha=0.7)
    plt.title('Dislivello per Segmento')
    plt.ylabel('m')
    plt.xlabel('Segmento')
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return output_path

def create_duration_chart(rides: List[Ride], output_path: str = "duration_chart.png") -> str:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    durations = [r.duration_minutes for r in rides] if rides else [0]
    labels = [r.date for r in rides] if rides else ['Nessuna ride']
    plt.figure(figsize=(10, 4))
    plt.bar(labels, durations, color='#4ecca3')
    plt.title('Durata per Ride')
    plt.ylabel('minuti')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return output_path