"""BikeMaster 2.0 - Power Model (stima potenza/velocità da FTP e profilo)."""

from __future__ import annotations

from typing import Optional

from ..models import AnalysisContext
from .base import Algorithm

__all__ = ["PowerModel"]

G = 9.81
RHO = 1.225


class PowerModel(Algorithm):
    name = "PowerModel"
    formula = ("P = (crr·m·g + m·g·sin(atan(slope)) + ½·ρ·CdA·v²)·v / η  [stima da FTP]; "
               "v_ftp = risolvi P=FTP per la velocità")
    description = "Stima potenza richiesta e velocità sostenibile da FTP e profilo di pendenza."
    unit = "W"
    required_inputs = ["ftp", "massa_totale", "pendenza", "crr", "cda", "efficienza"]

    @staticmethod
    def _power_for_speed(v_ms: float, mass_kg: float, slope_pct: float,
                         crr: float, cda: float, eta: float, wind_ms: float = 0.0) -> float:
        slope = slope_pct / 100.0
        v_air = max(v_ms + wind_ms, 0.0)
        f_roll = crr * mass_kg * G
        f_grav = mass_kg * G * slope
        f_air = 0.5 * RHO * cda * (v_air ** 2)
        return (f_roll + f_grav + f_air) * v_ms / max(eta, 1e-3)

    @staticmethod
    def _speed_for_power(ftp_w: float, mass_kg: float, slope_pct: float,
                         crr: float, cda: float, eta: float, wind_ms: float = 0.0) -> float:
        if ftp_w <= 0:
            return 0.0
        slope = slope_pct / 100.0
        f_grav = mass_kg * G * slope
        f_roll = crr * mass_kg * G
        a = 0.5 * RHO * cda / max(eta, 1e-3)
        b = f_roll + f_grav + 0.5 * RHO * cda * (wind_ms ** 2) / max(eta, 1e-3)
        c = -ftp_w
        disc = b * b - 4 * a * c
        if disc < 0:
            disc = 0.0
        return (-b + disc ** 0.5) / (2 * a)

    def _compute(self, ctx: AnalysisContext, extra: Optional[dict]) -> tuple[float, float, float]:
        m = ctx.activity.metrics(ctx.transformer)
        slope = m["avg_slope_percent"]
        mass = ctx.total_mass_kg
        ftp = ctx.athlete.ftp_w.value if ctx.athlete.ftp_w else 0.0
        wind = 0.0
        if ctx.world.wind_speed_ms is not None:
            wind = ctx.world.wind_speed_ms.value

        power_from_sensors = self._avg_power_from_sensors(ctx)
        if power_from_sensors > 0:
            precision = 5.0
            confidence = 0.9
            return power_from_sensors, precision, confidence

        if ftp <= 0:
            est_power = self._power_for_speed(m["avg_speed_ms"], mass, slope,
                                              ctx.bike.crr, ctx.bike.cda,
                                              ctx.bike.drivetrain_efficiency, wind)
            precision = est_power * 0.25
            confidence = 0.5
            return est_power, precision, confidence

        v_ftp = self._speed_for_power(ftp, mass, slope, ctx.bike.crr,
                                      ctx.bike.cda, ctx.bike.drivetrain_efficiency, wind)
        est_power = self._power_for_speed(v_ftp, mass, slope, ctx.bike.crr,
                                          ctx.bike.cda, ctx.bike.drivetrain_efficiency, wind)
        precision = est_power * 0.18
        confidence = 0.75 if ftp > 0 else 0.4
        return est_power, precision, confidence

    @staticmethod
    def _avg_power_from_sensors(ctx: AnalysisContext) -> float:
        pts = [p for p in ctx.activity.points if p.power is not None]
        if not pts:
            return 0.0
        return sum(p.power for p in pts) / len(pts)

    def _extra_details(self, ctx: AnalysisContext, extra: Optional[dict]) -> dict:
        m = ctx.activity.metrics(ctx.transformer)
        slope = m["avg_slope_percent"]
        mass = ctx.total_mass_kg
        ftp = ctx.athlete.ftp_w.value if ctx.athlete.ftp_w else 0.0
        wind = ctx.world.wind_speed_ms.value if ctx.world.wind_speed_ms else 0.0
        v_ftp = 0.0
        if ftp > 0:
            v_ftp = self._speed_for_power(ftp, mass, slope, ctx.bike.crr,
                                          ctx.bike.cda, ctx.bike.drivetrain_efficiency, wind)
        est_power = self._power_for_speed(v_ftp or m["avg_speed_ms"], mass, slope,
                                          ctx.bike.crr, ctx.bike.cda,
                                          ctx.bike.drivetrain_efficiency, wind)
        return {
            "ftp_w": ftp,
            "sustainable_speed_ms": round(v_ftp, 3) if v_ftp > 0 else None,
            "estimated_power_w": round(est_power, 1),
            "avg_speed_ms": round(m["avg_speed_ms"], 3),
            "slope_percent": slope,
            "sensor_avg_power_w": round(self._avg_power_from_sensors(ctx), 1),
        }
