"""HR repository - data access abstraction for heart rate and sensor data."""

from __future__ import annotations


class HRRepository:
    @staticmethod
    def get_hr_settings(athlete_id: int, tenant_id: int = 0):
        from ...db.database import get_hr_settings

        return get_hr_settings(athlete_id, tenant_id)

    @staticmethod
    def upsert_hr_settings(athlete_id: int, tenant_id: int = 0, **kwargs):
        from ...db.database import upsert_hr_settings

        return upsert_hr_settings(athlete_id, tenant_id=tenant_id, **kwargs)

    @staticmethod
    def log_hr_samples(athlete_id: int, samples: list, tenant_id: int = 0):
        from ...db.database import log_hr_samples

        return log_hr_samples(athlete_id, samples, tenant_id)

    @staticmethod
    def get_hr_24h_samples(athlete_id: int, hours: int = 24, tenant_id: int = 0):
        from ...db.database import get_hr_24h_samples

        return get_hr_24h_samples(athlete_id, hours=hours, tenant_id=tenant_id)

    @staticmethod
    def get_hr_daily_summary(athlete_id: int, days: int = 30, tenant_id: int = 0):
        from ...db.database import get_hr_daily_summary

        return get_hr_daily_summary(athlete_id, days=days, tenant_id=tenant_id)

    @staticmethod
    def delete_hr_samples(athlete_id: int, older_than: str | None = None, tenant_id: int = 0):
        from ...db.database import delete_hr_samples

        return delete_hr_samples(athlete_id, older_than=older_than, tenant_id=tenant_id)

    @staticmethod
    def log_sensor_data(athlete_id: int, data: dict, tenant_id: int = 0):
        from ...db.database import log_sensor_data

        return log_sensor_data(athlete_id, data, tenant_id)
