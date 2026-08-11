"""Itineraries API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..routes import _user_id, get_current_user
from ..schemas import ItineraryCreate, StageCreate

router = APIRouter(prefix="/itineraries", tags=["itineraries"])


@router.post("/")
async def create_itinerary(
    payload: ItineraryCreate, current_user: dict = Depends(get_current_user)
):
    """Create a new itinerary owned by the current athlete."""
    from ...db.database import save_itinerary

    athlete_id = _user_id(current_user)
    data = payload.model_dump()
    data["athlete_id"] = athlete_id
    data["tenant_id"] = current_user.get("tenant_id", athlete_id)
    try:
        itinerary_id = save_itinerary(data)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=422, detail=f"Invalid itinerary data: {exc}"
        ) from exc
    return {"id": itinerary_id, **data}


@router.get("/")
async def list_itineraries_endpoint(current_user: dict = Depends(get_current_user)):
    """List itineraries for the current athlete."""
    from ...db.database import list_itineraries

    athlete_id = _user_id(current_user)
    if current_user.get("is_admin"):
        return {"itineraries": list_itineraries()}
    return {"itineraries": list_itineraries(athlete_id)}


@router.get("/{itinerary_id}")
async def get_itinerary_endpoint(
    itinerary_id: int, current_user: dict = Depends(get_current_user)
):
    """Get a single itinerary with its stages."""
    from ...db.database import get_itinerary, list_stages

    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary["athlete_id"] != _user_id(current_user) and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    return {"itinerary": itinerary, "stages": list_stages(itinerary_id)}


@router.post("/{itinerary_id}/stages")
async def create_stage(
    itinerary_id: int,
    payload: StageCreate,
    current_user: dict = Depends(get_current_user),
):
    """Add a stage to an itinerary owned by the current athlete."""
    from ...db.database import get_itinerary, save_stage

    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary["athlete_id"] != _user_id(current_user) and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    data = payload.model_dump(exclude_unset=True)
    data["itinerary_id"] = itinerary_id
    stage_id = save_stage(data)
    return {"id": stage_id, **data}


@router.put("/{itinerary_id}")
async def update_itinerary_endpoint(
    itinerary_id: int,
    payload: ItineraryCreate,
    current_user: dict = Depends(get_current_user),
):
    """Update an itinerary owned by the current athlete."""
    from ...db.database import get_itinerary, update_itinerary

    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary["athlete_id"] != _user_id(current_user) and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    tenant_id = current_user.get("tenant_id", itinerary.get("athlete_id"))
    data = payload.model_dump(exclude_unset=True)
    ok = update_itinerary(itinerary_id, data, tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Itinerary not found or no changes")
    updated = get_itinerary(itinerary_id)
    return updated


@router.delete("/{itinerary_id}")
async def delete_itinerary_endpoint(
    itinerary_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Delete an itinerary owned by the current athlete."""
    from ...db.database import delete_itinerary, get_itinerary

    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary["athlete_id"] != _user_id(current_user) and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    tenant_id = current_user.get("tenant_id", itinerary.get("athlete_id"))
    ok = delete_itinerary(itinerary_id, tenant_id)
    return {"deleted": ok}


@router.get("/{itinerary_id}/stages/{stage_id}")
async def get_stage_endpoint(
    itinerary_id: int,
    stage_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Retrieve a single stage by id."""
    from ...db.database import get_itinerary, get_stage

    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary["athlete_id"] != _user_id(current_user) and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    stage = get_stage(stage_id)
    if not stage or stage.get("itinerary_id") != itinerary_id:
        raise HTTPException(status_code=404, detail="Stage not found")
    return stage


@router.put("/{itinerary_id}/stages/{stage_id}")
async def update_stage_endpoint(
    itinerary_id: int,
    stage_id: int,
    payload: StageCreate,
    current_user: dict = Depends(get_current_user),
):
    """Update a stage within an itinerary owned by the current athlete."""
    from ...db.database import get_itinerary, get_stage, update_stage

    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary["athlete_id"] != _user_id(current_user) and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    tenant_id = current_user.get("tenant_id", itinerary.get("athlete_id"))
    stage = get_stage(stage_id)
    if not stage or stage.get("itinerary_id") != itinerary_id:
        raise HTTPException(status_code=404, detail="Stage not found")
    data = payload.model_dump(exclude_unset=True)
    data["itinerary_id"] = itinerary_id
    ok = update_stage(stage_id, data, tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Stage not found or no changes")
    return get_stage(stage_id)


@router.delete("/{itinerary_id}/stages/{stage_id}")
async def delete_stage_endpoint(
    itinerary_id: int,
    stage_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Delete a stage from an itinerary owned by the current athlete."""
    from ...db.database import delete_stage, get_itinerary, get_stage

    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary["athlete_id"] != _user_id(current_user) and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    tenant_id = current_user.get("tenant_id", itinerary.get("athlete_id"))
    stage = get_stage(stage_id)
    if not stage or stage.get("itinerary_id") != itinerary_id:
        raise HTTPException(status_code=404, detail="Stage not found")
    ok = delete_stage(stage_id, tenant_id)
    return {"deleted": ok}


@router.put("/{itinerary_id}/reorder")
async def reorder_stages_endpoint(
    itinerary_id: int,
    stage_order: list[int],
    current_user: dict = Depends(get_current_user),
):
    """Reorder stages within an itinerary owned by the current athlete."""
    from ...db.database import get_itinerary, reorder_stages

    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary["athlete_id"] != _user_id(current_user) and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    tenant_id = current_user.get("tenant_id", itinerary.get("athlete_id"))
    reorder_stages(itinerary_id, stage_order, tenant_id)
    return {"reordered": True}
