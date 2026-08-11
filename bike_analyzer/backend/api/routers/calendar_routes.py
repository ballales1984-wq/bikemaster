"""Calendar API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ...security import get_current_user
from ..routes import _ensure_athlete_access
from ..schemas import CalendarEventCreate, CalendarEventUpdate
from ...analytics.repositories.calendar_repository import CalendarRepository

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.post("/events")
async def create_calendar_event(
    event_data: CalendarEventCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a calendar event for an athlete."""
    from ...utils.dates import date_only

    event_data_dict = event_data.model_dump()
    event_data_dict["date"] = date_only(event_data_dict.get("date"))
    event_data_dict["tenant_id"] = current_user.get("tenant_id", current_user["id"])
    _ensure_athlete_access(event_data_dict["athlete_id"], current_user)
    event_id = CalendarRepository.save_calendar_event(event_data_dict)
    event = CalendarRepository.get_calendar_event(int(event_id))
    return event


@router.get("/events")
async def list_calendar_events(
    athlete_id: int = Query(...),
    year: int = Query(...),
    month: int = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """List calendar events for an athlete in a given month."""
    _ensure_athlete_access(athlete_id, current_user)
    events = CalendarRepository.get_events_by_month(athlete_id, year, month, tenant_id)
    return {"events": events}


@router.get("/events/range")
async def list_events_by_range(
    athlete_id: int = Query(...),
    start: str = Query(...),
    end: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """List calendar events for an athlete within a date range."""
    _ensure_athlete_access(athlete_id, current_user)
    events = CalendarRepository.get_events_by_date_range(athlete_id, start, end, tenant_id)
    return {"events": events}


@router.get("/events/{event_id}")
async def get_calendar_event_endpoint(
    event_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Get a single calendar event by ID."""
    event = CalendarRepository.get_calendar_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    _ensure_athlete_access(event["athlete_id"], current_user)
    return event


@router.put("/events/{event_id}")
async def update_calendar_event_endpoint(
    event_id: int,
    event_data: CalendarEventUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update a calendar event. Only the owner can modify."""
    update_dict = event_data.model_dump(exclude_none=True)
    if update_dict.get("date"):
        update_dict["date"] = date_only(update_dict.get("date"))
    event = CalendarRepository.get_calendar_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    _ensure_athlete_access(event["athlete_id"], current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    ok = CalendarRepository.update_calendar_event(event_id, update_dict, tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found")

    return CalendarRepository.get_calendar_event(event_id)


@router.delete("/events/{event_id}")
async def delete_calendar_event_endpoint(
    event_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Delete a calendar event. Only the owner can delete."""
    event = CalendarRepository.get_calendar_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    _ensure_athlete_access(event["athlete_id"], current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    ok = CalendarRepository.delete_calendar_event(event_id, tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"deleted": True}


@router.post("/events/{event_id}/complete")
async def toggle_event_complete(
    event_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Toggle the completed flag on a calendar event."""

    event = CalendarRepository.get_calendar_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    _ensure_athlete_access(event["athlete_id"], current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    CalendarRepository.update_calendar_event(event_id, {"completed": not event["completed"]}, tenant_id)
    return CalendarRepository.get_calendar_event(event_id)
