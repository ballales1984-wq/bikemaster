"""BikeMaster 2.0 - Power Model (estimates power/speed from FTP and profile).

The forward model is P = (crr·m·g + m·g·slope + ½·ρ·CdA·(v+wind)²)·v / η.
The inverse model solves v for a given P using bisection on the forward model.
"""

from __future__ import annotations

from typing import Optional

from ..models import AnalysisContext
from .base import Algorithm
from bike_analyzer.core.physics import RiderBikeParams, instantaneous_power, required_speed_for_power

__all__ = ["PowerModel"]


class PowerModel(Algorithm):
    """Stima potenza richiesta e velocita' sostenibile da FTP e profilo di pendenza.

    Formula diretta (forward):
        P = (crr·m·g + m·g·slope + ½·ρ·CdA·v²)·v / η

    Formula inversa (inverse):
        v_ftp = risolvi P=FTP per la velocita' tramite bisection

    Il valore restituito (power) e' la potenza meccanica calcolata tramite
    il modello diretto alla velocita' media dell'attivita', rendendo il
    risultato sensibile a variazioni di massa, pendenza, CdA e vento.
    Quando FTP e' disponibile e la velocita' media e' nota, la potenza
    stimata riflette le resistenze aerodinamiche e di pendenza alla
    velocita' reale, non l'identita' P(v_ftp)=FTP.
    """

    name = "PowerModel"
    formula = ("P = (crr·m·g + m·g·slope + ½·ρ·CdA·v²)·v / η  [forward model]; "
               "v_ftp = solve P=FTP for speed [inverse model]")
    description = "Estimates required power and sustainable speed from FTP and slope profile."
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
        """Numerical resolution (bisection) of P = f(v) for sustainable speed.

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
        """Stima la potenza da sensori o da FTP/velocita' sostenibile.

        Quando FTP e' disponibile e la velocita' media dell'attivita' e'
        maggiore di zero, si usa il modello diretto P=f(v) alla velocita'
        reale dell'attivita'.  Questo rende il risultato sensibile a
        variazioni di massa, pendenza, CdA e vento — fondamentale per
        la simulazione what-if.

        Quando FTP e' disponibile ma la velocita' media e' zero/inesistente,
        si restituisce FTP come potenza (il ciclista e' al limite) e
        v_ftp come velocita' sostenibile (sensibile ai parametri).
        """
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

        avg_speed_ms = m["avg_speed_ms"]

        if ftp <= 0:
            est_power = self._power_for_speed(avg_speed_ms, mass, slope,
                                              ctx.bike.crr, ctx.bike.cda,
                                              ctx.bike.drivetrain_efficiency, wind)
            confidence = 0.5
            if ctx.athlete.weight_kg.source != "estimate":
                confidence = 0.6
            return est_power, est_power * 0.25, confidence

        # FTP is available: compute the sustainable speed at FTP power.
        # This is the inverse model — sensitive to mass/slope/CdA/wind.
        v_ftp = self._speed_for_power(ftp, mass, slope, ctx.bike.crr,
                                      ctx.bike.cda, ctx.bike.drivetrain_efficiency, wind)

        if avg_speed_ms > 0:
            # Forward model: power at the activity's actual speed.
            # This is sensitive to what-if parameter changes (mass, slope, CdA, wind).
            est_power = self._power_for_speed(avg_speed_ms, mass, slope,
                                              ctx.bike.crr, ctx.bike.cda,
                                              ctx.bike.drivetrain_efficiency, wind)
        else:
            # No speed data available: the cyclist is producing FTP power.
            # Return FTP as the power estimate; v_ftp as the sustainable speed.
            # The what-if comparison will show speed differences (not power),
            # which is the physically meaningful what-if output for FTP-paced riding.
            est_power = ftp

        ftp_source = ctx.athlete.ftp_w.source if ctx.athlete.ftp_w else "estimate"
        confidence = self._confidence_for_source(ftp_source, 0.75)
        return est_power, v_ftp, confidence

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
        avg_speed = m["avg_speed_ms"]

        v_ftp = 0.0
        if ftp > 0:
            v_ftp = self._speed_for_power(ftp, mass, slope, ctx.bike.crr,
                                          ctx.bike.cda, ctx.bike.drivetrain_efficiency, wind)

        # Use activity speed when available (forward model, sensitive to what-if);
        # fall back to v_ftp only when no speed data exists.
        ref_speed = avg_speed if avg_speed > 0 else v_ftp
        forces = self._cycling_forces(mass, slope, ctx.bike.crr, ctx.bike.cda,
                                      ref_speed, wind,
                                      ctx.bike.drivetrain_efficiency)
        return {
            "ftp_w": ftp,
            "sustainable_speed_ms": round(v_ftp, 3) if v_ftp > 0 else None,
            "estimated_power_w": round(forces["power_w"], 1),
            "avg_speed_ms": round(avg_speed, 3),
            "slope_percent": slope,
            "sensor_avg_power_w": round(self._avg_power_from_sensors(ctx), 1),
        }

