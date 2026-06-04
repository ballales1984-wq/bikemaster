"""API routes."""
from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from ..models.models import Ride, GPSPoint
from ..analytics.analytics import calculate_summary, analyze_ride
from ..analytics.calories import estimate_calories, calories_per_km
from ..analytics.fatigue import calculate_fatigue_score, estimate_recovery_hours, get_recovery_recommendation
from ..processing.processing import process_route
from ..maps.map_renderer import create_route_map

router = APIRouter()

@router.get("/health")
async def health_check(): return {"status": "ok", "service": "bikemaster"}

@router.post("/rides")
async def create_ride(ride_data: dict):
    from ..db.database import save_ride, init_db
    init_db()
    points = ride_data.get("gps_points", [])
    ride_dict = {k: v for k, v in ride_data.items() if k != "id"}
    if points: ride_dict["gps_points"] = points
    if not ride_dict.get("avg_speed_kmh") and ride_dict.get("distance_km") and ride_dict.get("duration_minutes"):
        ride_dict["avg_speed_kmh"] = ride_dict["distance_km"] / (ride_dict["duration_minutes"] / 60)
    if not ride_dict.get("calories"):
        ride = Ride(**{k: v for k, v in ride_dict.items() if k != "gps_points"})
        ride_dict["calories"] = estimate_calories(ride, method="physics")
    ride_id = save_ride(ride_dict)
    return {"id": int(ride_id), **ride_dict}

@router.get("/rides")
async def list_rides(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), sort: str = Query("date", regex="^(date|distance|duration)$")):
    from ..db.database import get_all_rides
    all_rides = get_all_rides()
    # Sort
    reverse = sort == "date"
    if sort == "distance":
        all_rides = sorted(all_rides, key=lambda x: x.get("distance_km", 0), reverse=True)
    elif sort == "duration":
        all_rides = sorted(all_rides, key=lambda x: x.get("duration_minutes", 0), reverse=True)
    elif sort == "date":
        all_rides = sorted(all_rides, key=lambda x: x.get("date", ""), reverse=True)
    # Paginate
    start = (page - 1) * page_size
    paginated = all_rides[start:start + page_size]
    return {"rides": paginated, "total": len(all_rides), "page": page, "page_size": page_size}

@router.get("/rides/{ride_id}")
async def get_ride(ride_id: int):
    from ..db.database import get_ride as _get_ride
    ride = _get_ride(ride_id)
    if not ride: raise HTTPException(status_code=404, detail="Ride not found")
    # Add analytics
    r = Ride(**ride)
    ride["calories"] = r.calories or estimate_calories(r)
    ride["fatigue_score"] = round(calculate_fatigue_score(r), 1)
    ride["calories_per_km"] = round(calories_per_km(r), 0) if r.distance_km else 0
    return ride

@router.delete("/rides/{ride_id}")
async def delete_ride(ride_id: int):
    from ..db.database import delete_ride as _delete
    if not _delete(ride_id): raise HTTPException(status_code=404, detail="Ride not found")
    return {"deleted": True}

@router.post("/rides/analyze")
async def analyze_rides(rides: List[dict]):
    return calculate_summary([Ride(**r) for r in rides])

@router.post("/rides/{ride_id}/analyze")
async def analyze_single_ride(ride_id: int, ride_data: dict):
    return analyze_ride(Ride(id=ride_id, **ride_data))

@router.post("/rides/{ride_id}/map")
async def generate_ride_map(ride_id: int):
    from ..db.database import get_ride as _get_ride
    ride = _get_ride(ride_id)
    if not ride: raise HTTPException(status_code=404, detail="Ride not found")
    gps_points = ride.get("gps_points")
    if not gps_points: raise HTTPException(status_code=400, detail="No GPS points for this ride")
    points = [GPSPoint(**p) for p in gps_points]
    map_path = create_route_map(points, output_path=f"ride_{ride_id}_map.html")
    return {"map_url": f"/static/ride_{ride_id}_map.html"}

@router.post("/import/gpx")
async def import_gpx(file: UploadFile = File(...)):
    from ..db.database import save_ride, init_db
    from ..ingestion.gps_parser import parse_gpx_file, points_to_ride
    init_db()
    content = await file.read()
    points_data = parse_gpx_file(content.decode())
    ride_data = points_to_ride(points_data, name=file.filename)
    if "error" not in ride_data:
        ride = Ride(**ride_data)
        ride_id = save_ride({k: v for k, v in ride.to_dict().items() if k != "id"})
        ride_data["id"] = int(ride_id)
    return ride_data

@router.post("/import/fit")
async def import_fit(file: UploadFile = File(...)):
    from ..db.database import save_ride, init_db
    from ..ingestion.gps_parser import parse_fit_file, points_to_ride
    init_db()
    content = await file.read()
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(content)
    points_data = parse_fit_file(temp_path)
    import os
    os.remove(temp_path)
    ride_data = points_to_ride(points_data, name=file.filename)
    if "error" not in ride_data:
        ride = Ride(**ride_data)
        ride_id = save_ride({k: v for k, v in ride.to_dict().items() if k != "id"})
        ride_data["id"] = int(ride_id)
    return ride_data

@router.post("/import/multiple")
async def import_multiple(files: List[UploadFile] = File(...)):
    from ..db.database import save_ride, init_db
    from ..ingestion.gps_parser import parse_gpx_file, parse_fit_file, points_to_ride
    init_db()
    imported = []
    for file in files:
        content = await file.read()
        ext = file.filename.lower().split('.')[-1] if file.filename else ""
        if ext == "gpx":
            points = parse_gpx_file(content.decode())
        elif ext in ("fit", "fitf"):
            temp_path = f"temp_{file.filename}"
            with open(temp_path, "wb") as f:
                f.write(content)
            points = parse_fit_file(temp_path)
        else:
            points = []
        ride_data = points_to_ride(points, name=file.filename)
        if "error" not in ride_data:
            ride = Ride(**ride_data)
            ride_id = save_ride({k: v for k, v in ride.to_dict().items() if k != "id"})
            ride_data["id"] = int(ride_id)
            imported.append(ride_data)
    return {"imported": imported, "count": len(imported)}

@router.get("/rides/export/json")
async def export_json():
    from ..db.database import get_all_rides
    from ..analytics.analytics import export_rides_json
    rides = [Ride(**r) for r in get_all_rides()]
    path = export_rides_json(rides, "rides_export.json")
    from fastapi.responses import FileResponse
    return FileResponse(path, media_type="application/json", filename="rides.json")

@router.get("/rides/export/csv")
async def export_csv():
    from ..db.database import get_all_rides
    from ..analytics.analytics import export_rides_csv
    rides = [Ride(**r) for r in get_all_rides()]
    path = export_rides_csv(rides, "rides_export.csv")
    from fastapi.responses import FileResponse
    return FileResponse(path, media_type="text/csv", filename="rides.csv")

@router.get("/rides/{ride_id}/report")
async def get_ride_report(ride_id: int):
    from ..db.database import get_ride as _get_ride
    from ..analytics.analytics import generate_text_report, analyze_ride
    ride = _get_ride(ride_id)
    if not ride: raise HTTPException(status_code=404, detail="Ride not found")
    return {"report": generate_text_report(Ride(**ride))}

@router.get("/charts/speed/{ride_id}")
async def speed_chart(ride_id: int):
    from ..db.database import get_ride as _get_ride
    from ..analytics.analytics import create_speed_chart
    ride = _get_ride(ride_id)
    if not ride: raise HTTPException(status_code=404, detail="Ride not found")
    gps_points = ride.get("gps_points")
    if not gps_points: raise HTTPException(status_code=400, detail="No GPS points")
    points = [GPSPoint(**p) for p in gps_points]
    from ..processing.processing import build_segments
    segments = build_segments(points)
    path = f"ride_{ride_id}_speed.png"
    create_speed_chart(segments, path)
    from fastapi.responses import FileResponse
    return FileResponse(path, media_type="image/png", filename="speed.png")

@router.get("/charts/duration")
async def duration_chart():
    from ..db.database import get_all_rides
    from ..analytics.analytics import create_duration_chart
    rides = [Ride(**r) for r in get_all_rides()]
    path = "duration_chart.png"
    create_duration_chart(rides, path)
    from fastapi.responses import FileResponse
    return FileResponse(path, media_type="image/png", filename="duration.png")