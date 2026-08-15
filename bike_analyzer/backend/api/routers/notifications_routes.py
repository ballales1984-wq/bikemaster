"""Notifications API routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from ..routes import _ensure_athlete_access, get_current_user
from ..schemas import NotificationContextIn, NotificationListOut, NotificationOut, NotificationScoreOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _to_notification_dict(n) -> dict:
    """Convert a notification model to a serializable dict."""
    return {
        "id": n.id,
        "category": n.category,
        "channel": n.channel,
        "title": n.title,
        "message": n.message,
        "tts_text": n.tts_text,
        "score": n.score,
        "priority": n.priority,
        "language": n.language,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("", response_model=NotificationListOut)
async def list_notifications(
    request: Request,
    athlete_id: int = 0,
    category: str | None = Query(default=None, description="Filter by category"),
    current_user: dict = Depends(get_current_user),
):
    """Evaluate pending notifications for the athlete."""
    from ...analytics.proactive import (
        NotificationCategory,
        NotificationContext,
        NotificationPreferences,
        NotificationRouter,
    )

    resolved_id = athlete_id if athlete_id else current_user["id"]
    if resolved_id:
        _ensure_athlete_access(resolved_id, current_user)

    prefs = NotificationPreferences()
    router_notif = NotificationRouter(prefs)

    intensity_zone = None
    try:
        z = int(request.query_params.get("intensity_zone", ""))
        if 0 <= z <= 5:
            intensity_zone = z
    except (TypeError, ValueError):
        pass

    plan: dict = {}
    if request.query_params.get("planned_today") == "1":
        plan["planned_today"] = True
    if request.query_params.get("goal_active") == "1":
        plan["goal_active"] = True

    athlete_state: dict = {}
    try:
        tsb = float(request.query_params.get("tsb", ""))
        athlete_state["tsb"] = tsb
    except (TypeError, ValueError):
        pass

    context = NotificationContext(
        athlete_state=athlete_state,
        plan=plan or None,
        intensity_zone=intensity_zone,
    )

    candidates = [
        (
            NotificationCategory.SAFETY.value,
            "stopped",
            {"minutes": int(request.query_params.get("stopped_min", 0)) or 10},
            {"stopped_minutes": int(request.query_params.get("stopped_min", 0)) or 10},
        ),
        (
            NotificationCategory.RECOVERY.value,
            "intense_yesterday",
            {},
            {"insufficient_recovery": (athlete_state.get("tsb", 0) < -15)},
        ),
        (
            NotificationCategory.TRAINING.value,
            "weather_changed",
            {"plan": "2 ore di fondo"},
            {"plan_changed": bool(request.query_params.get("weather_changed") == "1")},
        ),
        (
            NotificationCategory.GOAL.value,
            "granfondo_countdown",
            {"n": int(request.query_params.get("rides_left", 0)) or 3},
            {},
        ),
    ]

    notifications: list = []
    for cat, key, variables, signals in candidates:
        if category and cat != category:
            continue
        n = router_notif.route(
            context,
            cat,
            key,
            variables,
            signals=signals,
        )
        if n is not None:
            notifications.append(n)

    batched = NotificationRouter.batch(notifications, prefs.language) if notifications else None
    out = [batched] if batched else []
    return NotificationListOut(
        notifications=[NotificationOut(**_to_notification_dict(n)) for n in out],
        meta={"candidate_count": len(candidates), "language": prefs.language},
    )


@router.post("/preferences")
async def update_notification_preferences(
    prefs: Any,
    athlete_id: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """Persist athlete notification preferences."""
    from ...analytics.proactive import NotificationPreferences as PrefModel

    resolved_id = athlete_id if athlete_id else current_user["id"]
    if resolved_id:
        _ensure_athlete_access(resolved_id, current_user)

    normalized = PrefModel.from_dict(prefs.model_dump())
    return {
        "athlete_id": resolved_id,
        "preferences": normalized.__dict__,
        "message": "Notification preferences saved.",
    }


@router.post("/evaluate", response_model=NotificationScoreOut)
async def evaluate_notification(
    payload: NotificationContextIn,
    category: str = Query("training"),
    current_user: dict = Depends(get_current_user),
):
    """Evaluate a single candidate notification and return its score."""
    from ...analytics.proactive import (
        ContextEvaluator,
        NotificationContext,
        NotificationPreferences,
    )

    now = None
    if payload.now:
        try:
            now = datetime.fromisoformat(payload.now.replace("Z", "+00:00"))
        except ValueError:
            now = None
    context = NotificationContext(
        athlete_state=payload.athlete_state or {},
        plan=payload.plan,
        current_ride=payload.current_ride,
        weather=payload.weather,
        intensity_zone=payload.intensity_zone,
        now=now or datetime.now(UTC),
    )
    prefs = NotificationPreferences()
    score = ContextEvaluator.evaluate(context, category=category)
    return NotificationScoreOut(
        urgency=score.urgency,
        relevance=score.relevance,
        timeliness=score.timeliness,
        score=score.score,
        should_notify=score.should_notify and not prefs.paused,
        reasons=score.reasons,
    )
