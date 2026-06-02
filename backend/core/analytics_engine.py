"""Core analytics engine - all performance calculations"""

from __future__ import annotations

from typing import Optional

import numpy as np


class AnalyticsEngine:
    """Compute cycling performance metrics from processed GPS data"""

    def __init__(
        self,
        rider_weight_kg: float = 75.0,
        bike_weight_kg: float = 8.5,
        cda: float = 0.32,
        crr: float = 0.004,
        wind_speed_ms: float = 0.0,
        wind_deg: float = 0.0,
    ):
        self.rider_weight_kg = rider_weight_kg
        self.bike_weight_kg = bike_weight_kg
        self.cda = cda  # drag coefficient * frontal area
        self.crr = crr
        self.wind_speed_ms = wind_speed_ms
        self.wind_deg = wind_deg

    def compute_all(self, processed: dict, heart_rates: Optional[list[int]] = None,
                    cadences: Optional[list[int]] = None, powers: Optional[list[int]] = None) -> dict:
        """Return full analytics dict from GPSProcessor output"""
        speed = processed["avg_speed_kmh"]
        max_speed = processed["max_speed_kmh"]
        distance_km = processed["total_distance_m"] / 1000
        duration_s = processed["duration_seconds"]
        min_elev = processed["min_elevation"]
        max_elev = processed["max_elevation"]
        gain = processed["elevation_gain"]
        loss = processed["elevation_loss"]

        avg_hr = self._mean(heart_rates)
        max_hr = self._max(heart_rates)
        avg_cad = self._mean(cadences)
        avg_power = self._mean(powers)

        energy = self._estimate_calories(duration_s, avg_hr, avg_power)

        zone_distribution = self._compute_zone_dist(
            processed["speeds_kmh"], processed["distances_m"]
        )

        return {
            "total_distance_km": round(distance_km, 3),
            "total_duration_seconds": round(duration_s, 1),
            "avg_speed_kmh": round(speed, 2),
            "max_speed_kmh": round(max_speed, 2),
            "min_elevation_m": round(min_elev, 1) if min_elev is not None else None,
            "max_elevation_m": round(max_elev, 1) if max_elev is not None else None,
            "elevation_gain_m": round(gain, 1),
            "elevation_loss_m": round(loss, 1),
            "avg_heart_rate": round(avg_hr, 1) if avg_hr is not None else None,
            "max_heart_rate": round(max_hr, 1) if max_hr is not None else None,
            "avg_cadence": round(avg_cad, 1) if avg_cad is not None else None,
            "energy_kcal": round(energy, 1) if energy is not None else None,
            "avg_power": round(avg_power, 1) if avg_power is not None else None,
            "zone_distribution": zone_distribution,
        }

    def _mean(self, arr: Optional[list]) -> Optional[float]:
        return float(np.mean(arr)) if arr else None

    def _max(self, arr: Optional[list]) -> Optional[float]:
        return float(np.max(arr)) if arr else None

    def _estimate_calories(
        self, duration_s: float, avg_hr: Optional[float], avg_power: Optional[float]
    ) -> Optional[float]:
        """
        Multi-factor calorie estimation:
        - Primary: average power * duration / 4184 J per kcal
        - Fallback: heart rate based (ACSM formula)
        """
        if avg_power and duration_s:
            return (avg_power * duration_s) / 4184.0

        if avg_hr and duration_s:
            age = 30
            weight = self.rider_weight_kg
            gender_factor = 1.0
            calories = (
                (avg_hr * 0.6309 + weight * 0.1988 + age * 0.2017 - 55.0969) * duration_s / 4.184
            )
            return max(calories, 0.0) * gender_factor

        return None

    def _compute_zone_dist(self, speeds: np.ndarray, distances_m: np.ndarray) -> dict:
        """Compute time/distance spent in each power/speed zone"""
        if len(speeds) == 0:
            return {}

        zones = {
            "Z1_recovery": (0, 15.0),
            "Z2_endurance": (15.0, 25.0),
            "Z3_tempo": (25.0, 30.0),
            "Z4_threshold": (30.0, 35.0),
            "Z5_vo2max": (35.0, 42.0),
            "Z6_anaerobic": (42.0, float("inf")),
        }

        total = float(np.sum(distances_m))
        if total == 0:
            return {}

        result = {}
        for zone_name, (low, high) in zones.items():
            mask = (speeds >= low) & (speeds < high)
            zone_dist = float(np.sum(distances_m[mask]))
            result[zone_name] = {
                "distance_km": round(zone_dist / 1000, 2),
                "percentage": round(zone_dist / total * 100, 1) if total > 0 else 0.0,
            }
        return result
