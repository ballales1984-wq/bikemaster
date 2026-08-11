"""Metabolism repository - data access abstraction for metabolic data."""

from __future__ import annotations

from ...db.database import (
    get_athlete,
    get_food_logs_by_athlete_date,
    get_metabolic_adaptive_weights,
    get_metabolic_profile,
    get_metabolic_reference_value,
    get_rides_by_athlete,
    save_metabolic_adaptive_weights,
    save_metabolic_daily_summary,
    save_metabolic_profile,
)


class MetabolismRepository:
    @staticmethod
    def get_athlete(athlete_id: int, tenant_id: int = 0):
        return get_athlete(athlete_id, tenant_id)

    @staticmethod
    def get_rides_by_athlete(athlete_id: int, tenant_id: int = 0):
        return get_rides_by_athlete(athlete_id, tenant_id)

    @staticmethod
    def get_metabolic_profile(athlete_id: int, tenant_id: int = 0):
        return get_metabolic_profile(athlete_id, tenant_id)

    @staticmethod
    def get_metabolic_adaptive_weights(athlete_id: int, tenant_id: int = 0):
        return get_metabolic_adaptive_weights(athlete_id, tenant_id)

    @staticmethod
    def get_metabolic_reference_value(sex, age, weight, activity_level, tenant_id=0):
        return get_metabolic_reference_value(sex, age, weight, activity_level, tenant_id)

    @staticmethod
    def get_food_logs_by_athlete_date(athlete_id: int, date: str, tenant_id: int = 0):
        return get_food_logs_by_athlete_date(athlete_id, date, tenant_id=tenant_id)

    @staticmethod
    def save_metabolic_profile(profile: dict, athlete_id: int, tenant_id: int = 0):
        return save_metabolic_profile(profile, athlete_id, tenant_id)

    @staticmethod
    def save_metabolic_adaptive_weights(weights: dict, athlete_id: int, tenant_id: int = 0):
        return save_metabolic_adaptive_weights(weights, athlete_id, tenant_id)

    @staticmethod
    def save_metabolic_daily_summary(summary: dict, tenant_id: int = 0):
        return save_metabolic_daily_summary(summary, tenant_id)
