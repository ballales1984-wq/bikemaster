"""BikeMaster 2.0 - Movement Model (cinematica del movimento)."""

from __future__ import annotations

from typing import Optional

from ..models import AnalysisContext
from .base import Algorithm

__all__ = ["MovementModel"]


class MovementModel(Algorithm):
    name = "MovementModel"
    formula = "v_media = distanza / durata; v_max = max(samples); a = d(v)/d(t)"
    description = "Calcola velocità media/massima e accelerazione dalla traccia GPS."
    unit = "m/s"
    required_inputs = ["gps_points", "distanza", "durata"]

    def _compute(self, ctx: AnalysisContext, extra: Optional[dict]) -> tuple[float, float, float]:
        m = ctx.activity.metrics(ctx.transformer)
        dist_m = m["distance_m"]
        dur_s = m["duration_s"]
        if dur_s <= 0:
            return 0.0, 0.0, 0.3
        avg = dist_m / dur_s
        precision = 0.5 if dist_m > 0 else 1.0
        confidence = 0.95 if len(ctx.activity.points) >= 2 else 0.4
        return avg, precision, confidence

    def _extra_details(self, ctx: AnalysisContext, extra: Optional[dict]) -> dict:
        m = ctx.activity.metrics(ctx.transformer)
        speeds = [p for p in ctx.activity.points if p.speed is not None]
        max_speed = max((s.speed for s in speeds), default=m["avg_speed_ms"])
        accel = 0.0
        if len(speeds) >= 2:
            ds = [abs(speeds[i + 1].speed - speeds[i].speed) for i in range(len(speeds) - 1)]
            accel = max(ds, default=0.0)
        return {
            "distance_m": m["distance_m"],
            "duration_s": m["duration_s"],
            "gain_m": m["gain_m"],
            "max_speed_ms": max_speed,
            "max_accel_ms2": accel,
        }
