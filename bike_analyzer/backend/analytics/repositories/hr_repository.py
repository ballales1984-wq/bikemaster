"""HR repository - data access abstraction for heart rate and sensor data."""

from __future__ import annotations

from ...db.database import (
    delete_hr_samples,
    get_hr_24h_samples,
    get_hr_daily_summary,
    get_hr_settings,
    log_hr_samples,
    log_sensor_data,
    upsert_hr_settings,
)


class HRRepository:
    @staticmethod
    def get_hr_settings(athlete_id: int, tenant_id: int = 0):
        return get_hr_settings(athlete_id, tenant_id)

    @staticmethod
    def upsert_hr_settings(athlete_id: int, tenant_id: int = 0, **kwargs):
        return upsert_hr_settings(athlete_id, tenant_id=tenant_id, **kwargs)

    @staticmethod
    def log_hr_samples(athlete_id: int, samples: list, tenant_id: int = 0):
        return log_hr_samples(athlete_id, samples, tenant_id)

    @staticmethod
    def get_hr_24h_samples(athlete_id: int, tenant_id: int = 0):
        return get_hr_24h_samples(athlete_id, tenant_id)

    @staticmethod
    def get_hr_daily_summary(athlete_id: int, date: str, tenant_id: int = 0):
        return get_hr_daily_summary(athlete_id, date, tenant_id)

    @staticmethod
    def delete_hr_samples(athlete_id: int, date: str, tenant_id: int = 0):
        return delete_hr_samples(athlete_id, date, tenant_id)

    @staticmethod
    def log_sensor_data(athlete_id: int, data: dict, tenant_id: int = 0):
        return log_sensor_data(athlete_id, data, tenant_id)
