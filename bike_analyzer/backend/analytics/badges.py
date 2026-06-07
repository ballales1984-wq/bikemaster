"""Badge/Medal system for cycling achievements."""
from __future__ import annotations
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta


BADGE_DEFINITIONS = [
    {"id": 1, "name": "Prima Uscita", "description": "Completa la tua prima uscita", "icon": "🚴", "category": "milestone", "target": 1},
    {"id": 2, "name": "Centomiglia", "description": "Total 100km in rides", "icon": "💯", "category": "distance", "target": 100},
    {"id": 3, "name": "Migliaia", "description": "Total 1000km in rides", "icon": "🏔️", "category": "distance", "target": 1000},
    {"id": 4, "name": "Maratona", "description": "Total 10000km in rides", "icon": "🏆", "category": "distance", "target": 10000},
    {"id": 5, "name": "Coppia di Uscite", "description": "Complete 10 rides", "icon": "📅", "category": "milestone", "target": 10},
    {"id": 6, "name": "Centomila", "description": "Total 100 rides completed", "icon": "💯", "category": "milestone", "target": 100},
    {"id": 7, "name": "Elevazione", "description": "Total 5000m elevation gain", "icon": "⛰️", "category": "elevation", "target": 5000},
    {"id": 8, "name": "Salita d'Acciaio", "description": "Total 10000m elevation gain", "icon": "🏔️", "category": "elevation", "target": 10000},
    {"id": 9, "name": "Velocità", "description": "Achieve 30+ km/h average speed", "icon": "⚡", "category": "speed", "target": 30},
    {"id": 10, "name": "Velocità Supersonica", "description": "Achieve 35+ km/h average speed", "icon": "🚀", "category": "speed", "target": 35},
    {"id": 11, "name": "Allenatore", "description": "7-day training streak", "icon": "📆", "category": "consistency", "target": 7},
    {"id": 12, "name": "Dedicato", "description": "30-day training streak", "icon": "📆", "category": "consistency", "target": 30},
]


def calculate_badges(athlete_id: int, rides: List[dict], athlete: Optional[dict] = None) -> List[dict]:
    """Calculate badge achievements for an athlete based on rides."""
    total_km = sum(r.get("distance_km", 0) for r in rides)
    total_rides = len(rides)
    total_elevation = sum(r.get("elevation_gain_m", 0) or 0 for r in rides)
    
    max_speed = 0.0
    for r in rides:
        avg = r.get("avg_speed_kmh", 0) or 0
        max_speed = max(max_speed, avg)
    
    streak_days = calculate_streak(rides)
    
    achieved = []
    for badge in BADGE_DEFINITIONS:
        progress = 0.0
        unlocked = False
        
        if badge["category"] == "distance":
            progress = min(total_km / badge["target"], 1.0)
            unlocked = total_km >= badge["target"]
        elif badge["category"] == "elevation":
            progress = min(total_elevation / badge["target"], 1.0)
            unlocked = total_elevation >= badge["target"]
        elif badge["category"] == "speed":
            progress = min(max_speed / badge["target"], 1.0) if max_speed > 0 else 0
            unlocked = max_speed >= badge["target"]
        elif badge["category"] == "milestone":
            if badge["target"] == 1:
                progress = 1.0 if total_rides > 0 else 0.0
                unlocked = total_rides >= 1
            else:
                progress = min(total_rides / badge["target"], 1.0)
                unlocked = total_rides >= badge["target"]
        elif badge["category"] == "consistency":
            progress = min(streak_days / badge["target"], 1.0)
            unlocked = streak_days >= badge["target"]
        
        achieved.append({
            "id": badge["id"],
            "name": badge["name"],
            "description": badge["description"],
            "icon": badge["icon"],
            "category": badge["category"],
            "achieved": unlocked,
            "progress": round(progress * 100, 1),
            "target": badge["target"],
        })
    
    return achieved


def calculate_streak(rides: List[dict]) -> int:
    """Calculate current consecutive day streak from rides."""
    if not rides:
        return 0
    dates = sorted(set(r.get("date", "")[:10] for r in rides if r.get("date")))
    if not dates:
        return 0
    
    streak = 0
    today = datetime.now(timezone.utc).date()
    for i in range(len(dates) - 1, -1, -1):
        try:
            ride_date = datetime.fromisoformat(dates[i]).date()
            expected = today - timedelta(days=streak)
            if ride_date == expected:
                streak += 1
            elif ride_date < expected:
                break
        except (ValueError, TypeError):
            continue
    return streak


def get_heatmap_points(rides: List[dict], grid_size: float = 0.001) -> dict:
    """Aggregate GPS points into heatmap grid cells."""
    all_points = []
    for ride in rides:
        for pt in (ride.get("gps_points") or []):
            lat, lon = pt.get("lat"), pt.get("lon")
            if lat and lon:
                all_points.append({"lat": lat, "lon": lon})
    
    if not all_points:
        return {"points": [], "bounds": {"min_lat": 0, "max_lat": 0, "min_lon": 0, "max_lon": 0}, "total_points": 0}
    
    grid = {}
    for pt in all_points:
        lat_key = round(pt["lat"] / grid_size) * grid_size
        lon_key = round(pt["lon"] / grid_size) * grid_size
        key = (lat_key, lon_key)
        grid[key] = grid.get(key, 0) + 1
    
    points = [{"lat": k[0], "lon": k[1], "count": v} for k, v in grid.items()]
    
    lats = [p["lat"] for p in points]
    lons = [p["lon"] for p in points]
    bounds = {
        "min_lat": min(lats) if lats else 0,
        "max_lat": max(lats) if lats else 0,
        "min_lon": min(lons) if lons else 0,
        "max_lon": max(lons) if lons else 0,
    }
    
    return {"points": points, "bounds": bounds, "total_points": len(all_points)}


__all__ = ["calculate_badges", "get_heatmap_points", "BADGE_DEFINITIONS"]