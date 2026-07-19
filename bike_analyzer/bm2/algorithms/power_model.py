"""BikeMaster 2.0 - Power Model (stima potenza/velocità da FTP e profilo)."""

from __future__ import annotations

from typing import Optional

from ..models import AnalysisContext
from .base import Algorithm
from bike_analyzer.core.physics import RiderBikeParams, instantaneous_power, required_speed_for_power

__all__ = ["PowerModel"]


class PowerModel(Algorithm):
    """Stima potenza richiesta e velocita' sostenibile da FTP e profilo di pendenza.

    Formula: P = (crr·m·g + m·g·slope + ½·ρ·CdA·v²)·v / η  [stima da FTP];
             v_ftp = risolvi P=FTP per la velocita'
    """

    name = "PowerModel"
    formula = ("P = (crr·m·g + m·g·slope + ½·ρ·CdA·v²)·v / η  [stima da FTP]; "
               "v_ftp = risolvi P=FTP per la velocità")
    description = "Stima potenza richiesta e velocità sostenibile da FTP e profilo di pendenza."
    unit = "W"
    required_inputs = ["ftp", "massa_totale", "pendenza", "crr", "cda", "efficienza"]

    @staticmethod
    def _power_for_speed(v_ms: float, mass_kg: float, slope_pct: float,
                         crr: float, cda: float, eta: float, wind_ms: float = 0.0) -> float:
        """Calcola la potenza meccanica richiesta per una data velocita'."""
        return instantaneous_power(
            v_ms, slope_pct / 100.0,
            RiderBikeParams(rider_mass_kg=mass_kg, cda=cda, crr=crr, drivetrain_efficiency=eta),
            wind_ms=wind_ms,
        )

    @staticmethod
    def _speed_for_power(target_w: float, mass_kg: float, slope_pct: float,
                         crr: float, cda: float, eta: float, wind_ms: float = 0.0) -> float:
        """Risoluzione numerica (bisezione) di P = f(v) per la velocità sostenibile.

        Delegato al kernel unico ``core.physics.required_speed_for_power``.
        """
        if target_w <= 0:
            return 0.0
        return required_speed_for_power(
            target_w, slope_pct / 100.0,
            RiderBikeParams(rider_mass_kg=mass_kg, cda=cda, crr=crr, drivetrain_efficiency=eta),
            wind_ms=wind_ms,
        )

    def _compute(self, ctx: AnalysisContext, extra: Optional[dict]) -> tuple[float, float, float]:
        """Stima la potenza da sensori o da FTP/velocita' sostenibile."""
        m = ctx.activity.metrics(ctx.transformer)
        slope = m["avg_slope_percent"]
        mass = ctx.total_mass_kg
        ftp = ctx.athlete.ftp_w.value if ctx.athlete.ftp_w else 0.0
        wind = 0.0
        if ctx.world.wind_speed_ms is not None:
            wind = ctx.world.wind_speed_ms.value

        power_from_sensors = self._avg_power_from_sensors(ctx)
        if power_from_sensors > 0:
            confidence = self._confidence_for_source("power_meter", 0.9)
            return power_from_sensors, 5.0, confidence

        if ftp <= 0:
            est_power = self._power_for_speed(m["avg_speed_ms"], mass, slope,
                                              ctx.bike.crr, ctx.bike.cda,
                                              ctx.bike.drivetrain_efficiency, wind)
            confidence = 0.5
            if ctx.athlete.weight_kg.source != "estimate":
                confidence = 0.6
            return est_power, est_power * 0.25, confidence

        v_ftp = self._speed_for_power(ftp, mass, slope, ctx.bike.crr,
                                       ctx.bike.cda, ctx.bike.drivetrain_efficiency, wind)
        # The sustainable speed at FTP is the physically meaningful estimate: it is
        # sensitive to mass/slope/CdA/wind. Resolving v for P=FTP and then
        # recomputing P(v) would just return FTP again (degenerate what-if).
        sustainable_speed_ms = v_ftp
        # Estimate the power required at the *actual* average speed of the
        # activity, so the value reacts to mass/slope/CdA changes.
        ref_speed_ms = m["avg_speed_ms"] if m["avg_speed_ms"] > 0 else sustainable_speed_ms
        est_power = self._power_for_speed(ref_speed_ms, mass, slope, ctx.bike.crr,
                                           ctx.bike.cda, ctx.bike.drivetrain_efficiency, wind)
        ftp_source = ctx.athlete.ftp_w.source if ctx.athlete.ftp_w else "estimate"
        confidence = self._confidence_for_source(ftp_source, 0.75)
        return est_power, sustainable_speed_ms, confidence

    @staticmethod
    def _avg_power_from_sensors(ctx: AnalysisContext) -> float:
        """Media della potenza dai punti con sensore di potenza, 0 se assenti."""
        pts = [p for p in ctx.activity.points if p.power is not None]
        if not pts:
            return 0.0
        return sum(p.power for p in pts) / len(pts)

    def _extra_details(self, ctx: AnalysisContext, extra: Optional[dict]) -> dict:
        """Restituisce FTP, velocita' sostenibile, potenza stimata e media sensori."""
        m = ctx.activity.metrics(ctx.transformer)
        slope = m["avg_slope_percent"]
        mass = ctx.total_mass_kg
        ftp = ctx.athlete.ftp_w.value if ctx.athlete.ftp_w else 0.0
        wind = ctx.world.wind_speed_ms.value if ctx.world.wind_speed_ms else 0.0
        v_ftp = 0.0
        if ftp > 0:
            v_ftp = self._speed_for_power(ftp, mass, slope, ctx.bike.crr,
                                          ctx.bike.cda, ctx.bike.drivetrain_efficiency, wind)
        forces = self._cycling_forces(mass, slope, ctx.bike.crr, ctx.bike.cda,
                                      v_ftp or m["avg_speed_ms"], wind,
                                      ctx.bike.drivetrain_efficiency)
        return {
            "ftp_w": ftp,
            "sustainable_speed_ms": round(v_ftp, 3) if v_ftp > 0 else None,
            "estimated_power_w": round(forces["power_w"], 1),
            "avg_speed_ms": round(m["avg_speed_ms"], 3),
            "slope_percent": slope,
            "sensor_avg_power_w": round(self._avg_power_from_sensors(ctx), 1),
        }
