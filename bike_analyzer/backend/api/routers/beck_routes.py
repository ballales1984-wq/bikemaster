"""Beck Depression Inventory API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from bike_analyzer.backend.db.database import (
    get_beck_assessment,
    get_beck_assessments_by_athlete,
    get_latest_beck_assessment,
    save_beck_assessment,
)
from bike_analyzer.backend.security import get_current_user

from ..routes import _current_athlete_id
from ..schemas import BeckAssessmentCreate, BeckAssessmentResponse, BeckHistoryResponse

router = APIRouter(prefix="/beck", tags=["beck"])


@router.post("/assessments", response_model=BeckAssessmentResponse, status_code=201)
async def create_beck_assessment(
    payload: BeckAssessmentCreate,
    current_user: dict = Depends(get_current_user),
):
    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    assessment = payload.model_dump()
    assessment["athlete_id"] = athlete_id
    assessment["tenant_id"] = tenant_id
    assessment_id = save_beck_assessment(assessment, tenant_id=tenant_id)
    result = get_beck_assessment(assessment_id)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Failed to save Beck assessment")
    return result


@router.get("/assessments", response_model=list[BeckAssessmentResponse])
async def list_beck_assessments(
    current_user: dict = Depends(get_current_user),
):
    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    return get_beck_assessments_by_athlete(athlete_id, tenant_id=tenant_id)


@router.get("/assessments/latest", response_model=BeckAssessmentResponse | None)
async def get_latest_beck(
    current_user: dict = Depends(get_current_user),
):
    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    return get_latest_beck_assessment(athlete_id, tenant_id=tenant_id)


@router.get("/history", response_model=BeckHistoryResponse)
async def get_beck_history(
    current_user: dict = Depends(get_current_user),
):
    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    items = get_beck_assessments_by_athlete(athlete_id, tenant_id=tenant_id)
    latest = items[0] if items else None
    trend = [
        {
            "date": item.get("created_at"),
            "score": item.get("total_score"),
            "severity": item.get("severity"),
        }
        for item in items
    ]
    return BeckHistoryResponse(items=items, latest=latest, trend=trend)
