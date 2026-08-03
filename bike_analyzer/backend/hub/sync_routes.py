"""Hub sync endpoints — minimal cloud sync support.

These endpoints are called by the SyncClient on the local backend to
push/pull data to/from the hub's PostgreSQL store. They implement the
basic sync protocol: check, push, pull.

Full conflict resolution and entity state management are handled by the
local sync service; the hub only stores received data.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select as sa_select
from sqlalchemy.exc import SQLAlchemyError

from bike_analyzer.backend.db.async_db import get_session_factory
from bike_analyzer.backend.db.models import (
    AthleteModel,
    RideModel,
)
from bike_analyzer.backend.security import get_current_user

logger = logging.getLogger(__name__)

hub_sync_router = APIRouter(tags=["sync"])


@hub_sync_router.get("/sync/check")
async def hub_sync_check(
    since: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Check for changes on the hub since the given timestamp."""
    from sqlalchemy import func as sa_func

    tenant_id = current_user.get("tenant_id", current_user["id"])
    session_factory = get_session_factory()
    async with session_factory() as session:
        since_dt = datetime.fromisoformat(since) if since else None
        stmt = sa_select(sa_func.max(RideModel.updated_at)).where(RideModel.tenant_id == tenant_id)
        if since_dt:
            stmt = stmt.where(RideModel.updated_at >= since_dt)
        result = await session.execute(stmt)
        last_ts = result.scalar_one_or_none()

    return {
        "last_sync_ts": (last_ts.isoformat() if last_ts else datetime.now(UTC).isoformat()),
        "server_changes_count": 0,
        "server_changes": [],
        "server_version": "hub-0.1",
    }


@hub_sync_router.post("/sync/push")
async def hub_sync_push(
    deltas: list[dict[str, Any]],
    current_user: dict = Depends(get_current_user),
):
    """Receive local deltas and merge them into the hub PostgreSQL store."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    session_factory = get_session_factory()
    accepted = 0
    errors = []

    for delta in deltas:
        try:
            entity_type = delta.get("entity_type")
            entity_data = delta.get("data", {})
            entity_id = delta.get("entity_id")

            if entity_type == "ride":
                async with session_factory() as session:
                    stmt = sa_select(RideModel).where(RideModel.id == entity_id, RideModel.tenant_id == tenant_id)
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()
                    if existing:
                        from sqlalchemy import update as sa_update
                        stmt = sa_update(RideModel).where(RideModel.id == entity_id).values(**entity_data)
                    else:
                        from sqlalchemy import insert as sa_insert
                        stmt = sa_insert(RideModel).values(**entity_data)
                    await session.execute(stmt)
                    await session.commit()
                accepted += 1

            elif entity_type == "athlete":
                from sqlalchemy import insert as sa_insert
                from sqlalchemy import update as sa_update
                stmt = sa_select(AthleteModel).where(AthleteModel.id == entity_id, AthleteModel.tenant_id == tenant_id)
                async with session_factory() as session:
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()
                    if existing:
                        stmt = sa_update(AthleteModel).where(AthleteModel.id == entity_id).values(**entity_data)
                    else:
                        stmt = sa_insert(AthleteModel).values(**entity_data)
                    await session.execute(stmt)
                    await session.commit()
                accepted += 1

            else:
                errors.append(f"Unsupported entity_type: {entity_type}")

        except SQLAlchemyError as exc:
            errors.append(f"DB error for {entity_type}:{entity_id}: {exc}")
        except Exception as exc:
            errors.append(f"Error for {entity_type}:{entity_id}: {exc}")

    return {
        "accepted": accepted,
        "conflicts": [],
        "errors": errors,
    }


@hub_sync_router.get("/sync/pull")
async def hub_sync_pull(
    since: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Pull changes from the hub since the given timestamp."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    session_factory = get_session_factory()
    changes = []

    async with session_factory() as session:
        since_dt = datetime.fromisoformat(since) if since else None
        stmt = sa_select(RideModel).where(RideModel.tenant_id == tenant_id)
        if since_dt:
            stmt = stmt.where(RideModel.updated_at >= since_dt)
        result = await session.execute(stmt)
        rides = result.scalars().all()
        for ride in rides:
            changes.append({
                "entity_type": "ride",
                "entity_id": ride.id,
                "data": {
                    "id": ride.id,
                    "athlete_id": ride.athlete_id,
                    "date": ride.date,
                    "distance_km": ride.distance_km,
                    "duration_minutes": ride.duration_minutes,
                    "avg_speed_kmh": ride.avg_speed_kmh,
                    "tenant_id": ride.tenant_id,
                },
                "modified_at": ride.updated_at.isoformat() if ride.updated_at else datetime.now(UTC).isoformat(),
            })

    return {"changes": changes}
