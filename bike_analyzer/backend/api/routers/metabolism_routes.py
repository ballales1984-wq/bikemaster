"""Metabolism tracking REST API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from bike_analyzer.backend.analytics.metabolism import (
    calibrate_athlete,
    ensure_metabolic_profile,
    get_athlete_weights,
    recalculate_daily_summary,
    recalculate_range,
)
from bike_analyzer.backend.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metabolism", tags=["metabolism"])


class MetabolicProfileCreate(BaseModel):
    weight_kg: float | None = None
    height_cm: float | None = None
    age: int | None = None
    fat_percentage: float | None = None
    sex: str = "male"
    bmr_formula: str = "mifflin"
    activity_level: str = "moderate"
    bmr_kcal: float | None = None
    tdee_kcal: float | None = None
    notes: str | None = None


class FoodLogCreate(BaseModel):
    date: str
    meal_type: str
    description: str
    kcal: float
    carbs_g: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    sodium_mg: float | None = None


class FoodLogUpdate(BaseModel):
    meal_type: str | None = None
    description: str | None = None
    kcal: float | None = None
    carbs_g: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    sodium_mg: float | None = None


class CalibrateRequest(BaseModel):
    sensor_bmr_kcal: float
    sensor_tdee_kcal: float
    date: str


class NutritionFoodItemCreate(BaseModel):
    name: str
    category: str
    kcal_per_100g: float
    carbs_g_per_100g: float | None = None
    protein_g_per_100g: float | None = None
    fat_g_per_100g: float | None = None
    fiber_g_per_100g: float | None = None
    sodium_mg: float | None = None


class NutritionFoodItemUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    kcal_per_100g: float | None = None
    carbs_g_per_100g: float | None = None
    protein_g_per_100g: float | None = None
    fat_g_per_100g: float | None = None
    fiber_g_per_100g: float | None = None
    sodium_mg: float | None = None


def _current_athlete_id(current_user: dict) -> int:
    try:
        return int(current_user.get("athlete_id") or current_user["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid user token") from exc


@router.get("/profile")
async def get_metabolic_profile_endpoint(current_user: dict = Depends(get_current_user)):
    """Return the athlete's metabolic profile."""
    from bike_analyzer.backend.analytics.repositories.metabolism_repository import (
        MetabolismRepository,
    )

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    profile = MetabolismRepository.get_metabolic_profile(athlete_id, tenant_id)
    if not profile:
        profile = ensure_metabolic_profile(athlete_id, tenant_id)
    if not profile:
        profile = {
            "athlete_id": athlete_id,
            "tenant_id": tenant_id,
            "sex": "male",
            "bmr_formula": "mifflin",
            "activity_level": "moderate",
        }
    return profile


@router.put("/profile")
async def upsert_metabolic_profile_endpoint(
    payload: MetabolicProfileCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create or update the athlete's metabolic profile."""
    from bike_analyzer.backend.analytics.repositories.metabolism_repository import (
        MetabolismRepository,
    )
    from bike_analyzer.backend.db.database import get_athlete

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete = get_athlete(athlete_id, tenant_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    valid_sex = {"male", "female"}
    if payload.sex not in valid_sex:
        raise HTTPException(status_code=422, detail=f"Invalid sex: {payload.sex}")
    valid_activity = {"sedentary", "light", "moderate", "active", "very_active"}
    if payload.activity_level not in valid_activity:
        raise HTTPException(status_code=422, detail=f"Invalid activity_level: {payload.activity_level}")
    data = payload.model_dump(exclude_none=True)
    data["athlete_id"] = athlete_id
    data["tenant_id"] = tenant_id
    MetabolismRepository.save_metabolic_profile(data, athlete_id, tenant_id)
    profile = MetabolismRepository.get_metabolic_profile(athlete_id, tenant_id)
    return profile or data


@router.get("/food-log")
async def get_food_logs(
    date: str = Query(..., min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    current_user: dict = Depends(get_current_user),
):
    """Return food logs for a specific date."""
    from bike_analyzer.backend.analytics.repositories.metabolism_repository import (
        MetabolismRepository,
    )

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    return MetabolismRepository.get_food_logs_by_athlete_date(athlete_id, date, tenant_id=tenant_id)


@router.post("/food-log", status_code=201)
async def create_food_log(
    payload: FoodLogCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new food log entry."""
    from bike_analyzer.backend.db.database import get_athlete, get_food_log, save_food_log

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete = get_athlete(athlete_id, tenant_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    data = payload.model_dump(exclude_none=True)
    data["athlete_id"] = athlete_id
    data["tenant_id"] = tenant_id
    log_id = save_food_log(data, tenant_id)
    row = get_food_log(log_id)
    return row or {}


@router.put("/food-log/{log_id}")
async def update_food_log(
    log_id: int,
    payload: FoodLogUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update an existing food log entry."""
    from bike_analyzer.backend.db.database import get_food_log, update_food_log

    athlete_id = _current_athlete_id(current_user)
    row = get_food_log(log_id)
    if not row or row.get("athlete_id") != athlete_id:
        raise HTTPException(status_code=404, detail="Food log not found")
    data = payload.model_dump(exclude_none=True)
    update_food_log(log_id, data)
    return get_food_log(log_id)


@router.delete("/food-log/{log_id}", status_code=204)
async def delete_food_log(log_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a food log entry."""
    from bike_analyzer.backend.db.database import delete_food_log, get_food_log

    athlete_id = _current_athlete_id(current_user)
    row = get_food_log(log_id)
    if not row or row.get("athlete_id") != athlete_id:
        raise HTTPException(status_code=404, detail="Food log not found")
    delete_food_log(log_id)
    return None


@router.get("/daily-summary")
async def get_daily_summary(
    date: str = Query(..., min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    current_user: dict = Depends(get_current_user),
):
    """Return the metabolic daily summary for the authenticated athlete."""
    try:
        tenant_id = current_user.get("tenant_id", current_user["id"])
        athlete_id = _current_athlete_id(current_user)
        summary = recalculate_daily_summary(athlete_id, date, tenant_id)
        return summary
    except Exception as exc:
        logger.exception("Failed to compute daily summary for athlete_id=%s date=%s", _current_athlete_id(current_user), date)
        raise HTTPException(status_code=500, detail="Failed to compute daily summary") from exc


@router.get("/range-summary")
async def get_range_summary(
    start_date: str = Query(..., min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(..., min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    current_user: dict = Depends(get_current_user),
):
    """Return metabolic daily summaries for a date range."""
    try:
        tenant_id = current_user.get("tenant_id", current_user["id"])
        athlete_id = _current_athlete_id(current_user)
        summaries = recalculate_range(athlete_id, start_date, end_date, tenant_id)
        return summaries
    except Exception as exc:
        logger.exception("Failed to compute range summary for athlete_id=%s", _current_athlete_id(current_user))
        raise HTTPException(status_code=500, detail="Failed to compute range summary") from exc


@router.post("/recalculate")
async def recalculate_daily(
    date: str = Query(..., min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    current_user: dict = Depends(get_current_user),
):
    """Force recalculate the metabolic daily summary for a specific date."""
    try:
        tenant_id = current_user.get("tenant_id", current_user["id"])
        athlete_id = _current_athlete_id(current_user)
        summary = recalculate_daily_summary(athlete_id, date, tenant_id)
        return summary
    except Exception as exc:
        logger.exception("Failed to recalculate daily summary for athlete_id=%s date=%s", _current_athlete_id(current_user), date)
        raise HTTPException(status_code=500, detail="Failed to recalculate daily summary") from exc


@router.post("/calibrate")
async def calibrate_endpoint(
    payload: CalibrateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Calibrate the athlete's metabolic profile with sensor values."""
    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    result = calibrate_athlete(
        athlete_id,
        payload.sensor_bmr_kcal,
        payload.sensor_tdee_kcal,
        payload.date,
        tenant_id,
    )
    return result


@router.post("/recalculate-calibrated")
async def recalculate_calibrated(
    date: str = Query(..., min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    current_user: dict = Depends(get_current_user),
):
    """Recalculate the daily summary using calibrated weights."""
    try:
        athlete_id = _current_athlete_id(current_user)
        tenant_id = current_user.get("tenant_id", current_user["id"])
        from bike_analyzer.backend.analytics.metabolism import recalculate_daily_summary_calibrated

        summary = recalculate_daily_summary_calibrated(athlete_id, date, tenant_id)
        return summary
    except Exception as exc:
        logger.exception("Failed to recalculate calibrated summary for athlete_id=%s date=%s", _current_athlete_id(current_user), date)
        raise HTTPException(status_code=500, detail="Failed to recalculate calibrated summary") from exc


@router.get("/weights")
async def get_weights(current_user: dict = Depends(get_current_user)):
    """Return the athlete's adaptive weights."""
    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    weights = get_athlete_weights(athlete_id, tenant_id)
    data = weights.to_dict()
    data["athlete_id"] = athlete_id
    return data


@router.post("/nutrition", status_code=201)
async def create_nutrition_item(
    payload: NutritionFoodItemCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a nutrition food item."""
    from bike_analyzer.backend.db.database import save_nutrition_food_item

    tenant_id = current_user.get("tenant_id", current_user["id"])
    data = payload.model_dump(exclude_none=True)
    data["tenant_id"] = tenant_id
    item_id = save_nutrition_food_item(data, tenant_id)
    from bike_analyzer.backend.db.database import get_nutrition_food_item

    item = get_nutrition_food_item(item_id)
    return item or {}


@router.get("/nutrition/search")
async def search_nutrition(
    q: str = Query(...),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """Search nutrition food items."""
    from bike_analyzer.backend.db.database import search_nutrition_food_items

    results = search_nutrition_food_items(q, limit=limit)
    return results


@router.get("/nutrition/categories")
async def list_nutrition_categories(current_user: dict = Depends(get_current_user)):
    """List nutrition categories."""
    from bike_analyzer.backend.db.database import list_nutrition_categories

    categories = list_nutrition_categories()
    return categories


@router.get("/nutrition/{item_id}")
async def get_nutrition_item(item_id: int, current_user: dict = Depends(get_current_user)):
    """Get a nutrition food item by ID."""
    from bike_analyzer.backend.db.database import get_nutrition_food_item

    item = get_nutrition_food_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.put("/nutrition/{item_id}")
async def update_nutrition_item(
    item_id: int,
    payload: NutritionFoodItemUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update a nutrition food item."""
    from bike_analyzer.backend.db.database import get_nutrition_food_item, update_nutrition_food_item

    item = get_nutrition_food_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    data = payload.model_dump(exclude_none=True)
    update_nutrition_food_item(item_id, data)
    return get_nutrition_food_item(item_id)


@router.delete("/nutrition/{item_id}", status_code=204)
async def delete_nutrition_item(item_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a nutrition food item."""
    from bike_analyzer.backend.db.database import delete_nutrition_food_item

    delete_nutrition_food_item(item_id)
    return None


class ReferenceValuesImport(BaseModel):
    values: list[dict]


@router.post("/reference-values")
async def import_reference_values(
    payload: ReferenceValuesImport,
    current_user: dict = Depends(get_current_user),
):
    """Import metabolic reference values."""
    from bike_analyzer.backend.db.database import upsert_metabolic_reference_value

    tenant_id = current_user.get("tenant_id", current_user["id"])
    imported = 0
    for v in payload.values:
        upsert_metabolic_reference_value(v, tenant_id)
        imported += 1
    return {"imported": imported, "tenant_id": tenant_id}


@router.get("/reference-values")
async def list_reference_values(current_user: dict = Depends(get_current_user)):
    """List metabolic reference values."""
    from bike_analyzer.backend.db.database import get_all_metabolic_reference_values

    tenant_id = current_user.get("tenant_id", current_user["id"])
    return get_all_metabolic_reference_values(tenant_id)
