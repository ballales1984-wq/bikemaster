"""Analytics engine for ride analysis."""
from __future__ import annotations
import math
from typing import List, Optional
from ..models.models import Ride, GPSPoint, Segment
from .calories import estimate_calories
from .fatigue import calculate_fatigue_score, estimate_recovery_hours, get_recovery_recommendation
import json
import csv
from io import StringIO
from tempfile import NamedTemporaryFile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    return 2 * 6_371_000 * math.asin(math.sqrt(math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2))

def calculate_summary(rides: List[Ride]) -> dict:
    if not rides: return {"total_rides": 0, "total_km": 0.0, "total_calories": 0.0, "avg_speed": 0.0, "avg_fatigue": 0.0}
    return {"total_rides": len(rides), "total_km": round(sum(r.distance_km for r in rides), 1), "total_calories": round(sum(r.calories for r in rides), 0), "avg_speed": round(sum(r.avg_speed_kmh for r in rides) / len(rides), 1), "avg_fatigue": round(sum(calculate_fatigue_score(r) for r in rides) / len(rides), 1)}

def analyze_ride(ride: Ride) -> dict:
    fatigue = calculate_fatigue_score(ride)
    return {"ride_id": ride.id, "date": ride.date, "distance_km": ride.distance_km, "duration_minutes": ride.duration_minutes, "avg_speed_kmh": ride.avg_speed_kmh, "calories": ride.calories, "fatigue_score": round(fatigue, 1), "recovery_hours": estimate_recovery_hours(fatigue), "recovery_recommendation": get_recovery_recommendation(fatigue)}

def ride_to_json(ride: Ride) -> str:
    return json.dumps(ride.to_dict(), indent=2)

def rides_to_json(rides: List[Ride]) -> str:
    return json.dumps([r.to_dict() for r in rides], indent=2)

def rides_to_csv(rides: List[Ride]) -> str:
    output = StringIO()
    if not rides: return ""
    writer = csv.writer(output)
    writer.writerow(["date", "distance_km", "duration_minutes", "avg_speed_kmh", "weight_kg", "calories", "heart_rate_avg", "elevation_gain_m"])
    for r in rides: writer.writerow([r.date, r.distance_km, r.duration_minutes, r.avg_speed_kmh, r.weight_kg, r.calories, r.heart_rate_avg or "", r.elevation_gain_m or ""])
    return output.getvalue()

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
    return f"BikeMaster Report\nDate: {a['date']}\nDistance: {a['distance_km']} km\nDuration: {a['duration_minutes']} min\nAvg Speed: {a['avg_speed_kmh']} km/h\nCalories: {a['calories']}\nFatigue Score: {a['fatigue_score']}/10\nRecovery: {a['recovery_hours']}h - {a['recovery_recommendation']}"

def create_speed_chart(segments: List[Segment], output_path: str = "speed_chart.png") -> str:
    speeds = [s.avg_speed_km_h for s in segments] if segments else [0]
    plt.figure(figsize=(10, 4))
    plt.plot(speeds, color="#FF6B00", linewidth=2)
    plt.title("Speed Profile")
    plt.ylabel("km/h")
    plt.xlabel("Segment")
    plt.savefig(output_path)
    plt.close()
    return output_path

def create_elevation_chart(segments: List[Segment], output_path: str = "elevation_chart.png") -> str:
    elev = [s.elevation_gain_m for s in segments] if segments else [0]
    plt.figure(figsize=(10, 4))
    plt.fill_between(range(len(elev)), elev, color="#4ecca3", alpha=0.7)
    plt.title("Elevation per Segment")
    plt.ylabel("m")
    plt.xlabel("Segment")
    plt.savefig(output_path)
    plt.close()
    return output_path

def create_duration_chart(rides: List[Ride], output_path: str = "duration_chart.png") -> str:
    durations = [r.duration_minutes for r in rides] if rides else [0]
    labels = [r.date for r in rides] if rides else ["No rides"]
    plt.figure(figsize=(10, 4))
    plt.bar(labels, durations, color="#4ecca3")
    plt.title("Ride Duration")
    plt.ylabel("minutes")
    plt.xticks(rotation=45)
    plt.savefig(output_path)
    plt.close()
    return output_path

def create_distance_chart(segments: List[Segment], output_path: str = "distance_chart.png") -> str:
    distances = [s.distance_m / 1000 for s in segments] if segments else [0]
    plt.figure(figsize=(10, 4))
    plt.plot(range(len(distances)), distances, color="#FF6B00", linewidth=2)
    plt.title("Distance per Segment")
    plt.ylabel("km")
    plt.xlabel("Segment")
    plt.savefig(output_path)
    plt.close()
    return output_path

def generate_speed_chart(points: Optional[List[GPSPoint]], title: str = "Speed Profile") -> str:
    if not points: return ""
    speeds = [p.speed for p in points if p.speed is not None]
    if not speeds: return ""
    plt.figure(figsize=(10, 4))
    plt.plot(range(len(speeds)), speeds, color="#FF6B00", linewidth=2)
    plt.title(title)
    plt.ylabel("km/h")
    plt.xlabel("Point")
    f = NamedTemporaryFile(suffix=".png", delete=False)
    plt.savefig(f.name)
    plt.close()
    return f.name

def generate_distance_chart(points: Optional[List[GPSPoint]], title: str = "Distance Progression") -> str:
    if not points: return ""
    distances = [0.0]
    total = 0.0
    for i in range(1, len(points)):
        total += haversine_distance_m(points[i-1].lat, points[i-1].lon, points[i].lat, points[i].lon)
        distances.append(total / 1000)
    plt.figure(figsize=(10, 4))
    plt.plot(range(len(distances)), distances, color="#0066CC", linewidth=2)
    plt.title(title)
    plt.ylabel("km")
    plt.xlabel("Point")
    f = NamedTemporaryFile(suffix=".png", delete=False)
    plt.savefig(f.name)
    plt.close()
    return f.name

def generate_time_chart(points: Optional[List[GPSPoint]], title: str = "Time Analysis") -> str:
    if not points: return ""
    times = [p.timestamp.strftime("%H:%M") for p in points]
    plt.figure(figsize=(10, 2))
    plt.plot(range(len(times)), [1] * len(times), "o", markersize=3, color="#333333")
    plt.title(title)
    plt.yticks([])
    f = NamedTemporaryFile(suffix=".png", delete=False)
    plt.savefig(f.name)
    plt.close()
    return f.name