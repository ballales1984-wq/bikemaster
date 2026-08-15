"""Calendar repository — persistence for calendar events.

This module re-exports the calendar functions from ``db/database.py`` so the
rest of the codebase has a single import path. The actual implementations live
in ``database.py`` and are dispatched to PostgreSQL via ``@pg_dispatch`` when
``DATABASE_URL`` is configured.
"""

from __future__ import annotations

from ...db.database import (
    delete_calendar_event,
    get_calendar_event,
    get_events_by_athlete,
    get_events_by_date_range,
    get_events_by_month,
    save_calendar_event,
    update_calendar_event,
)


class CalendarRepository:
    @staticmethod
    def save_calendar_event(event: dict, tenant_id: int = 0) -> int:
        return save_calendar_event(event, tenant_id=tenant_id)

    @staticmethod
    def get_calendar_event(event_id: int) -> dict | None:
        return get_calendar_event(event_id)

    @staticmethod
    def get_events_by_athlete(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
        return get_events_by_athlete(athlete_id, tenant_id=tenant_id)

    @staticmethod
    def get_events_by_date_range(
        athlete_id: int, start_date: str, end_date: str, tenant_id: int | None = None
    ) -> list[dict]:
        return get_events_by_date_range(athlete_id, start_date, end_date, tenant_id)

    @staticmethod
    def get_events_by_month(athlete_id: int, year: int, month: int, tenant_id: int | None = None) -> list[dict]:
        return get_events_by_month(athlete_id, year, month, tenant_id)

    @staticmethod
    def update_calendar_event(event_id: int, event_data: dict, tenant_id: int | None = None) -> bool:
        return update_calendar_event(event_id, event_data, tenant_id)

    @staticmethod
    def delete_calendar_event(event_id: int, tenant_id: int | None = None) -> bool:
        return delete_calendar_event(event_id, tenant_id)
