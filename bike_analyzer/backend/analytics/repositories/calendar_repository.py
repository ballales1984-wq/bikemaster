"""Calendar repository - data access abstraction for calendar events."""

from __future__ import annotations


class CalendarRepository:
    @staticmethod
    def get_calendar_event(event_id: int):
        from ...db.database import get_calendar_event

        return get_calendar_event(event_id)

    @staticmethod
    def save_calendar_event(event_data: dict):
        from ...db.database import save_calendar_event

        return save_calendar_event(event_data)

    @staticmethod
    def get_events_by_month(athlete_id: int, year: int, month: int, tenant_id: int = 0):
        from ...db.database import get_events_by_month

        return get_events_by_month(athlete_id, year, month, tenant_id)

    @staticmethod
    def get_events_by_date_range(athlete_id: int, start: str, end: str, tenant_id: int = 0):
        from ...db.database import get_events_by_date_range

        return get_events_by_date_range(athlete_id, start, end, tenant_id)

    @staticmethod
    def update_calendar_event(event_id: int, update_dict: dict, tenant_id: int = 0):
        from ...db.database import update_calendar_event

        return update_calendar_event(event_id, update_dict, tenant_id)

    @staticmethod
    def delete_calendar_event(event_id: int, tenant_id: int = 0):
        from ...db.database import delete_calendar_event

        return delete_calendar_event(event_id, tenant_id)
