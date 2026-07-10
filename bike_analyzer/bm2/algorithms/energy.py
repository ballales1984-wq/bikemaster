"""BikeMaster 2.0 - Energy Model (consumo energetico)."""

from __future__ import annotations

from typing import Optional

from ..models import AnalysisContext
from .base import Algorithm

__all__ = ["EnergyModel"]

G = 9.81            # m/s^2
RHO = 1.225         # densità aria kg/m^3
GROSS_EFFICIENCY = 0.24   # efficienza metabolica ciclismo ~24%
J_PER_KCAL = 4184.0


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

        f_roll = ctx.bike.crr * mass * G
        f_grav = mass * G * slope
        f_air = 0.5 * RHO * ctx.bike.cda * (v_air ** 2)
        p_mech = (f_roll + f_grav + f_air) * v  # W
        p_mech /= max(ctx.bike.drivetrain_efficiency, 1e-3)

        e_mech_j = p_mech * dur_s
        e_metab_j = e_mech_j / GROSS_EFFICIENCY
        kcal = e_metab_j / J_PER_KCAL

        # incertezza: dominata da cdA, efficienza e slope
        precision = kcal * 0.15
        has_slope = m["gain_m"] > 0
        confidence = 0.85 if has_slope else 0.7
        return kcal, precision, confidence

    def _extra_details(self, ctx: AnalysisContext, extra: Optional[dict]) -> dict:
        m = ctx.activity.metrics(ctx.transformer)
        dist_m = m["distance_m"]
        dur_s = m["duration_s"]
        v = dist_m / dur_s if dur_s > 0 else 0.0
        mass = ctx.total_mass_kg
        slope = m["avg_slope_percent"] / 100.0
        f_roll = ctx.bike.crr * mass * G
        f_grav = mass * G * slope
        wind = ctx.world.wind_speed_ms.value if ctx.world.wind_speed_ms else 0.0
        f_air = 0.5 * RHO * ctx.bike.cda * ((v + wind) ** 2)
        p_mech = (f_roll + f_grav + f_air) * v / max(ctx.bike.drivetrain_efficiency, 1e-3)
        return {
            "distance_m": dist_m,
            "duration_s": dur_s,
            "avg_speed_ms": v,
            "mechanical_power_w": p_mech,
            "metabolic_power_w": p_mech / GROSS_EFFICIENCY,
            "total_mass_kg": mass,
        }
