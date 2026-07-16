"""Load Manager — Training Stress Calculator service.

Spec (agent): service ``TrainingStressCalculator`` producing ``TrainingStress``.
Does NOT modify existing modules (training_stress.py, power_model.py, fatigue.py).
Supports both power-based and MET/HR-based estimation.
"""

from __future__ import annotations

from typing import Optional

from bike_analyzer.backend.models.models import Ride

from .calculators import calculate_tss, terrain_correction
from .config import DEFAULT_CONFIG
from .models import StressMethod, TrainingStress


class TrainingStressCalculator:
    """Compute TSS per ride from power (preferred) or HR/speed (fallback)."""

    def __init__(self, ftp_watts: float | None = None, config=DEFAULT_CONFIG) -> None:
        self.ftp_watts = ftp_watts
        self.config = config

    def from_ride(self, ride: Ride) -> TrainingStress:
        duration_h = ride.duration_hours
        if duration_h <= 0:
            return TrainingStress(
                ride_id=ride.id, date=ride.date[:10] if ride.date else "",
                tss=0.0, intensity_factor=0.0, method=StressMethod.MET, duration_hours=0.0,
            )

        tcorr = terrain_correction(ride.elevation_gain_m, ride.distance_km)

        # Power-based path (uses power_model helpers when GPS power is present).
        gps = ride.gps_points or []
        watts = [p.power for p in gps if p.power is not None]
        if self.ftp_watts and self.ftp_watts > 0 and watts:
            from bike_analyzer.backend.analytics.power_model import (
                intensity_factor,
                normalized_power,
                training_stress_score,
            )

            np = normalized_power(watts)
            if_val = intensity_factor(np, self.ftp_watts)
            tss = training_stress_score(np, if_val, duration_h)
            tss *= 1.0 + tcorr
            return TrainingStress(
                ride_id=ride.id, date=ride.date[:10] if ride.date else "",
                tss=round(min(tss, 500.0), 1), intensity_factor=if_val,
                normalized_power=np, avg_power=round(sum(watts) / len(watts), 1),
                method=StressMethod.POWER, duration_hours=round(duration_h, 3),
                ftp_watts=self.ftp_watts, elevation_gain_m=ride.elevation_gain_m,
                terrain_correction=tcorr,
            )

        # HR/speed-based estimation.
        if_val = self._estimate_if_from_hr_speed(ride)
        method = StressMethod.HR if (ride.heart_rate_avg and self._max_hr(ride)) else StressMethod.MET
        res = calculate_tss(duration_h, if_val, self.ftp_watts, None, None, tcorr)
        return TrainingStress(
            ride_id=ride.id, date=ride.date[:10] if ride.date else "",
            tss=res["tss"], intensity_factor=res["intensity_factor"],
            method=method, duration_hours=round(duration_h, 3),
            ftp_watts=self.ftp_watts, elevation_gain_m=ride.elevation_gain_m,
            terrain_correction=tcorr,
        )

    def _estimate_if_from_hr_speed(self, ride: Ride) -> float:
        if_val = 0.5
        if ride.avg_speed_kmh and ride.avg_speed_kmh > 0:
            if_val = min(ride.avg_speed_kmh / 40.0, 1.0)
        hr_avg = ride.heart_rate_avg
        max_hr = self._max_hr(ride)
        if hr_avg and max_hr:
            hr_pct = hr_avg / max_hr
            if_val = max(if_val, min(hr_pct / 0.9, 1.2))
        return round(if_val, 3)

    @staticmethod
    def _max_hr(ride: Ride) -> Optional[float]:
        # Athlete age is not on Ride; use a conservative default if HR present.
        if ride.heart_rate_avg and ride.heart_rate_avg > 0:
            return 190.0
        return None


__all__ = ["TrainingStressCalculator"]
