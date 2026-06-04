"""Sample ride data generator for testing and demos"""

import random
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np

from bike_analyzer.backend.processing import GPSPoint, process_route
from bike_analyzer.backend.processing.processing import haversine_distance_m

def _circular_walk(
    center_lat: float, center_lon: float,
    radius_km: float, n_points: int,
    noise_m: float = 15.0,
) -> tuple[list[float], list[float]]:
    angle = np.linspace(0, 2 * np.pi, n_points)
    r = radius_km * 1000 + np.random.normal(0, noise_m, n_points)
    dlat = (r * np.cos(angle)) / 111320.0
    dlon = (r * np.sin(angle)) / (111320.0 * np.cos(np.radians(center_lat)))
    lats = center_lat + dlat
    lons = center_lon + dlon
    return lats.tolist(), lons.tolist()

def generate_sample_ride(
    n_points: int = 100,
    center_lat: float = 45.4654,
    center_lon: float = 9.1859,
    radius_km: float = 8.0,
    duration_minutes: int = 60,
    avg_speed_kmh: float = 22.0,
) -> list[GPSPoint]:
    lats, lons = _circular_walk(center_lat, center_lon, radius_km, n_points)
    base_time = datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
    dt = duration_minutes * 60 / n_points
    return [GPSPoint(lat=lats[i], lon=lons[i], timestamp=base_time + timedelta(seconds=i * dt)) for i in range(n_points)]

if __name__ == "__main__":
    points = generate_sample_ride()
    processed, stats = process_route(points)
    print(f"Generated {len(points)} points, processed: {stats.total_distance_m:.1f}m, avg speed: {stats.avg_speed_km_h:.1f}km/h")