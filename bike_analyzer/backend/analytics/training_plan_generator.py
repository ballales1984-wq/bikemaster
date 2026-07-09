"""Cycling training plan generator.

Produces periodic training plans that can be consumed by `GranfondoPlanner.vue`
and other scheduling surfaces. Currently supports:
- `generate_weekly_plan` — 7-day plan
- `generate_monthly_plan` — 4-week block plan

Each function first attempts an LLM-enhanced plan via the configured AI Coach
provider. If no provider is available or the call fails, it falls back to a
rule-based local generator.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from ..models.models import AthleteProfile, Ride
from ..settings import get_settings

_s = get_settings()


@dataclass
class WorkoutDay:
    date: str
    title: str
    workout_type: str
    duration_minutes: int
    target_zone: str
    description: str


def _weekday_name(date: datetime) -> str:
    return date.strftime("%A")


def _plan_summary(athlete: AthleteProfile, rides: list[Ride]) -> dict[str, Any]:
    total_rides = len(rides)
    recent = rides[-4:] if rides else []
    avg_distance = sum(r.distance_km for r in recent) / len(recent) if recent else 0
    avg_duration = sum(r.duration_minutes for r in recent) / len(recent) if recent else 0
    return {
        "total_rides": total_rides,
        "recent_rides": len(recent),
        "avg_distance_km": round(avg_distance, 1),
        "avg_duration_min": round(avg_duration, 1),
    }


def _local_weekly_plan(athlete: AthleteProfile, rides: list[Ride], start_date: datetime) -> list[WorkoutDay]:
    level = (athlete.experience_level or "beginner").lower()
    zone2 = 75 if level in ("beginner", "intermediate") else 90
    zone3 = int(zone2 * 0.7)
    zone4 = int(zone2 * 0.4)

    templates = [
        ("Endurance base", "endurance", zone2, "Z2", "Ritmo facile, conversazione libera"),
        ("Threshold", "threshold", zone3, "Z3", "Soglia controllata"),
        ("Recovery spin", "recovery", 40, "Z1-Z2", "Pedalata molto leggera"),
        ("Endurance base", "endurance", zone2, "Z2", "Ritmo facile, conversazione libera"),
        ("VO2max intervals", "intervals", zone4, "Z5", "Sforzo massimo breve"),
        ("Long ride", "endurance", int(zone2 * 1.4), "Z2-Z3", "Uscita lunga di fondo"),
        ("Recovery spin", "recovery", 40, "Z1-Z2", "Pedalata molto leggera"),
    ]

    plan: list[WorkoutDay] = []
    for i in range(7):
        day = start_date + timedelta(days=i)
        title, wtype, duration, zone, desc = templates[i]
        plan.append(
            WorkoutDay(
                date=day.strftime("%Y-%m-%d"),
                title=title,
                workout_type=wtype,
                duration_minutes=duration,
                target_zone=zone,
                description=desc,
            )
        )
    return plan


def _local_monthly_plan(athlete: AthleteProfile, rides: list[Ride], start_date: datetime) -> list[WorkoutDay]:
    phase = "build"
    if len(rides) < 10:
        phase = "base"
    elif any((r.duration_minutes or 0) > 180 for r in rides[-5:]):
        phase = "peak"

    templates = {
        "base": [
            ("Endurance base", "endurance", 75, "Z2", "Costruisci fondo aerobico"),
            ("Endurance base", "endurance", 75, "Z2", "Costruisci fondo aerobico"),
            ("Recovery spin", "recovery", 45, "Z1-Z2", "Pedalata leggera"),
            ("Endurance base", "endurance", 75, "Z2", "Costruisci fondo aerobico"),
            ("Sweet spot", "threshold", 60, "Z3", "Soglia controllata"),
        ],
        "build": [
            ("Threshold", "threshold", 60, "Z3", "Sviluppa soglia"),
            ("Endurance base", "endurance", 90, "Z2", "Fondo lento"),
            ("Recovery spin", "recovery", 45, "Z1-Z2", "Recupero attivo"),
            ("VO2max intervals", "intervals", 50, "Z5", "Picchi di potenza"),
            ("Long ride", "endurance", 120, "Z2-Z3", "Uscita lunga"),
        ],
        "peak": [
            ("Race prep", "intervals", 45, "Z4-Z5", "Intensita gara"),
            ("Endurance base", "endurance", 60, "Z2", "Mantieni fondo"),
            ("Recovery spin", "recovery", 45, "Z1-Z2", "Recupero attivo"),
            ("Threshold", "threshold", 50, "Z3", "Soglia"),
            ("Long ride", "endurance", 150, "Z2-Z3", "Uscita lunga"),
        ],
    }
    weekly_templates = templates.get(phase, templates["base"])

    plan: list[WorkoutDay] = []
    for week in range(4):
        for day_offset in range(5):
            day = start_date + timedelta(days=week * 7 + day_offset)
            title, wtype, duration, zone, desc = weekly_templates[day_offset]
            plan.append(
                WorkoutDay(
                    date=day.strftime("%Y-%m-%d"),
                    title=title,
                    workout_type=wtype,
                    duration_minutes=duration,
                    target_zone=zone,
                    description=desc,
                )
            )
    return plan


def _llm_plan_prompt(athlete: AthleteProfile, rides: list[Ride], plan_type: str, start_date: datetime) -> str:
    summary = _plan_summary(athlete, rides)
    recent = rides[-3:]
    if recent:
        parts = [f"{r.date}: {r.distance_km:.1f}km/{r.duration_minutes:.0f}min" for r in recent]
        recent_info = "; ".join(parts)
    else:
        recent_info = "nessuna"
    end_date = (
        start_date + timedelta(days=7)
        if plan_type == "weekly"
        else start_date + timedelta(days=28)
    )

    return f"""Sei un coach ciclistico esperto. Genera un piano di allenamento {plan_type} personalizzato.

Profilo atleta:
- Nome: {athlete.name}
- Livello: {athlete.experience_level}
- FTP: {athlete.ftp_watts or 250}W
- Peso: {athlete.weight_kg} kg
- Volume settimanale: {athlete.weekly_volume_km:.0f} km
- Terreno: {athlete.preferred_terrain or 'non specificato'}
- Obiettivi: {athlete.goals or 'non specificati'}

Dati:
- Uscite archiviate: {summary['total_rides']}
- Media recente (ultime 4): {summary['avg_distance_km']}km / {summary['avg_duration_min']}min
- Ultime uscite: {recent_info}
- Periodo: {start_date.strftime('%Y-%m-%d')} -> {end_date.strftime('%Y-%m-%d')}

REGOLE:
- Rispondi in italiano
- Restituisci ESCLUSIVAMENTE JSON valido, senza testo aggiuntivo
- Struttura:
  {{
    "plan_name": "Piano {plan_type}",
    "start_date": "{start_date.strftime('%Y-%m-%d')}",
    "end_date": "{end_date.strftime('%Y-%m-%d')}",
    "days": [
      {{
        "date": "YYYY-MM-DD",
        "title": "...",
        "workout_type": "...",
        "duration_minutes": 60,
        "target_zone": "Z2",
        "description": "..."
      }}
    ],
    "summary": "Frase breve di spiegazione"
  }}
- Includi 1-2 giorni di recupero ogni 7 giorni
- Non usare emoji
- Non usare backtick o codice markdown
- Non aggiungere saluti o chiusure
"""


def _try_llm_plan(
    athlete: AthleteProfile,
    rides: list[Ride],
    plan_type: str,
    start_date: datetime,
) -> dict[str, Any] | None:
    try:
        from ..analytics.ai_coach import _chat_completion_text, _clean_ai_output, get_ai_coach_client
        client, provider = get_ai_coach_client()
        model = _s.groq_model
        prompt = _llm_plan_prompt(athlete, rides, plan_type, start_date)
        raw = _chat_completion_text(client, model, prompt, max_tokens=1200)
        cleaned = _clean_ai_output(raw)
        import json
        import re

        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group(0))
        if "days" in data and isinstance(data["days"], list):
            return data
        return None
    except Exception:
        return None


def generate_weekly_plan(
    athlete: AthleteProfile,
    rides: list[Ride] | None = None,
    start_date: str | None = None,
) -> dict[str, Any]:
    """Generate a 7-day training plan.

    Tries LLM first when AI_COACH_MODE is not local/offline/fallback,
    then falls back to rule-based local generator.
    """
    rides = rides or []
    start = datetime.fromisoformat(start_date) if start_date else datetime.now(UTC)
    env_mode = (_s.ai_coach_mode or "").strip().lower()
    if env_mode not in {"local", "offline", "fallback"}:
        llm = _try_llm_plan(athlete, rides, "settimanale", start)
        if llm:
            return llm

    days = _local_weekly_plan(athlete, rides, start)
    return {
        "plan_name": "Piano settimanale",
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": (start + timedelta(days=7)).strftime("%Y-%m-%d"),
        "days": [
            {
                "date": d.date,
                "title": d.title,
                "workout_type": d.workout_type,
                "duration_minutes": d.duration_minutes,
                "target_zone": d.target_zone,
                "description": d.description,
            }
            for d in days
        ],
        "summary": f"Piano generato per {athlete.experience_level} su FTP {athlete.ftp_watts or 250}W",
    }


def generate_monthly_plan(
    athlete: AthleteProfile,
    rides: list[Ride] | None = None,
    start_date: str | None = None,
) -> dict[str, Any]:
    """Generate a 4-week training plan block.

    Tries LLM first when AI_COACH_MODE is not local/offline/fallback,
    then falls back to rule-based local generator.
    """
    rides = rides or []
    start = datetime.fromisoformat(start_date) if start_date else datetime.now(UTC)
    env_mode = (_s.ai_coach_mode or "").strip().lower()
    if env_mode not in {"local", "offline", "fallback"}:
        llm = _try_llm_plan(athlete, rides, "mensile", start)
        if llm:
            return llm

    days = _local_monthly_plan(athlete, rides, start)
    return {
        "plan_name": "Piano mensile",
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": (start + timedelta(days=28)).strftime("%Y-%m-%d"),
        "days": [
            {
                "date": d.date,
                "title": d.title,
                "workout_type": d.workout_type,
                "duration_minutes": d.duration_minutes,
                "target_zone": d.target_zone,
                "description": d.description,
            }
            for d in days
        ],
        "summary": f"Blocco 4 settimane per {athlete.experience_level} su FTP {athlete.ftp_watts or 250}W",
    }


__all__ = [
    "WorkoutDay",
    "generate_weekly_plan",
    "generate_monthly_plan",
]
