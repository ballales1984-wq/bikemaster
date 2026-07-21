"""BikeMaster 2.0 - Metabolism Model (profilo metabolico e spesa energetica).

Integrates with the existing core calculators (core/calculators/metabolism.py)
to provide BMR, TDEE, NEAT, EAT, climb bonus and daily energy balance within
the BM2 Model Engine pipeline. Leverages athlete body composition, ride tracking
and GPS data to produce realistic energy expenditure estimates.
"""

from __future__ import annotations

from typing import Optional

from ..models import AnalysisContext, MetabolicDailySummary, MetabolicProfile
from .base import Algorithm, ModelResult

__all__ = ["MetabolismModel"]


class MetabolismModel(Algorithm):
    """Stima il profilo metabolico (BMR/TDEE/NEAT/EAT) e la spesa energetica giornaliera.

    Formula: BMR = Mifflin-St Jeor o Cunningham;
             TDEE = BMR * activity_multiplier + NEAT + EAT + climb_bonus;
             NEAT = GPS-derived (low-speed segments) + baseline per activity level;
             EAT = sum(ride calories from physics/MET estimators);
             TEF = 0.10 * intake (thermic effect of food).
    """

    name = "MetabolismModel"
    formula = ("BMR = Mifflin/Cunningham; "
               "TDEE = BMR*mult + NEAT + EAT + climb_bonus; "
               "TEF = 0.10*intake")
    description = "Stima BMR, TDEE, NEAT, EAT e bilancio energetico giornaliero."
    unit = "kcal/day"
    required_inputs = ["peso", "bmr_formula", "activity_level", "sex", "age"]

    def _compute(self, ctx: AnalysisContext, extra: Optional[dict]) -> tuple[float, float, float]:
        """Calcola TDEE giornaliero in kcal/day."""
        profile = self._build_profile(ctx, extra)
        tdee = profile.tdee_kcal
        precision = max(tdee * 0.12, 15.0) if tdee > 0 else 0.0
        confidence = 0.75 if profile.bmr_kcal > 0 else 0.3
        if ctx.athlete.fat_percentage is not None:
            confidence = min(confidence + 0.05, 0.9)
        return tdee, precision, confidence

    def _build_profile(self, ctx: AnalysisContext, extra: Optional[dict]) -> MetabolicProfile:
        """Builds a full MetabolicProfile from the AnalysisContext."""
        from bike_analyzer.core.calculators.metabolism import (
            MetabolicProfileInput,
            calculate_bmr,
            calculate_daily_expenditure,
            reference_for_athlete,
        )

        weight_kg = ctx.athlete.weight_kg.value
        height_m_val = ctx.athlete.height_m.value if ctx.athlete.height_m else None
        if height_m_val is not None and height_m_val > 3.0:
            height_cm = height_m_val
        elif height_m_val is not None:
            height_cm = height_m_val * 100.0
        else:
            height_cm = None
        age = ctx.athlete.age
        fat = ctx.athlete.fat_percentage
        sex = ctx.athlete.sex
        bmr_formula = ctx.athlete.bmr_formula
        activity_level = ctx.athlete.activity_level

        profile_input = MetabolicProfileInput(
            weight_kg=weight_kg,
            height_cm=height_cm,
            age=age,
            fat_percentage=fat,
            sex=sex,
            bmr_formula=bmr_formula,
            activity_level=activity_level,
        )

        bmr = calculate_bmr(profile_input)
        ref = reference_for_athlete(age, sex, weight_kg, activity_level, height_cm)

        rides = []
        if ctx.activity.points:
            from ..models import Activity as BM2Activity
            ride_data = {
                "elevation_gain_m": ctx.activity.summary.get("elevation_gain_m"),
                "gps_points": [
                    {
                        "timestamp": p.timestamp.isoformat() if p.timestamp else None,
                        "speed": p.speed,
                        "altitude": p.altitude,
                    }
                    for p in ctx.activity.points
                ],
                "calories": ctx.activity.summary.get("calories"),
            }
            rides.append(ride_data)

        expenditure = calculate_daily_expenditure(profile_input, rides, "")

        neat_w = 1.0
        climb_bonus_w = 1.0
        sensor_bmr_conf = 1.0
        sensor_tdee_conf = 1.0
        activity_multiplier_w = 1.0
        n_calibrations = 0

        if ctx.metabolic_profile:
            mp = ctx.metabolic_profile
            neat_w = mp.neat_w
            climb_bonus_w = mp.climb_bonus_w
            sensor_bmr_conf = mp.sensor_bmr_conf
            sensor_tdee_conf = mp.sensor_tdee_conf
            activity_multiplier_w = mp.activity_multiplier_w
            n_calibrations = mp.n_calibrations

        adj_ref_bmr = ref["bmr_kcal"] * activity_multiplier_w
        adj_ref_tdee = ref["tdee_kcal"] * activity_multiplier_w * neat_w

        if sensor_bmr_conf > 0 and bmr > 0:
            bmr_blended = sensor_bmr_conf * bmr + (1.0 - sensor_bmr_conf) * adj_ref_bmr
        else:
            bmr_blended = adj_ref_bmr

        eat_cal = expenditure["eat_kcal"]
        neat_cal = expenditure["neat_kcal"]
        climb_cal = expenditure["climb_bonus_kcal"] * climb_bonus_w

        tdee_raw = bmr_blended + neat_cal + eat_cal + climb_cal
        tdee_blended = max(tdee_raw, bmr_blended)

        from datetime import UTC, datetime
        now = datetime.now(UTC).isoformat()

        return MetabolicProfile(
            bmr_kcal=round(bmr_blended, 1),
            tdee_kcal=round(tdee_blended, 1),
            neat_kcal=round(neat_cal, 1),
            eat_kcal=round(eat_cal, 1),
            climb_bonus_kcal=round(climb_cal, 1),
            bmr_formula=bmr_formula,
            activity_level=activity_level,
            sex=sex,
            fat_percentage=fat,
            age=age,
            weight_kg=round(weight_kg, 1),
            height_cm=round(height_cm, 1) if height_cm else None,
            reference_bmr_kcal=round(ref["bmr_kcal"], 1),
            reference_tdee_kcal=round(ref["tdee_kcal"], 1),
            sensor_bmr_conf=round(sensor_bmr_conf, 4),
            sensor_tdee_conf=round(sensor_tdee_conf, 4),
            activity_multiplier_w=round(activity_multiplier_w, 4),
            neat_w=round(neat_w, 4),
            climb_bonus_w=round(climb_bonus_w, 4),
            n_calibrations=n_calibrations,
            created_at=now,
            updated_at=now,
        )

    def _extra_details(self, ctx: AnalysisContext, extra: Optional[dict]) -> dict:
        """Aggiunge scomporsi TDEE, flessibilita' metabolica e raccomandazioni."""
        profile = self._build_profile(ctx, extra)
        m = ctx.activity.metrics(ctx.transformer) if ctx.activity.points else {}
        dur_h = m.get("duration_s", 0) / 3600.0

        tef_kcal = 0.0
        intake_kcal = 0.0
        if extra and "intake_kcal" in extra:
            intake_kcal = float(extra["intake_kcal"])
            tef_kcal = intake_kcal * 0.10

        balance = intake_kcal - profile.tdee_kcal if intake_kcal > 0 else None

        metabolic_flexibility = 0.0
        if profile.reference_tdee_kcal > 0 and profile.tdee_kcal > 0:
            deviation = abs(profile.tdee_kcal - profile.reference_tdee_kcal) / profile.reference_tdee_kcal
            metabolic_flexibility = max(0.0, min(1.0, 1.0 - deviation))

        recommendation = self._recommendation(profile, balance, dur_h)

        return {
            "bmr_kcal": profile.bmr_kcal,
            "neat_kcal": profile.neat_kcal,
            "eat_kcal": profile.eat_kcal,
            "climb_bonus_kcal": profile.climb_bonus_kcal,
            "tef_kcal": round(tef_kcal, 1),
            "intake_kcal": round(intake_kcal, 1),
            "balance_kcal": round(balance, 1) if balance is not None else None,
            "reference_bmr_kcal": profile.reference_bmr_kcal,
            "reference_tdee_kcal": profile.reference_tdee_kcal,
            "sensor_bmr_conf": profile.sensor_bmr_conf,
            "sensor_tdee_conf": profile.sensor_tdee_conf,
            "activity_multiplier_w": profile.activity_multiplier_w,
            "neat_w": profile.neat_w,
            "climb_bonus_w": profile.climb_bonus_w,
            "n_calibrations": profile.n_calibrations,
            "metabolic_flexibility_score": round(metabolic_flexibility, 2),
            "duration_h": round(dur_h, 2),
            "recommendation": recommendation,
        }

    def run(self, ctx: AnalysisContext, extra: Optional[dict] = None) -> "ModelResult":
        """Overrides run to also return the MetabolicProfile in details."""
        missing = [inp for inp in self.required_inputs if not self._has_input(ctx, extra, inp)]
        if missing:
            return ModelResult(
                value=0.0,
                unit=self.unit,
                formula=self.formula,
                data_used=list(self.required_inputs),
                precision=0.0,
                confidence=0.0,
                source=self.name,
                details={"error": f"input mancanti: {missing}"},
            )
        value, precision, confidence = self._compute(ctx, extra)
        profile = self._build_profile(ctx, extra)
        details = self._extra_details(ctx, extra)
        details["metabolic_profile"] = profile.to_dict()
        return ModelResult(
            value=value,
            unit=self.unit,
            formula=self.formula,
            data_used=list(self.required_inputs),
            precision=precision,
            confidence=confidence,
            source=self.name,
            details=details,
        )

    @staticmethod
    def _recommendation(profile: MetabolicProfile, balance: float | None, dur_h: float) -> str:
        """Raccomandazione testuale basata sul bilancio energetico."""
        if balance is None:
            if profile.tdee_kcal > 0:
                return f"BMR {profile.bmr_kcal:.0f} kcal, TDEE {profile.tdee_kcal:.0f} kcal. Registra l'intake per il bilancio."
            return "Inserisci peso, eta' e sesso per il calcolo BMR."
        if balance > 500:
            return "Surplus energetico elevato: valuta se ridurre l'intake o aumentare l'attivita'."
        if balance > 200:
            return "Surplus moderato: adatto per periodi di guadagno muscolare."
        if balance >= -200:
            return "Bilancio neutro: mantenimento stabile."
        if balance >= -500:
            return "Deficit leggero: adatto per perdita di peso graduale."
        return "Deficit elevato: rischio di catabolismo, valuta aumento intake o riduzione attivita'."

    def build_daily_summary(self, ctx: AnalysisContext, date: str,
                            intake_kcal: float = 0.0, carbs_g: float = 0.0,
                            protein_g: float = 0.0, fat_g: float = 0.0,
                            fiber_g: float = 0.0, water_ml: float = 0.0) -> MetabolicDailySummary:
        """Build a MetabolicDailySummary from the context and nutrition data."""
        profile = self._build_profile(ctx, None)
        tef = intake_kcal * 0.10
        balance = round(intake_kcal - profile.tdee_kcal, 1)

        m = ctx.activity.metrics(ctx.transformer) if ctx.activity.points else {}
        elev = ctx.activity.summary.get("elevation_gain_m")

        return MetabolicDailySummary(
            date=date,
            bmr_kcal=profile.bmr_kcal,
            neat_kcal=profile.neat_kcal,
            eat_kcal=profile.eat_kcal,
            climb_bonus_kcal=profile.climb_bonus_kcal,
            tdee_kcal=profile.tdee_kcal,
            intake_kcal=round(intake_kcal, 1),
            balance_kcal=balance,
            carbs_g=round(carbs_g, 1),
            protein_g=round(protein_g, 1),
            fat_g=round(fat_g, 1),
            fiber_g=round(fiber_g, 1),
            water_ml=round(water_ml, 0),
            tef_kcal=round(tef, 1),
            steps_estimated=None,
            elevation_gain_estimated_m=round(elev, 1) if elev else None,
            rides_count=1 if ctx.activity.points else 0,
            gps_neat_kcal=profile.neat_kcal,
            metabolic_flexibility_score=0.0,
        )
