"""Ride-related API routes"""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.api.dependencies import get_db
from backend.services.ride_service import RideService, DEFAULT_DB_URL
from backend.models.schemas import (
    RideCreate,
    RideResponse,
    RideListResponse,
    FileImportRequest,
    ComparisonRequest,
    ComparisonResponse,
    AnalyticsData,
    FileFormat,
    SportType,
)
from backend.gps.mapper import generate_map


router = APIRouter()
router_prefixless = APIRouter()


def get_ride_service() -> RideService:
    return RideService(DEFAULT_DB_URL)


def _ride_to_dict(ride) -> dict:
    return {
        "id": ride.id,
        "name": ride.name,
        "description": ride.description,
        "sport_type": ride.sport_type,
        "source": ride.source,
        "external_id": ride.external_id,
        "created_at": ride.created_at.isoformat() if ride.created_at else None,
        "total_distance_km": ride.total_distance_km,
        "total_duration_seconds": ride.total_duration_seconds,
        "avg_speed_kmh": ride.avg_speed_kmh,
        "max_speed_kmh": ride.max_speed_kmh,
        "point_count": ride.point_count,
    }


@router.post("/", response_model=RideResponse, status_code=status.HTTP_201_CREATED)
def create_ride(
    ride_in: RideCreate,
    service: RideService = Depends(get_ride_service),
):
    ride = service.create_ride(ride_in)
    return RideResponse(**_ride_to_dict(ride))


@router.get("/", response_model=RideListResponse)
def list_rides(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sport_type: Optional[str] = Query(None),
    service: RideService = Depends(get_ride_service),
):
    rides, total = service.list_rides(page, page_size, sport_type)
    return RideListResponse(
        rides=[RideResponse(**_ride_to_dict(r)) for r in rides],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{ride_id}", response_model=RideResponse)
def get_ride(ride_id: int, service: RideService = Depends(get_ride_service)):
    ride = service.get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    return RideResponse(**_ride_to_dict(ride))


@router.put("/{ride_id}", response_model=RideResponse)
def update_ride(
    ride_id: int,
    ride_in: RideUpdate,
    service: RideService = Depends(get_ride_service),
):
    ride = service.update_ride(ride_id, ride_in)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    return RideResponse(**_ride_to_dict(ride))


@router.delete("/{ride_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ride(ride_id: int, service: RideService = Depends(get_ride_service)):
    ok = service.delete_ride(ride_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Ride not found")
    return None


@router.post("/import", response_model=RideResponse, status_code=status.HTTP_201_CREATED)
async def import_ride(
    request: FileImportRequest,
    ride_service: RideService = Depends(get_ride_service),
):
    try:
        ride = ride_service.import_ride(request)
        return RideResponse(**_ride_to_dict(ride))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/upload", response_model=RideResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    sport_type: SportType = SportType.CYCLING,
    name: Optional[str] = None,
    ride_service: RideService = Depends(get_ride_service),
):
    temp_path = Path(f"/tmp/{file.filename}")
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    fmt = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "unknown"
    try:
        request = FileImportRequest(format=FileFormat(fmt), sport_type=sport_type, name=name)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Unsupported file format: {fmt}"
        )

    try:
        ride = ride_service.import_ride(request)
        return RideResponse(**_ride_to_dict(ride))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{ride_id}/analytics", response_model=AnalyticsData)
def get_analytics(ride_id: int, service: RideService = Depends(get_ride_service)):
    data = service.compute_analytics(ride_id)
    if not data:
        raise HTTPException(status_code=404, detail="Ride not found")
    return data


@router.post("/{ride_id}/map")
def get_ride_map(
    ride_id: int,
    service: RideService = Depends(get_ride_service),
    heatmap: bool = Query(False, description="Show speed heatmap instead of polylines"),
    save_path: Optional[str] = Query(None, description="Save HTML map to this path"),
):
    ride = service.get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    points = sorted(ride.gps_points, key=lambda p: p.point_index)
    if len(points) < 2:
        raise HTTPException(status_code=400, detail="Not enough points for a map")

    lats = [p.latitude for p in points]
    lons = [p.longitude for p in points]

    result = service.processor.process(
        lats, lons,
        elevations=[p.elevation for p in points],
        timestamps=[p.timestamp for p in points],
    )

    speeds = result["speeds_kmh"]
    html = generate_map(
        lat=result["latitudes"].tolist(),
        lon=result["longitudes"].tolist(),
        elevations=(
            result["elevations"].tolist()
            if result["elevations"] is not None
            else None
        ),
        speeds=speeds.tolist(),
        name=ride.name,
        show_heatmap=heatmap,
        output_path=save_path,
    )

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


@router.post("/compare", response_model=ComparisonResponse)
def compare_rides(
    req: ComparisonRequest,
    service: RideService = Depends(get_ride_service),
):
    data = service.compare_rides(req.ride_ids)
    rides = service.list_rides(page=1, page_size=100)[0]
    ride_map = {r.id: r for r in rides}
    return ComparisonResponse(
        rides=[RideResponse(**_ride_to_dict(ride_map.get(rid))) for rid in req.ride_ids if rid in ride_map],
        comparison_summary=data.get("comparison", {}),
    )
