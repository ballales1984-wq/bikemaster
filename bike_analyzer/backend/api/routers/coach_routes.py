"""Coach AI API routes."""

from __future__ import annotations

import contextlib

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from ...rate_limiter import limiter
from ..routes import (
    _athlete_profile_data,
    _ensure_athlete_access,
    _ensure_ride_access,
    _current_athlete_id,
    _public_athlete,
    get_current_user,
    logger,
)
from ..schemas import CoachChatRequest
from ...models.models import AthleteProfile, Ride

router = APIRouter(prefix="/coach", tags=["coach"])


@router.get("/history")
async def coach_chat_history(athlete_id: int = Query(...), current_user: dict = Depends(get_current_user)):
    """Retrieve AI coach chat history for an athlete."""
    from ...db.database import get_chat_history

    _ensure_athlete_access(athlete_id, current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    history = get_chat_history(athlete_id, tenant_id=tenant_id)
    return {"athlete_id": athlete_id, "history": history}


@router.get("/workout")
@limiter.limit("10/minute")
async def workout_recommendations(
    request: Request,
    athlete_id: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """Get AI-generated workout recommendations for an athlete."""
    from ...analytics.ai_coach import generate_workout_recommendations
    from ...db.database import get_athlete, get_rides_by_athlete

    try:
        resolved_id = athlete_id if athlete_id else current_user["id"]
        _ensure_athlete_access(resolved_id, current_user)
        rides = [Ride(**r) for r in get_rides_by_athlete(resolved_id)]
        athlete_data = get_athlete(resolved_id)
        if athlete_data:
            athlete_data = _public_athlete(athlete_data)
        athlete = AthleteProfile(**_athlete_profile_data(athlete_data)) if athlete_data else AthleteProfile()
        result = generate_workout_recommendations(athlete, rides)
        return {"recommendations": result}
    except HTTPException:
        raise
    except Exception:
        logger.exception("AI Coach error in workout recommendations")
        return {"recommendations": "AI Coach error. Please try again later."}


@router.get("/full")
@limiter.limit("5/minute")
async def coach_full_data(
    request: Request,
    athlete_id: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """Generate a full AI coach report (training, recovery, historical analysis).

    The report includes training advice, recovery advice, historical
    trends, training scores, and recovery scores. Rate limited.
    """
    from ...analytics.ai_coach import ai_coach_full
    from ...db.database import (
        get_athlete,
        get_rides_by_athlete,
        save_chat_message,
    )

    try:
        resolved_id = athlete_id
        if athlete_id:
            _ensure_athlete_access(athlete_id, current_user)
        if not resolved_id:
            resolved_id = current_user["id"]
        if not resolved_id:
            profile_message = "Create an athlete profile in the Dashboard to receive personalized recommendations."
            return {
                "training_advice": profile_message,
                "recovery_advice": profile_message,
                "historical_analysis": "",
                "training_scores": [],
                "recovery_scores": [],
                "charts": [],
            }
        rides = [Ride(**r) for r in get_rides_by_athlete(resolved_id)]
        athlete_data = get_athlete(resolved_id)
        if not athlete_data:
            return {
                "training_advice": "Athlete not found. Create a profile in the Dashboard.",
                "recovery_advice": "Athlete not found. Create a profile in the Dashboard.",
                "historical_analysis": "",
                "training_scores": [],
                "recovery_scores": [],
                "charts": [],
            }
        athlete_data = {k: v for k, v in athlete_data.items() if k != "password_hash"}
        athlete = AthleteProfile(**_athlete_profile_data(athlete_data))
        result = ai_coach_full(athlete, rides, resolved_id)
        if athlete_id and result.get("training_advice"):
            tenant_id = current_user.get("tenant_id", resolved_id)
            save_chat_message(resolved_id, "assistant", result["training_advice"][:500], tenant_id)
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("AI Coach error in full report")
        return {
            "training_advice": "AI Coach error. Please try again later.",
            "recovery_advice": "AI Coach error. Please try again later.",
            "historical_analysis": "",
            "training_scores": [],
            "recovery_scores": [],
            "charts": [],
        }


@router.get("/page", response_class=HTMLResponse)
async def coach_page():
    """Serve the AI Coach static HTML page."""
    from pathlib import Path

    page = Path(__file__).parent.parent / "static" / "ai_coach.html"
    if page.exists():
        return page.read_text(encoding="utf-8")
    return HTMLResponse("<h1>AI Coach page not available</h1>", status_code=404)


@router.get("/recovery")
async def recovery_recommendations(
    fatigue_score: float = 5.0,
    ride_id: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """Get AI recovery recommendations based on fatigue and recent rides."""
    from ...analytics.ai_coach import generate_recovery_recommendations
    from ...db.database import get_athlete, get_ride, get_rides_by_athlete

    try:
        ride_obj = None
        athlete_data = None
        if ride_id:
            ride_data = get_ride(ride_id)
            if ride_data:
                _ensure_ride_access(ride_data, current_user)
                ride_obj = Ride(**ride_data)
                athlete_data = get_athlete(ride_data.get("athlete_id"))
        elif current_user:
            tenant_id = current_user.get("tenant_id", current_user["id"])
            rides = get_rides_by_athlete(_current_athlete_id(current_user), tenant_id)
            if rides:
                athlete_data = get_athlete(current_user["id"], tenant_id)
        if athlete_data:
            athlete_data = {k: v for k, v in athlete_data.items() if k != "password_hash"}
        athlete = AthleteProfile(**_athlete_profile_data(athlete_data)) if athlete_data else AthleteProfile()
        result = generate_recovery_recommendations(athlete, [ride_obj] if ride_obj else [], fatigue_score)
        return {"recommendations": result}
    except HTTPException:
        raise
    except Exception:
        logger.exception("AI Coach error in recovery recommendations")
        return {"recommendations": "AI Coach error. Please try again later."}


@router.get("/trends")
async def historical_trends(current_user: dict = Depends(get_current_user)):
    """Analyze historical training trends for the athlete."""
    from ...analytics.ai_coach import analyze_historical_trends
    from ...db.database import get_rides_by_athlete

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [Ride(**r) for r in get_rides_by_athlete(_current_athlete_id(current_user), tenant_id)]
    return analyze_historical_trends(rides)


@router.post("/chat")
async def coach_chat_post(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Send a message to the AI coach via POST (JSON body)."""

    body = await request.json()
    chat_req = CoachChatRequest(**body)
    athlete_id = chat_req.athlete_id or current_user["id"]
    return await _process_chat(athlete_id, chat_req.message, current_user)


async def _process_chat(athlete_id: int, message: str, current_user: dict):
    """Gestisce la chat con l'AI coach: salva messaggi, genera consigli e restituisce la storia."""
    from ...analytics.ai_coach import generate_training_advice
    from ...db.database import (
        get_athlete,
        get_chat_history,
        get_rides_by_athlete,
        save_athlete,
        save_chat_message,
    )

    tenant_id = current_user.get("tenant_id", athlete_id)
    _ensure_athlete_access(athlete_id, current_user)

    if get_athlete(athlete_id) is None:
        save_athlete(
            {
                "name": current_user.get("name") or f"Athlete {athlete_id}",
                "email": current_user.get("email"),
                "picture": current_user.get("picture"),
                "experience_level": "Beginner",
                "tenant_id": tenant_id,
            },
            athlete_id=athlete_id,
            tenant_id=tenant_id,
        )

    save_chat_message(athlete_id, "user", message[:500], tenant_id)
    athlete_data = get_athlete(athlete_id, tenant_id)
    if athlete_data:
        athlete_data = {k: v for k, v in athlete_data.items() if k != "password_hash"}
    athlete = AthleteProfile(**_athlete_profile_data(athlete_data)) if athlete_data else AthleteProfile()
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id, tenant_id=tenant_id)]
    response = generate_training_advice(athlete, rides, athlete_id)
    save_chat_message(athlete_id, "assistant", response[:500], tenant_id)
    return {"response": response, "history": get_chat_history(athlete_id, tenant_id=tenant_id)}


@router.post("/chat/bm2")
async def coach_chat_bm2(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """AI Coach chat with BM2 physics engine integration.

    Combines the AI coach's training advice with BM2 simulation
    and power validation results for a comprehensive analysis.
    """
    from bike_analyzer.bm2.orchestrator import AIOrchestrator
    from bike_analyzer.core.physics import RiderBikeParams, validate_ride_power

    from ...analytics.ai_coach import generate_training_advice
    from ...db.database import get_athlete, get_chat_history, get_rides_by_athlete, save_chat_message
    from ...models.models import AthleteProfile, Ride

    body = await request.json()
    chat_req = CoachChatRequest(**body)
    athlete_id = chat_req.athlete_id or current_user["id"]
    tenant_id = current_user.get("tenant_id", athlete_id)
    _ensure_athlete_access(athlete_id, current_user)

    athlete_data = get_athlete(athlete_id, tenant_id)
    if athlete_data:
        athlete_data = {k: v for k, v in athlete_data.items() if k != "password_hash"}
    athlete = AthleteProfile(**_athlete_profile_data(athlete_data)) if athlete_data else AthleteProfile()
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id, tenant_id=tenant_id)]
    coach_response = generate_training_advice(athlete, rides, athlete_id)

    message = chat_req.message

    def _save_chat(role, content):
        if athlete_data:
            with contextlib.suppress(Exception):
                save_chat_message(athlete_id, role, content[:500], tenant_id)

    _save_chat("user", message)
    response_text = coach_response
    bm2_result = None
    ride_id_match = None
    import re as _re
    ride_id_match = _re.search(r"ride\s*#?(\d+)|ride\s+(\d+)", message, _re.IGNORECASE)
    if ride_id_match:
        rid = int(ride_id_match.group(1) or ride_id_match.group(2))
        from ...db.database import get_ride as _get_ride
        from .bm2_routes import _to_gps
        ride_dict = _get_ride(rid)
        if ride_dict:
            try:
                gps = [_to_gps(p) for p in (ride_dict.get("gps_points") or [])]
                ride = Ride(**{k: v for k, v in ride_dict.items() if k in Ride.__dataclass_fields__})
                ride.gps_points = gps
                params = RiderBikeParams(
                    rider_mass_kg=float(athlete.weight_kg.value) if athlete.weight_kg else 75.0,
                    bike_mass_kg=8.0,
                    cda=0.40,
                    crr=0.005,
                    drivetrain_efficiency=0.97,
                )
                validation = validate_ride_power(ride, params)
                if validation:
                    bm2_result = {
                        "validation": validation.to_dict(),
                        "ride_id": rid,
                    }
            except Exception:
                pass

    if not bm2_result and any(kw in message.lower() for kw in ["energia", "power", "ftp", "performance", "calories", "kcal"]):
        try:
            orchestrator = AIOrchestrator()
            bm2_result = orchestrator.answer(message, {
                "athlete": {"weight": athlete.weight_kg.value if athlete.weight_kg else 75},
                "bike": {"weight": 8},
                "world": {"surface": "asphalt", "avg_slope": 4},
                "gps_points": [],
                "sensors": [],
            })
        except Exception:
            pass

    response_text = coach_response
    if bm2_result:
        response_text += "\n\n---\n**BM2 Physics Analysis:**\n"
        if "validation" in bm2_result:
            v = bm2_result["validation"]
            response_text += f"- MAE: {v['mae_w']:.1f}W | RMSE: {v['rmse_w']:.1f}W | R²: {v['r2']:.3f}\n"
        if "results" in bm2_result:
            for name, r in bm2_result["results"].items():
                response_text += f"- {name}: {r['value']:.1f} {r['unit']}\n"

    _save_chat("assistant", response_text)
    return {
        "response": response_text,
        "history": get_chat_history(athlete_id, tenant_id=tenant_id),
        "bm2_result": bm2_result,
    }
