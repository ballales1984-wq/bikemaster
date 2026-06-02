"""Sample ride data generator for testing and demos"""

import random
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

from backend.gps.processor import GPSProcessor
from backend.models.schemas import GPSPointCreate, RideCreate


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
    name: str = "Sample Ride",
    n_points: int = 500,
    center_lat: float = 45.4654,
    center_lon: float = 9.1859,
    radius_km: float = 8.0,
    duration_minutes: int = 60,
    avg_speed_kmh: float = 22.0,
    elevation_start_m: float = 120.0,
    elevation_max_gain: float = 200.0,
    add_noise: bool = True,
    add_hr: bool = True,
    add_power: bool = True,
) -> RideCreate:
    lats, lons = _circular_walk(center_lat, center_lon, radius_km, n_points)

    total_duration_s = duration_minutes * 60
    dt = total_duration_s / n_points
    base_time = datetime.utcnow() - timedelta(days=random.randint(0, 30))

    timestamps = [base_time + timedelta(seconds=i * dt) for i in range(n_points)]

    target_dist_km = avg_speed_kmh * (duration_minutes / 60.0)
    base_dist_per_point = (target_dist_km * 1000) / n_points

    elevations = _generate_elevation(n_points, elevation_start_m, elevation_max_gain, add_noise)

    speeds_ms = []
    current_speed = avg_speed_kmh / 3.6
    for _ in range(n_points - 1):
        current_speed *= random.uniform(0.92, 1.08)
        current_speed = np.clip(current_speed, 2.0, 12.0)
        speeds_ms.append(current_speed)

    heart_rates = _generate_hr(n_points, avg_speed_kmh) if add_hr else [None] * n_points
    powers = _generate_power(n_points, avg_speed_kmh) if add_power else [None] * n_points
    cadences = _generate_cadence(n_points) if add_power else [None] * n_points

    if add_noise:
        lats = _add_gps_noise(lats, 0.00003)
        lons = _add_gps_noise(lons, 0.00003)

    points = []
    for i in range(n_points):
        hr = heart_rates[i] if i < len(heart_rates) else (150 if add_hr else None)
        power = powers[i] if i < len(powers) else (200 if add_power else None)
        cad = cadences[i] if i < len(cadences) else (80 if add_power else None)
        spd = speeds_ms[i] if i < len(speeds_ms) else None

        points.append(GPSPointCreate(
            latitude=lats[i],
            longitude=lons[i],
            elevation=elevations[i],
            timestamp=timestamps[i],
            speed=spd,
            heart_rate=int(hr) if hr is not None else None,
            cadence=int(cad) if cad is not None else None,
            power=int(power) if power is not None else None,
            temperature=round(random.uniform(18.0, 28.0), 1),
        ))

    return RideCreate(name=name, sport_type="cycling", source="generator", gps_points=points)


def _generate_elevation(n: int, start_m: float, max_gain: float, noise: bool) -> list[Optional[float]]:
    t = np.linspace(0, 4 * np.pi, n)
    base = start_m + max_gain * (0.5 + 0.5 * np.sin(t))
    if noise:
        base += np.random.normal(0, 3.0, n)
    return [round(float(v), 1) for v in base]


def _generate_hr(n: int, speed: float) -> list[Optional[int]]:
    base_hr = 130 + (speed - 15) * 4
    hr = base_hr + np.random.normal(0, 8, n)
    return [int(np.clip(v, 90, 195)) for v in hr]


def _generate_power(n: int, speed: float) -> list[Optional[int]]:
    base_power = 150 + (speed - 15) * 8
    p = base_power + np.random.normal(0, 25, n)
    return [int(np.clip(v, 80, 400)) for v in p]


def _generate_cadence(n: int) -> list[Optional[int]]:
    cad = 80 + np.random.normal(0, 4, n)
    return [int(np.clip(v, 60, 110)) for v in cad]


def _add_gps_noise(values: list[float], scale: float) -> list[float]:
    v = np.array(values)
    v += np.random.normal(0, scale, len(v))
    return v.tolist()
