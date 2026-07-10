"""BikeMaster 2.0 - Energy Model (consumo energetico)."""

from __future__ import annotations

from typing import Optional

from ..models import AnalysisContext
from .base import Algorithm

__all__ = ["EnergyModel"]


class EnergyModel(Algorithm):
    name = "EnergyModel"
    formula = ("P = (crr·m·g + m·g·sin(atan(slope)) + ½·ρ·CdA·v²)·v ; "
               "kcal = P·t / (η·4184)")
    description = "Stima il consumo energetico (kcal) da lavoro meccanico e efficienza metabolica."
    unit = "kcal"
    required_inputs = ["massa_totale", "velocità", "pendenza", "durata", "crr", "cda"]

    def _compute(self, ctx: AnalysisContext, extra: Optional[dict]) -> tuple[float, float, float]:
        m = ctx.activity.metrics(ctx.transformer)
        dist_m = m["distance_m"]
        dur_s = m["duration_s"]
        if dur_s <= 0 or dist_m <= 0:
            return 0.0, 0.0, 0.2

        v = dist_m / dur_s  # m/s
        mass = ctx.total_mass_kg
        slope = m["avg_slope_percent"] / 100.0  # frazione
        wind = 0.0
        if ctx.world.wind_speed_ms is not None:
            wind = ctx.world.wind_speed_ms.value  # vento contrario positivo
        v_air = max(v + wind, 0.0)

        forces = self._cycling_forces(mass, m["avg_slope_percent"], ctx.bike.crr,
                                     ctx.bike.cda, v, wind, ctx.bike.drivetrain_efficiency)
        p_mech = forces["power_w"]

        e_mech_j = p_mech * dur_s
        e_metab_j = e_mech_j / 0.24
        kcal = e_metab_j / 4184.0

        precision = max(kcal * 0.15, 1.0)
        has_slope = m["gain_m"] > 0
        confidence = 0.85 if has_slope else 0.7
        if ctx.athlete.weight_kg.source == "estimate":
            confidence *= 0.85
        return kcal, precision, confidence

    def _extra_details(self, ctx: AnalysisContext, extra: Optional[dict]) -> dict:
        m = ctx.activity.metrics(ctx.transformer)
        dist_m = m["distance_m"]
        dur_s = m["duration_s"]
        v = dist_m / dur_s if dur_s > 0 else 0.0
        mass = ctx.total_mass_kg
        wind = ctx.world.wind_speed_ms.value if ctx.world.wind_speed_ms else 0.0
        forces = self._cycling_forces(mass, m["avg_slope_percent"], ctx.bike.crr,
                                     ctx.bike.cda, v, wind, ctx.bike.drivetrain_efficiency)
        return {
            "distance_m": dist_m,
            "duration_s": dur_s,
            "avg_speed_ms": v,
            "mechanical_power_w": forces["power_w"],
            "metabolic_power_w": forces["power_w"] / 0.24,
            "total_mass_kg": mass,
        }
