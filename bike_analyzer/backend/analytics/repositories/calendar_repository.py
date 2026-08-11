"""Calendar repository - data access abstraction for calendar events."""

from __future__ import annotations

from ...db.repositories.calendar_repository import (
    delete_calendar_event,
    get_calendar_event,
    get_events_by_date_range,
    get_events_by_month,
    save_calendar_event,
    update_calendar_event,
)


class CalendarRepository:
    @staticmethod
    def get_calendar_event(event_id: int):
        return get_calendar_event(event_id)

    @staticmethod
    def save_calendar_event(event_data: dict):
        return save_calendar_event(event_data)

    @staticmethod
    def get_events_by_month(athlete_id: int, year: int, month: int, tenant_id: int = 0):
        return get_events_by_month(athlete_id, year, month, tenant_id)

    @staticmethod
    def get_events_by_date_range(athlete_id: int, start: str, end: str, tenant_id: int = 0):
        return get_events_by_date_range(athlete_id, start, end, tenant_id)

    @staticmethod
    def update_calendar_event(event_id: int, update_dict: dict, tenant_id: int = 0):
        return update_calendar_event(event_id, update_dict, tenant_id)

    @staticmethod
    def delete_calendar_event(event_id: int, tenant_id: int = 0):
        return delete_calendar_event(event_id, tenant_id)
