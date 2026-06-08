"""API routes."""
from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Body, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from ..models.models import Ride, GPSPoint, AthleteProfile, CalendarEvent
from ..analytics.analytics import calculate_summary, analyze_ride
from ..analytics.calories import estimate_calories, calories_per_km
from ..analytics.fatigue import calculate_fatigue_score, estimate_recovery_hours, get_recovery_recommendation
from ..analytics.badges import calculate_badges, get_heatmap_points
from ..analytics.granfondo_planner import generate_granfondo_plan
from ..processing.processing import process_route
from ..maps.map_renderer import create_route_map
from .schemas import RideCreate, RideResponse, RideAnalysisRequest, AthleteCreate, AthleteUpdate, MetricCreate, CalendarEventCreate, CalendarEventUpdate, GoogleFitAuthQuery, GoogleFitTokenRequest, GoogleFitImportRequest, GranfondoPlanRequest
from ..utils.logger import get_logger
from ..config import DB_PATH
from ..security import get_current_user, get_optional_current_user, get_admin_user

from ..maps.serpapi_maps import get_local_results, search_nearby


logger = get_logger(__name__)

FAKE_USERS_DB = {}

router = APIRouter()

@router.get("/health")
async def health_check(): return {"status": "ok", "service": "bikemaster"}

@router.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    from ..security import verify_password, create_access_token
    user = FAKE_USERS_DB.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": create_access_token(subject=form_data.username, is_admin=user.get("is_admin", False)), "token_type": "bearer"}

@router.post("/auth/register")
async def register(username: str = Body(..., min_length=3), password: str = Body(..., min_length=6), is_admin: bool = Body(False)):
    from ..security import hash_password, create_access_token
    from ..db.database import get_db_connection
    if username in FAKE_USERS_DB:
        raise HTTPException(status_code=400, detail="Username already exists")
    FAKE_USERS_DB[username] = {"username": username, "hashed_password": hash_password(password), "is_admin": is_admin}
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO athletes (name, experience_level) VALUES (?, ?)", (username, "Beginner"))
        conn.commit()
    return {"username": username, "msg": "Utente creato", "is_admin": is_admin}

def get_current_user_dependency():
    return Depends(get_current_user)

@router.post("/rides", response_model=RideResponse)
async def create_ride(ride_data: RideCreate, current_user: Optional[dict] = Depends(get_current_user)):
    from ..db.database import save_ride
    ride_dict = ride_data.model_dump()
    points = ride_dict.get("gps_points", [])
    if points: ride_dict["gps_points"] = points
    if not ride_dict.get("avg_speed_kmh") and ride_dict.get("distance_km") and ride_dict.get("duration_minutes") and ride_dict["duration_minutes"] > 0:
        ride_dict["avg_speed_kmh"] = ride_dict["distance_km"] / (ride_dict["duration_minutes"] / 60)
    if not ride_dict.get("calories"):
        ride = Ride(**{k: v for k, v in ride_dict.items() if k != "gps_points"})
        ride_dict["calories"] = estimate_calories(ride, method="physics")
    ride_id = save_ride(ride_dict)
    return {"id": int(ride_id), **ride_dict}

@router.get("/rides")
async def list_rides(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), sort: str = Query("date", pattern="^(date|distance|duration)$")):
    from ..db.database import get_paginated_rides
    rides, total = get_paginated_rides(page=page, page_size=page_size, sort=sort)
    return {"rides": rides, "total": total, "page": page, "page_size": page_size}

@router.get("/rides/{ride_id}")
async def get_ride(ride_id: int):
    from ..db.database import get_ride as _get_ride
    ride = _get_ride(ride_id)
    if not ride: raise HTTPException(status_code=404, detail="Ride not found")
    r = Ride(**ride)
    ride["fatigue_score"] = round(calculate_fatigue_score(r), 1)
    ride["calories_per_km"] = round(calories_per_km(r), 0) if r.distance_km else 0
    return ride

@router.delete("/rides/{ride_id}")
async def delete_ride(ride_id: int):
    from ..db.database import delete_ride as _delete
    if not _delete(ride_id): raise HTTPException(status_code=404, detail="Ride not found")
    return {"deleted": True}

@router.get("/rides/{ride_id}/segments")
async def get_ride_segments(ride_id: int, min_distance_m: int = Query(1000)):
    """Detect and return significant segments from ride GPS points."""
    from ..db.database import get_ride as _get_ride
    from ..processing.segment_detector import detect_climb_segments, detect_all_segments, segment_to_dict
    from ..models.models import GPSPoint
    
    ride = _get_ride(ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    
    gps_points = ride.get("gps_points")
    if not gps_points:
        raise HTTPException(status_code=400, detail="No GPS points for this ride")
    
    points = [GPSPoint(**p) for p in gps_points]
    climbs = detect_climb_segments(points)
    segments = detect_all_segments(points, min_length_m=min_distance_m)
    
    return {
        "ride_id": ride_id,
        "climbs": [segment_to_dict(c) for c in climbs],
        "segments": [{"distance_km": round(s.distance_m/1000, 2), "elevation_gain_m": s.elevation_gain_m, "avg_speed_kmh": round(s.avg_speed_km_h, 1)} for s in segments],
        "climb_count": len(climbs),
        "segment_count": len(segments)
    }

@router.post("/rides/analyze", response_model=dict)
async def analyze_rides(request: RideAnalysisRequest):
    return calculate_summary([Ride(**r.model_dump()) for r in request.rides])

@router.post("/rides/{ride_id}/analyze")
async def analyze_single_ride(ride_id: int, ride_data: RideCreate, current_user: dict = Depends(get_current_user_dependency)):
    return analyze_ride(Ride(id=ride_id, **ride_data.model_dump()))

@router.post("/rides/{ride_id}/map")
async def generate_ride_map(ride_id: int, current_user: Optional[dict] = Depends(get_optional_current_user)):
    from ..db.database import get_ride as _get_ride
    ride = _get_ride(ride_id)
    if not ride: raise HTTPException(status_code=404, detail="Ride not found")
    gps_points = ride.get("gps_points")
    if not gps_points: raise HTTPException(status_code=400, detail="No GPS points for this ride")
    points = [GPSPoint(**p) for p in gps_points]
    map_path = create_route_map(points, output_path=f"ride_{ride_id}_map.html")
    return {"map_url": f"/static/ride_{ride_id}_map.html"}

@router.post("/import/gpx")
async def import_gpx(file: UploadFile = File(...), current_user: dict = Depends(get_current_user_dependency)):
    from ..db.database import save_ride
    from ..ingestion.gps_parser import parse_gpx_file, points_to_ride
    content = await file.read()
    points_data = parse_gpx_file(content.decode())
    ride_data = points_to_ride(points_data, name=file.filename)
    if "error" not in ride_data:
        ride_id = save_ride({k: v for k, v in ride_data.items() if k != "id"})
        ride_data["id"] = int(ride_id)
    return ride_data

@router.post("/import/fit")
async def import_fit(file: UploadFile = File(...), current_user: dict = Depends(get_current_user_dependency)):
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
        ride_id = save_ride({k: v for k, v in ride_data.items() if k != "id"})
        ride_data["id"] = int(ride_id)
    return ride_data

@router.post("/import/multiple")
async def import_multiple(files: List[UploadFile] = File(...), current_user: dict = Depends(get_current_user_dependency)):
    from ..db.database import save_ride
    from ..ingestion.gps_parser import parse_gpx_file, parse_fit_file, points_to_ride
    import tempfile
    imported = []
    failed = []
    for file in files:
        try:
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
                ride_id = save_ride({k: v for k, v in ride_data.items() if k != "id"})
                ride_data["id"] = int(ride_id)
                imported.append(ride_data)
        except Exception as e:
            failed.append({"filename": file.filename, "error": str(e)})
    return {"imported": imported, "failed": failed, "count": len(imported), "total_files": len(files)}

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
async def get_ride_report(ride_id: int, current_user: dict = Depends(get_current_user_dependency)):
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
    path = f"duration_chart.png"
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

@router.post("/athletes", response_model=dict)
async def create_athlete(athlete_data: AthleteCreate, current_user: Optional[dict] = Depends(get_optional_current_user)):
    from ..db.database import save_athlete, init_db
    athlete_id = save_athlete(athlete_data.model_dump())
    return {"id": int(athlete_id), **athlete_data.model_dump()}

@router.get("/athletes")
async def list_athletes():
    from ..db.database import get_all_athletes
    athletes = get_all_athletes()
    return {"athletes": athletes}

@router.get("/athletes/{athlete_id}")
async def get_athlete_endpoint(athlete_id: int):
    from ..db.database import get_athlete as _get_athlete
    athlete = _get_athlete(athlete_id)
    if not athlete: raise HTTPException(status_code=404, detail="Athlete not found")
    return athlete

@router.post("/athletes/{athlete_id}/metrics")
async def add_metric(athlete_id: int, metric_data: MetricCreate, current_user: dict = Depends(get_current_user_dependency)):
    from ..db.database import save_metric, init_db
    metric_id = save_metric({"athlete_id": athlete_id, **metric_data.model_dump()})
    return {"id": int(metric_id), "athlete_id": athlete_id, **metric_data.model_dump()}

@router.put("/athletes/{athlete_id}")
async def update_athlete(athlete_id: int, athlete_data: AthleteUpdate, current_user: Optional[dict] = Depends(get_optional_current_user)):
    from ..db.database import update_athlete as _update, get_athlete as _get
    if not _get(athlete_id): raise HTTPException(status_code=404, detail="Athlete not found")
    _update(athlete_id, athlete_data.model_dump(exclude_none=True))
    return {"id": athlete_id, **athlete_data.model_dump(exclude_none=True)}


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
async def import_google_fit(payload: dict, current_user: dict = Depends(get_current_user_dependency)):
    from ..db.database import save_ride
    from ..ingestion.google_fit import fetch_cycling_activities, google_fit_to_ride
    access_token = payload.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="access_token required")
    activities = fetch_cycling_activities(access_token)
    rides_data = google_fit_to_ride(activities)
    imported = []
    for ride_data in rides_data:
        ride_id = save_ride({k: v for k, v in ride_data.items() if k != "id"})
        ride_data["id"] = int(ride_id)
        imported.append(ride_data)
    return {"imported": imported, "count": len(imported)}

@router.get("/scores/athlete/{athlete_id}")
async def get_athlete_scores(athlete_id: int, current_user: dict = Depends(get_current_user_dependency)):
    from ..db.database import get_rides_by_athlete, get_athlete
    from ..analytics.performance import calculate_performance_score, calculate_endurance_score, calculate_efficiency_score, get_experience_level
    athlete = get_athlete(athlete_id)
    if not athlete: raise HTTPException(status_code=404, detail="Athlete not found")
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id)]
    if rides:
        latest = rides[-1]
        return {"athlete": athlete, "scores": {"performance_score": calculate_performance_score(latest), "endurance_score": calculate_endurance_score(rides), "efficiency_score": calculate_efficiency_score(latest),         "experience_level": get_experience_level(AthleteProfile(**athlete))}}
    return {"athlete": athlete, "scores": {"performance_score": 0, "endurance_score": 0, "efficiency_score": 0, "experience_level": "Beginner"}}

@router.post("/benchmark/compare")
async def benchmark_compare(ride_data: dict):
    from ..analytics.benchmark import compare_athlete_to_benchmark
    from ..models.models import Ride
    ride = Ride(**ride_data)
    return compare_athlete_to_benchmark(AthleteProfile(), ride.distance_km, ride.avg_speed_kmh, ride.duration_hours)

@router.get("/knowledge")
async def list_knowledge():
    from ..analytics.knowledge_base import list_topics, get_kb_stats
    stats = get_kb_stats()
    return {
        "topics": stats["topics"],
        "chunks_per_topic": stats["chunks_per_topic"],
        "total_chunks": stats["total_chunks"],
        "total_words": stats["total_words"],
    }

@router.get("/knowledge/search")
async def search_knowledge_endpoint(query: str = "", max_chunks: int = 4, min_score: float = 0.05):
    from ..analytics.knowledge_base import search_knowledge_base, format_context_for_llm
    if not query or not query.strip():
        return {"results": [], "context": "", "count": 0}
    results = search_knowledge_base(query.strip(), max_chunks=max_chunks, min_score=min_score)
    context = format_context_for_llm(results)
    return {
        "results": results,
        "context": context,
        "count": len(results),
        "query": query,
        "topics_matched": sorted({r["topic"] for r in results}),
    }

@router.get("/knowledge/stats")
async def knowledge_stats():
    from ..analytics.knowledge_base import get_kb_stats
    return get_kb_stats()

@router.post("/knowledge/reload")
async def reload_knowledge():
    from ..analytics.knowledge_base import reload_kb
    return reload_kb()

@router.get("/coach/workout")
async def workout_recommendations(athlete_id: int = 0, current_user: Optional[dict] = Depends(get_optional_current_user)):
    from ..db.database import get_rides_by_athlete, get_athlete, get_db_connection
    from ..analytics.ai_coach import generate_workout_recommendations
    from ..models.models import AthleteProfile
    import traceback
    try:
        resolved_id = athlete_id
        if not resolved_id:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id FROM athletes ORDER BY id DESC LIMIT 1")
                row = cur.fetchone()
                resolved_id = row[0] if row else 0
        if not resolved_id:
            return {"recommendations": "Create an athlete profile in the Dashboard to receive personalized recommendations."}
        rides = [Ride(**r) for r in get_rides_by_athlete(resolved_id)]
        athlete_data = get_athlete(resolved_id)
        athlete = AthleteProfile(**athlete_data) if athlete_data else AthleteProfile()
        result = generate_workout_recommendations(athlete, rides)
        return {"recommendations": result}
    except Exception:
        traceback.print_exc()
        return {"recommendations": "AI Coach error. Please try again later."}


@router.get("/coach/full")
async def coach_full_data(athlete_id: int = 0, current_user: Optional[dict] = Depends(get_optional_current_user)):
    from ..db.database import get_all_rides, get_rides_by_athlete, get_athlete, get_db_connection, save_chat_message
    from ..analytics.ai_coach import ai_coach_full
    from ..models.models import AthleteProfile
    import traceback
    try:
        resolved_id = athlete_id
        if not resolved_id:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id FROM athletes ORDER BY id DESC LIMIT 1")
                row = cur.fetchone()
                resolved_id = row[0] if row else 0
        if not resolved_id:
            return {"training_advice": "Create an athlete profile in the Dashboard to receive personalized recommendations.", "recovery_advice": "Create an athlete profile in the Dashboard to receive personalized recommendations.", "historical_analysis": "", "training_scores": [], "recovery_scores": [], "charts": []}
        rides = [Ride(**r) for r in get_rides_by_athlete(resolved_id)]
        athlete_data = get_athlete(resolved_id)
        print(f"DEBUG: resolved_id={resolved_id}, athlete_data={athlete_data}")
        if not athlete_data:
            return {"training_advice": "Athlete not found. Create a profile in the Dashboard.", "recovery_advice": "Athlete not found. Create a profile in the Dashboard.", "historical_analysis": "", "training_scores": [], "recovery_scores": [], "charts": []}
        athlete = AthleteProfile(**athlete_data)
        result = ai_coach_full(athlete, rides, resolved_id)
        if athlete_id and result.get("training_advice"):
            save_chat_message(resolved_id, "assistant", result["training_advice"][:500])
        return result
    except Exception:
        traceback.print_exc()
        return {"training_advice": "AI Coach error. Please try again later.", "recovery_advice": "AI Coach error. Please try again later.", "historical_analysis": "", "training_scores": [], "recovery_scores": [], "charts": []}

@router.get("/coach/page", response_class=HTMLResponse)
async def coach_page():
    from pathlib import Path
    page = Path(__file__).parent.parent / "static" / "ai_coach.html"
    if page.exists():
        return page.read_text(encoding="utf-8")
    return HTMLResponse("<h1>AI Coach page not available</h1>", status_code=404)

@router.get("/coach/recovery")
async def recovery_recommendations(fatigue_score: float = 5.0, ride_id: int = 0, current_user: Optional[dict] = Depends(get_optional_current_user)):
    from ..db.database import get_ride, get_athlete
    from ..analytics.ai_coach import generate_recovery_recommendations
    from ..models.models import AthleteProfile, Ride
    import traceback
    try:
        ride_obj = Ride(**get_ride(ride_id)) if ride_id else None
        ride_data = get_ride(ride_id) if ride_id else None
        athlete_data = get_athlete(ride_data.get("athlete_id")) if ride_data else None
        athlete = AthleteProfile(**athlete_data) if athlete_data else AthleteProfile()
        result = generate_recovery_recommendations(athlete, [ride_obj] if ride_obj else [], fatigue_score)
        return {"recommendations": result}
    except Exception:
        traceback.print_exc()
        return {"recommendations": "AI Coach error. Please try again later."}


@router.get("/coach/trends")
async def historical_trends(current_user: Optional[dict] = Depends(get_optional_current_user)):
    from ..db.database import get_all_rides
    from ..analytics.ai_coach import analyze_historical_trends
    rides = [Ride(**r) for r in get_all_rides()]
    return analyze_historical_trends(rides)

@router.get("/rides/{ride_id}/map/google")
async def google_static_map(ride_id: int, colored: bool = False, current_user: Optional[dict] = Depends(get_optional_current_user)):
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
    suffix = "_colored" if colored else ""
    path = f"ride_{ride_id}_google_map{suffix}.png"
    create_google_static_map(points, api_key, path, colored=colored)
    return FileResponse(path, media_type="image/png", filename="map.png")

@router.get("/admin/backup")
async def create_backup(current_user: dict = Depends(get_admin_user)):
    from ..db.database import backup_database
    from fastapi.responses import FileResponse
    path = backup_database()
    return FileResponse(path, media_type="application/octet-stream", filename="backup.db")

@router.post("/admin/indexes")
async def create_db_indexes(current_user: dict = Depends(get_admin_user)):
    from ..db.database import create_indices
    create_indices()
    return {"status": "indexes_created"}

@router.get("/admin/stats")
async def get_system_stats(current_user: dict = Depends(get_admin_user)):
    from ..db.database import get_all_rides, DB_PATH
    rides = get_all_rides()
    total_km = sum(r.get("distance_km", 0) for r in rides)
    total_duration = sum(r.get("duration_minutes", 0) for r in rides)
    from pathlib import Path
    db_size = Path(DB_PATH).stat().st_size if Path(DB_PATH).exists() else 0
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

@router.put("/rides/{ride_id}")
async def update_ride(ride_id: int, ride: dict = Body(...), current_user: dict = Depends(get_current_user_dependency)):
    from ..db.database import update_ride as _update_ride, get_ride as _get_ride
    existing = _get_ride(ride_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Ride not found")
    merged = {**existing, **ride}
    _update_ride(ride_id, merged)
    return merged

@router.get("/rides/count")
async def count_rides():
    from ..db.database import get_all_rides
    return {"count": len(get_all_rides())}

@router.api_route("/coach/chat", methods=["GET", "POST"])
async def coach_chat(athlete_id: int = Query(...), message: str = Query(...)):
    from ..db.database import save_chat_message, get_chat_history, get_athlete
    from ..analytics.ai_coach import generate_training_advice
    from ..models.models import AthleteProfile
    from ..db.database import get_all_rides
    save_chat_message(athlete_id, "user", message[:500])
    athlete_data = get_athlete(athlete_id)
    athlete = AthleteProfile(**athlete_data) if athlete_data else AthleteProfile()
    rides = [Ride(**r) for r in get_all_rides()]
    response = generate_training_advice(athlete, rides, athlete_id)
    save_chat_message(athlete_id, "assistant", response[:500])
    return {"response": response, "history": get_chat_history(athlete_id)}

@router.get("/coach/history")
async def coach_history(athlete_id: int):
    from ..db.database import get_chat_history
    return {"history": get_chat_history(athlete_id)}

@router.get("/analytics/ceo")
async def ceo_analytics():
    from ..db.database import get_all_rides, get_all_athletes
    rides = get_all_rides()
    athletes = get_all_athletes()
    total_rides = len(rides)
    total_athletes = len(athletes)
    total_km = sum(r.get("distance_km", 0) for r in rides)
    total_hours = sum(r.get("duration_minutes", 0) for r in rides) / 60
    total_calories = sum(r.get("calories", 0) for r in rides)
    from datetime import datetime
    now = datetime.now()
    this_month = sum(1 for r in rides if r.get("date", "").startswith(now.strftime("%Y-%m")))
    last_month = sum(1 for r in rides if r.get("date", "").startswith(f"{now.year}-{now.month-1:02d}" if now.month > 1 else f"{now.year-1}-12"))
    from pathlib import Path
    db_size = Path(DB_PATH).stat().st_size if Path(DB_PATH).exists() else 0
    level_counts = {"Beginner": 0, "Amateur": 0, "Intermediate": 0, "Advanced": 0, "Elite": 0}
    for a in athletes:
        level = a.get("experience_level", "Beginner")
        if level in level_counts:
            level_counts[level] += 1
    return {
        "overview": {
            "total_athletes": total_athletes,
            "total_rides": total_rides,
            "total_kilometers": round(total_km, 1),
            "total_training_hours": round(total_hours, 1),
            "total_calories_burned": int(total_calories),
        },
        "growth": {
            "rides_this_month": this_month,
            "rides_last_month": last_month,
            "growth_rate": round((this_month - last_month) / last_month * 100, 1) if last_month else 0
        },
        "engagement": {
            "rides_per_athlete": round(total_rides / total_athletes, 1) if total_athletes else 0,
            "avg_km_per_ride": round(total_km / total_rides, 2) if total_rides else 0,
            "avg_calories_per_ride": int(total_calories / total_rides) if total_rides else 0
        },
        "athletes_by_level": level_counts,
        "system": {
            "database_size_bytes": db_size,
            "database_size_mb": round(db_size / (1024 * 1024), 2),
            "last_updated": now.isoformat()
        }
    }

@router.get("/analytics/speed-data")
async def speed_analytics(limit: int = Query(10, ge=1, le=50)):
    from ..db.database import get_all_rides
    rides = get_all_rides()
    recent = rides[-limit:] if len(rides) > limit else rides
    return {
        "labels": [r.get("date", "Ride")[-10:] if r.get("date") else "Ride" for r in recent],
        "speeds": [r.get("avg_speed_kmh", 0) for r in recent],
        "distances": [r.get("distance_km", 0) for r in recent]
    }

@router.get("/maps/places/nearby")
async def nearby_places(ride_id: int, query: str = Query(..., description="e.g.: cafe, bakery, restaurant")):
    from ..db.database import get_ride as _get_ride
    from ..config import SERPAPI_API_KEY
    ride = _get_ride(ride_id)
    if not ride: raise HTTPException(status_code=404, detail="Ride not found")
    gps_points = ride.get("gps_points")
    if not gps_points: raise HTTPException(status_code=400, detail="No GPS points for this ride")
    if not SERPAPI_API_KEY: raise HTTPException(status_code=500, detail="SERPAPI_API_KEY not configured")
    points = [GPSPoint(**p) for p in gps_points]
    results = get_local_results(points, query=query)
    if results is None: raise HTTPException(status_code=502, detail="SerpApi request failed")
    return {"query": query, "count": len(results), "results": results}

@router.get("/maps/places/search")
async def search_places_endpoint(ride_id: int, query: str = Query(..., description="Place search query")):
    from ..db.database import get_ride as _get_ride
    from ..config import SERPAPI_API_KEY
    ride = _get_ride(ride_id)
    if not ride: raise HTTPException(status_code=404, detail="Ride not found")
    gps_points = ride.get("gps_points")
    if not gps_points: raise HTTPException(status_code=400, detail="No GPS points for this ride")
    if not SERPAPI_API_KEY: raise HTTPException(status_code=500, detail="SERPAPI_API_KEY not configured")
    points = [GPSPoint(**p) for p in gps_points]
    data = search_nearby(points, query=query)
    if data is None: raise HTTPException(status_code=502, detail="SerpApi request failed")
    return data

@router.post("/calendar/events")
async def create_calendar_event(event_data: CalendarEventCreate, current_user: dict = Depends(get_current_user_dependency)):
    from ..db.database import save_calendar_event, get_calendar_event
    from ..utils.dates import date_only
    event_data_dict = event_data.model_dump()
    event_data_dict["date"] = date_only(event_data_dict.get("date"))
    event_id = save_calendar_event(event_data_dict)
    event = get_calendar_event(int(event_id))
    return event

@router.get("/calendar/events")
async def list_calendar_events(athlete_id: int = Query(...), year: int = Query(...), month: int = Query(...)):
    from ..db.database import get_events_by_month
    events = get_events_by_month(athlete_id, year, month)
    return {"events": events}

@router.get("/calendar/events/range")
async def list_events_by_range(athlete_id: int = Query(...), start: str = Query(...), end: str = Query(...)):
    from ..db.database import get_events_by_date_range
    events = get_events_by_date_range(athlete_id, start, end)
    return {"events": events}

@router.get("/calendar/events/{event_id}")
async def get_calendar_event_endpoint(event_id: int, current_user: dict = Depends(get_current_user_dependency)):
    from ..db.database import get_calendar_event
    event = get_calendar_event(event_id)
    if not event: raise HTTPException(status_code=404, detail="Event not found")
    return event

@router.put("/calendar/events/{event_id}")
async def update_calendar_event_endpoint(event_id: int, event_data: CalendarEventUpdate, current_user: dict = Depends(get_current_user_dependency)):
    from ..db.database import update_calendar_event
    from ..utils.dates import date_only
    update_dict = event_data.model_dump(exclude_none=True)
    if update_dict.get("date"):
        update_dict["date"] = date_only(update_dict.get("date"))
    ok = update_calendar_event(event_id, update_dict)
    if not ok: raise HTTPException(status_code=404, detail="Event not found")
    from ..db.database import get_calendar_event
    return get_calendar_event(event_id)

@router.delete("/calendar/events/{event_id}")
async def delete_calendar_event_endpoint(event_id: int, current_user: dict = Depends(get_current_user_dependency)):
    from ..db.database import delete_calendar_event
    ok = delete_calendar_event(event_id)
    if not ok: raise HTTPException(status_code=404, detail="Event not found")
    return {"deleted": True}

@router.post("/calendar/events/{event_id}/complete")
async def toggle_event_complete(event_id: int, current_user: dict = Depends(get_current_user_dependency)):
    from ..db.database import get_calendar_event, update_calendar_event
    event = get_calendar_event(event_id)
    if not event: raise HTTPException(status_code=404, detail="Event not found")
    update_calendar_event(event_id, {"completed": not event["completed"]})
    return get_calendar_event(event_id)


@router.get("/training/load")
async def get_training_load(athlete_id: int = Query(...), days: int = Query(30, ge=1, le=90), current_user: Optional[dict] = Depends(get_optional_current_user)):
    """Get ATL/CTL/TSB training load metrics for athlete."""
    from ..db.database import get_rides_by_athlete
    from ..analytics.training_load import calculate_atl_ctl_tsb, TrainingLoadDay
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id)]
    loads = calculate_atl_ctl_tsb(rides)
    recent = loads[-days:] if len(loads) > days else loads
    return {"athlete_id": athlete_id, "days": days, "training_loads": [l for l in recent]}


@router.get("/training/status")
async def get_training_status(athlete_id: int = Query(...), current_user: Optional[dict] = Depends(get_optional_current_user)):
    """Get current fitness status with ATL/CTL/TSB recommendation."""
    from ..db.database import get_rides_by_athlete
    from ..analytics.training_load import get_current_training_status
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id)]
    status = get_current_training_status(rides)
    return {"athlete_id": athlete_id, **status}


@router.get("/training/summary")
async def get_7day_summary(athlete_id: int = Query(...), current_user: dict = Depends(get_current_user_dependency)):
    """Get 7-day fitness summary for dashboard."""
    from ..db.database import get_rides_by_athlete
    from ..analytics.training_load import get_7day_fitness_summary
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id)]
    summary = get_7day_fitness_summary(rides)
    return {"athlete_id": athlete_id, "summary": summary}


@router.post("/training/goals")
async def create_training_goal(goal_data: dict, current_user: dict = Depends(get_current_user_dependency)):
    """Create a training goal for an athlete."""
    from ..db.postgres_db import save_training_goal, SQLALCHEMY_AVAILABLE
    if not SQLALCHEMY_AVAILABLE:
        raise HTTPException(status_code=500, detail="SQLAlchemy not available")
    from datetime import datetime
    goal = {
        "athlete_id": goal_data.get("athlete_id"),
        "title": goal_data.get("title", ""),
        "description": goal_data.get("description"),
        "goal_type": goal_data.get("goal_type", "granfondo"),
        "target_date": goal_data.get("target_date"),
        "target_distance_km": goal_data.get("target_distance_km"),
        "target_elevation_m": goal_data.get("target_elevation_m"),
        "status": "active"
    }
    goal_id = save_training_goal(goal["athlete_id"], goal)
    return {"id": goal_id, **goal}


@router.get("/training/goals")
async def list_training_goals(athlete_id: int = Query(...), status: str = Query(None), current_user: dict = Depends(get_current_user_dependency)):
    """List training goals for athlete."""
    from ..db.postgres_db import get_training_goals, SQLALCHEMY_AVAILABLE
    if not SQLALCHEMY_AVAILABLE:
        raise HTTPException(status_code=500, detail="SQLAlchemy not available")
    goals = get_training_goals(athlete_id, status)
    return {"goals": goals}


@router.post("/training/workouts/generate")
async def generate_workouts(goal_id: int = Body(...), event_count: int = Body(12, ge=4, le=20)):
    """Generate planned workouts for a granfondo goal."""
    from ..db.postgres_db import get_session, PlannedWorkoutModel, TrainingGoalModel
    from datetime import datetime, timedelta
    from ..analytics.training_load import get_current_training_status
    from ..db.database import get_rides_by_athlete
    from ..models.models import Ride
    
    with get_session() as session:
        goal = session.query(TrainingGoalModel).filter(TrainingGoalModel.id == goal_id).first()
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        rides = [Ride(**r) for r in get_rides_by_athlete(goal.athlete_id)]
        current_status = get_current_training_status(rides) if rides else {"ctl": 0}
        
        workouts_to_create = []
        start_date = datetime.now()
        
        workout_plan = [
            ("Base aerobica", "endurance", 0.5),
            ("Progressivo", "endurance", 0.6),
            ("Base aerobica", "endurance", 0.5),
            ("Thresholds", "threshold", 0.75),
            ("Recupero", "recovery", 0.4),
            ("Base aerobica", "endurance", 0.55),
            ("Progressivo", "sweetspot", 0.8),
            ("Recupero", "recovery", 0.45),
            ("Thresholds", "threshold", 0.75),
            ("Base aerobica", "endurance", 0.5),
            ("Pre-gara", "openers", 0.65),
            ("Giorno gara", "race", 0.9),
        ]
        
        for i in range(min(event_count, len(workout_plan))):
            workout_date = (start_date + timedelta(days=7 * i)).strftime("%Y-%m-%d")
            title, wtype, intensity = workout_plan[i]
            workouts_to_create.append(PlannedWorkoutModel(
                athlete_id=goal.athlete_id,
                goal_id=goal_id,
                date=workout_date,
                title=title,
                workout_type=wtype,
                duration_minutes=90,
                target_intensity=intensity
            ))
        
        session.add_all(workouts_to_create)
        return {"generated": len(workouts_to_create), "goal_id": goal_id}

@router.get("/weather")
async def get_weather(lat: float = Query(..., description="Latitude"), lon: float = Query(..., description="Longitude"), date: Optional[str] = Query(None, description="Date (YYYY-MM-DD) or today")):
    """Get weather for coordinates, optionally for a specific date."""
    from ..weather.weather_service import get_weather_for_coordinates, get_forecast_for_date, get_weather_score
    from ..config import WEATHER_API_KEY
    
    if not WEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="WEATHER_API_KEY not configured in .env file")
    
    if date:
        weather = get_forecast_for_date(lat, lon, date)
    else:
        weather = get_weather_for_coordinates(lat, lon)
    
    if "error" in weather:
        raise HTTPException(status_code=502, detail=weather["error"])
    
    temp = weather.get("temperature")
    humidity = weather.get("humidity")
    
    score, advice = get_weather_score(temp, humidity) if temp is not None and humidity is not None else (5, "Weather data not available")
    
    weather["score"] = score
    weather["advice"] = advice
    
    return weather

@router.get("/weather/forecast")
async def get_weather_forecast(lat: float = Query(..., description="Latitudine"), lon: float = Query(..., description="Longitudine"), days: int = Query(7, ge=1, le=5)):
    """Get multi-day weather forecast."""
    from ..weather.weather_service import get_forecast_for_date, get_weather_score
    from ..config import WEATHER_API_KEY
    from datetime import datetime, timedelta
    
    if not WEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="WEATHER_API_KEY not configured in .env file")
    
    forecasts = []
    today = datetime.now()
    
    for i in range(days):
        date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        weather = get_forecast_for_date(lat, lon, date)
        if "error" not in weather:
            temp = weather.get("temperature")
            humidity = weather.get("humidity")
            score, advice = get_weather_score(temp, humidity) if temp and humidity else (5, "")
            weather["score"] = score
            weather["advice"] = advice
            weather["date"] = date
        forecasts.append(weather)
    
    return {"forecasts": forecasts}


@router.get("/heatmap")
async def get_heatmap(athlete_id: int = Query(0), current_user: Optional[dict] = Depends(get_optional_current_user)):
    """Get heatmap data from all GPS points for an athlete."""
    from ..db.database import get_rides_by_athlete, get_all_rides
    rides = [Ride(**r) for r in (get_rides_by_athlete(athlete_id) if athlete_id else get_all_rides())]
    rides_dict = [r.to_dict() for r in rides]
    data = get_heatmap_points(rides_dict)
    return data


@router.get("/badges")
async def get_badges(athlete_id: int = Query(...), current_user: Optional[dict] = Depends(get_optional_current_user)):
    """Get badge achievements for an athlete."""
    from ..db.database import get_rides_by_athlete, get_athlete
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id)]
    athlete = get_athlete(athlete_id)
    badges = calculate_badges(athlete_id, [r.to_dict() for r in rides], athlete)
    achieved_count = sum(1 for b in badges if b["achieved"])
    return {"athlete_id": athlete_id, "badges": badges, "total_badges": len(badges), "achieved": achieved_count}


@router.post("/training/granfondo/plan")
async def generate_granfondo_workouts(request: GranfondoPlanRequest):
    """Generate granfondo training plan with tapering."""
    start_date = request.start_date
    weeks = request.target_weeks
    plan = generate_granfondo_plan(start_date, weeks)
    return {"athlete_id": request.athlete_id, "start_date": start_date, "weeks": weeks, "plan": plan, "total_workouts": len(plan)}
