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
    from ..db.database import save_ride
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
async def list_rides(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), sort: str = Query("date", pattern="^(date|distance|duration)$")):
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
    from ..db.database import save_ride
    from ..ingestion.gps_parser import parse_gpx_file, points_to_ride
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
    from ..db.database import save_ride
    from ..ingestion.gps_parser import parse_fit_file, points_to_ride
    import tempfile
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as tmp:
        tmp.write(content)
        temp_path = tmp.name
    try:
        points_data = parse_fit_file(temp_path)
    finally:
        import os
        os.unlink(temp_path)
    ride_data = points_to_ride(points_data, name=file.filename)
    if "error" not in ride_data:
        ride = Ride(**ride_data)
        ride_id = save_ride({k: v for k, v in ride.to_dict().items() if k != "id"})
        ride_data["id"] = int(ride_id)
    return ride_data

@router.post("/import/multiple")
async def import_multiple(files: List[UploadFile] = File(...)):
    from ..db.database import save_ride
    from ..ingestion.gps_parser import parse_gpx_file, parse_fit_file, points_to_ride
    import tempfile
    imported = []
    for file in files:
        content = await file.read()
        ext = file.filename.lower().split('.')[-1] if file.filename else ""
        if ext == "gpx":
            points = parse_gpx_file(content.decode())
        elif ext in ("fit", "fitf"):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as tmp:
                tmp.write(content)
                temp_path = tmp.name
            try:
                points = parse_fit_file(temp_path)
            finally:
                import os
                os.unlink(temp_path)
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

@router.get("/charts/distance/{ride_id}")
async def distance_chart(ride_id: int):
    from ..db.database import get_ride as _get_ride
    from ..analytics.analytics import create_distance_chart
    ride = _get_ride(ride_id)
    if not ride: raise HTTPException(status_code=404, detail="Ride not found")
    gps_points = ride.get("gps_points")
    if not gps_points: raise HTTPException(status_code=400, detail="No GPS points")
    points = [GPSPoint(**p) for p in gps_points]
    from ..processing.processing import build_segments
    segments = build_segments(points)
    path = f"ride_{ride_id}_distance.png"
    create_distance_chart(segments, path)
    from fastapi.responses import FileResponse
    return FileResponse(path, media_type="image/png", filename="distance.png")

@router.get("/charts/elevation/{ride_id}")
async def elevation_chart(ride_id: int):
    from ..db.database import get_ride as _get_ride
    from ..analytics.analytics import create_elevation_chart
    ride = _get_ride(ride_id)
    if not ride: raise HTTPException(status_code=404, detail="Ride not found")
    gps_points = ride.get("gps_points")
    if not gps_points: raise HTTPException(status_code=400, detail="No GPS points")
    points = [GPSPoint(**p) for p in gps_points]
    from ..processing.processing import build_segments
    segments = build_segments(points)
    path = f"ride_{ride_id}_elevation.png"
    create_elevation_chart(segments, path)
    from fastapi.responses import FileResponse
    return FileResponse(path, media_type="image/png", filename="elevation.png")

@router.post("/athletes")
async def create_athlete(athlete_data: dict):
    from ..db.database import save_athlete, init_db
    athlete_id = save_athlete(athlete_data)
    return {"id": int(athlete_id), **athlete_data}

@router.get("/athletes/{athlete_id}")
async def get_athlete(athlete_id: int):
    from ..db.database import get_athlete as _get_athlete
    athlete = _get_athlete(athlete_id)
    if not athlete: raise HTTPException(status_code=404, detail="Athlete not found")
    return athlete

@router.post("/athletes/{athlete_id}/metrics")
async def add_metric(athlete_id: int, metric_data: dict):
    from ..db.database import save_metric, init_db
    metric_id = save_metric({"athlete_id": athlete_id, **metric_data})
    return {"id": int(metric_id), "athlete_id": athlete_id, **metric_data}

@router.put("/athletes/{athlete_id}")
async def update_athlete(athlete_id: int, athlete_data: dict):
    from ..db.database import update_athlete as _update, get_athlete as _get
    if not _get(athlete_id): raise HTTPException(status_code=404, detail="Athlete not found")
    _update(athlete_id, athlete_data)
    return {"id": athlete_id, **athlete_data}


@router.get("/import/google-fit/auth")
async def google_fit_auth(client_id: str = Query(...), redirect_uri: str = Query("http://localhost:8000/api/v1/import/google-fit/callback"), state: str = ""):
    from ..ingestion.google_fit import get_authorization_url
    auth_url = get_authorization_url(client_id, redirect_uri=redirect_uri, state=state)
    return {"auth_url": auth_url}

@router.post("/import/google-fit/token")
async def google_fit_exchange_token(payload: dict):
    from ..ingestion.google_fit import exchange_code_for_token
    token_data = exchange_code_for_token(
        payload.get("client_id"),
        payload.get("client_secret"),
        payload.get("code"),
        payload.get("redirect_uri", "http://localhost:8000/api/v1/import/google-fit/callback"),
    )
    return {"access_token": token_data.get("access_token"), "refresh_token": token_data.get("refresh_token"), "expires_in": token_data.get("expires_in")}

@router.post("/import/google-fit")
async def import_google_fit(payload: dict):
    from ..db.database import save_ride
    from ..ingestion.google_fit import fetch_cycling_activities, google_fit_to_ride
    access_token = payload.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="access_token required")
    activities = fetch_cycling_activities(access_token)
    rides_data = google_fit_to_ride(activities)
    imported = []
    for ride_data in rides_data:
        from ..models.models import Ride
        ride = Ride(**{k: v for k, v in ride_data.items() if k != "id"})
        ride_id = save_ride({k: v for k, v in ride.to_dict().items() if k != "id"})
        ride_data["id"] = int(ride_id)
        imported.append(ride_data)
    return {"imported": imported, "count": len(imported)}

@router.get("/scores/athlete/{athlete_id}")
async def get_athlete_scores(athlete_id: int):
    from ..db.database import get_all_rides, get_athlete
    from ..analytics.performance import calculate_performance_score, calculate_endurance_score, calculate_efficiency_score, get_experience_level
    athlete = get_athlete(athlete_id)
    if not athlete: raise HTTPException(status_code=404, detail="Athlete not found")
    rides = [Ride(**r) for r in get_all_rides()]
    if rides:
        latest = rides[-1]
        return {"athlete": athlete, "scores": {"performance_score": calculate_performance_score(latest), "endurance_score": calculate_endurance_score(rides), "efficiency_score": calculate_efficiency_score(latest), "experience_level": get_experience_level(len(rides), sum(r.distance_km for r in rides))}}
    return {"athlete": athlete, "scores": {"performance_score": 0, "endurance_score": 0, "efficiency_score": 0, "experience_level": "Beginner"}}

@router.post("/benchmark/compare")
async def benchmark_compare(ride_data: dict):
    from ..analytics.benchmark import compare_with_benchmark
    from ..models.models import Ride
    ride = Ride(**ride_data)
    return compare_with_benchmark(ride)

@router.get("/knowledge")
async def list_knowledge():
    from ..analytics.knowledge_base import load_knowledge_base
    return {"topics": list(load_knowledge_base().keys())}

@router.get("/knowledge/search")
async def search_knowledge(query: str = ""):
    from ..analytics.knowledge_base import search_knowledge_base
    return {"results": search_knowledge_base(query)}

@router.get("/coach/workout")
async def workout_recommendations(athlete_id: int = 0):
    from ..db.database import get_all_rides, get_athlete
    from ..analytics.ai_coach import generate_workout_recommendations
    rides = [Ride(**r) for r in get_all_rides()]
    athlete = get_athlete(athlete_id) if athlete_id else None
    return {"recommendations": generate_workout_recommendations(rides, athlete)}

@router.get("/coach/recovery")
async def recovery_recommendations(fatigue_score: float = 5.0, ride_id: int = 0):
    from ..db.database import get_ride
    from ..analytics.ai_coach import generate_recovery_recommendations
    ride = Ride(**get_ride(ride_id)) if ride_id else None
    return {"recommendations": generate_recovery_recommendations(ride, fatigue_score)}

@router.get("/coach/trends")
async def historical_trends():
    from ..db.database import get_all_rides
    from ..analytics.ai_coach import analyze_historical_trends
    rides = [Ride(**r) for r in get_all_rides()]
    return analyze_historical_trends(rides)

@router.get("/rides/{ride_id}/map/google")
async def google_static_map(ride_id: int):
    from ..db.database import get_ride as _get_ride
    from ..maps.google_maps import create_google_static_map, get_google_api_key
    from fastapi.responses import FileResponse
    ride = _get_ride(ride_id)
    if not ride: raise HTTPException(status_code=404, detail="Ride not found")
    gps_points = ride.get("gps_points")
    if not gps_points: raise HTTPException(status_code=400, detail="No GPS points")
    api_key = get_google_api_key()
    if not api_key: raise HTTPException(status_code=500, detail="GOOGLE_MAPS_API_KEY not configured")
    points = [GPSPoint(**p) for p in gps_points]
    path = f"ride_{ride_id}_google_map.png"
    create_google_static_map(points, api_key, path)
    return FileResponse(path, media_type="image/png", filename="map.png")

@router.get("/admin/backup")
async def create_backup():
    from ..db.database import backup_database
    from fastapi.responses import FileResponse
    path = backup_database()
    return FileResponse(path, media_type="application/octet-stream", filename="backup.db")

@router.post("/admin/indexes")
async def create_db_indexes():
    from ..db.database import create_indices
    create_indices()
    return {"status": "indexes_created"}

@router.get("/admin/stats")
async def get_system_stats():
    from ..db.database import get_all_rides
    rides = get_all_rides()
    total_km = sum(r.get("distance_km", 0) for r in rides)
    total_duration = sum(r.get("duration_minutes", 0) for r in rides)
    from pathlib import Path
    db_size = Path("rides.db").stat().st_size if Path("rides.db").exists() else 0
    return {"rides_count": len(rides), "total_km": round(total_km, 1), "total_duration_hours": round(total_duration / 60, 1), "db_size_bytes": db_size}

@router.get("/health/detailed")
async def detailed_health_check():
    from ..db.database import get_all_rides, init_db
    rides = get_all_rides()
    from pathlib import Path
    db_ok = Path("rides.db").exists()
    return {"status": "ok", "service": "bikemaster", "database_connected": db_ok, "rides_in_db": len(rides), "api_version": "1.0"}

@router.post("/admin/reset-demo")
async def reset_demo_data():
    from ..db.database import get_all_rides, delete_ride, init_db
    rides = get_all_rides()
    for r in rides:
        if "demo" in r.get("date", ""):
            delete_ride(r["id"])
    from scripts.generate_sample_ride import generate_sample_ride
    generate_sample_ride()
    return {"status": "demo_reset", "message": "Demo data regenerated"}

@router.get("/rides/count")
async def count_rides():
    from ..db.database import get_all_rides
    return {"count": len(get_all_rides())}
