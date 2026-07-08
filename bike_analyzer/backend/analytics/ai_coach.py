"""AI Coach with cycling knowledge base RAG and athlete memory."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
from datetime import UTC

from ..config import (
    AI_COACH_MODE,
    GROQ_API_KEY,
    GROQ_MODEL,
    OLLAMA_API_KEY,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)
from ..models.models import AthleteProfile, Ride
from .analytics import calculate_summary, create_duration_chart, create_speed_chart
from .knowledge_base import format_context_for_llm, search_knowledge_base
from .performance import calculate_performance_score, calculate_recovery_score

logger = logging.getLogger(__name__)

LOCALE: str = os.getenv("LOCALE", "it")
_LANG_PROMPT = {
    "it": "Rispondi in italiano",
    "en": "Respond in English",
    "es": "Responde en español",
    "fr": "Réponds en français",
}
_LANG_INSTRUCTION = _LANG_PROMPT.get(LOCALE, _LANG_PROMPT["it"])
_LOCAL_COACH_MODES = {"local", "offline", "fallback"}
_BANNED_PROVIDERS: set[str] = set()

_current_client: object | None = None
_current_provider: str | None = None

_fmt_clean_pattern = re.compile(r"(?<!\d)(\d+\.\d)0(?!\d)")
_fmt_int_pattern = re.compile(r"(?<!\d)(\d+)\.0(?!\d)")


def _clean_ai_output(text: str) -> str:
    text = _fmt_int_pattern.sub(lambda m: m.group(1), text)
    text = _fmt_clean_pattern.sub(lambda m: m.group(1), text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def _coach_mode() -> str:
    env_mode = os.getenv("AI_COACH_MODE")
    return (env_mode if env_mode else AI_COACH_MODE).strip().lower()


def _provider_order() -> list[str]:
    configured = os.getenv("AI_COACH_PROVIDER_ORDER", "").strip().lower()
    if configured:
        providers = [p.strip() for p in configured.split(",") if p.strip()]
        if providers:
            return providers
    return ["ollama", "groq", "openai"]


def _ban_provider(provider: str, reason: str = "error") -> None:
    _BANNED_PROVIDERS.add(provider)
    global _current_client, _current_provider
    if _current_provider == provider:
        _current_client = None
        _current_provider = None
    logger.warning("AI Coach: provider '%s' banned due to %s, falling back", provider, reason)


def _is_recoverable_provider_error(error: Exception) -> bool:
    msg = str(error).lower()
    return not (isinstance(error, (ValueError, TypeError)) or "auth" in msg)


def get_ai_coach_client():
    global _current_client, _current_provider
    if _current_client and _current_provider and _current_provider not in _BANNED_PROVIDERS:
        return _current_client, _current_provider

    groq_key = os.getenv("GROQ_API_KEY", "").strip() or (GROQ_API_KEY or "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip() or (OPENAI_API_KEY or "").strip()
    ollama_key = os.getenv("OLLAMA_API_KEY", "ollama").strip() or (OLLAMA_API_KEY or "ollama").strip()
    ollama_url = (
        os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").strip()
        or (OLLAMA_BASE_URL or "http://localhost:11434/v1").strip()
    )
    keys = {"groq": groq_key, "openai": openai_key, "ollama": ollama_key}

    for provider in _provider_order():
        api_key = keys.get(provider)
        if provider in _BANNED_PROVIDERS or not api_key:
            continue
        if provider == "groq" and not api_key.startswith("gsk_"):
            continue
        if provider == "openai" and not api_key.startswith("sk-"):
            continue
        if provider == "ollama" and not api_key:
            continue
        try:
            if provider == "groq":
                from groq import Groq

                _current_client = Groq(api_key=api_key)
            elif provider == "openai":
                from openai import OpenAI

                _current_client = OpenAI(api_key=api_key)
            elif provider == "ollama":
                from openai import OpenAI

                _current_client = OpenAI(
                    base_url=ollama_url,
                    api_key=api_key,
                    timeout=300.0,
                    max_retries=1,
                )
            else:
                continue
            _current_provider = provider
            return _current_client, _current_provider
        except Exception as e:
            logger.warning(
                "AI Coach: %s init error: %s: %s",
                provider.title(),
                type(e).__name__,
                e,
            )
            _ban_provider(provider, "init error")
            _current_client = None
            _current_provider = None

    msg = (
        "AI Coach: no valid API key (GROQ=gsk_..., "
        "OPENAI=sk-..., OLLAMA=http://localhost:11434/v1) or all providers failed"
    )
    logger.error(msg)
    raise ValueError(msg)


def _use_local_coach() -> bool:
    return _coach_mode() in _LOCAL_COACH_MODES


def _kb(query: str, max_chunks: int = 3, session=None) -> str:
    """Search knowledge base with optional PGVector session fallback to BM25."""
    if session is not None:
        try:
            from .knowledge_base import search_knowledge_base_pgvector

            results = search_knowledge_base_pgvector(
                query, session, max_chunks=max_chunks, min_score=0.1, as_string=True
            )
            if results:
                return results
        except Exception as exc:
            logger.debug("PGVector knowledge base lookup failed (non-critical): %s", exc)
            pass
    results = search_knowledge_base(query, max_chunks=max_chunks)
    if not results:
        return ""
    parts = []
    for r in results:
        header = f"[{r.get('section', r['topic'])}]"
        parts.append(f"{header}\n{r['text'].strip()}")
    return "\n\n---\n\n".join(parts)


def _system_prompt() -> str:
    return (
        "Sei un coach ciclistico esperto. Rispondi in modo BREVE, SPECIFICO e PRATICO. "
        "Usa la conoscenza fornita quando disponibile. Non chiedere informazioni gia date."
    )


def _few_shot_training_examples() -> str:
    return (
        "ESEMPI:\n"
        "Q: Come migliorare il FTP?\n"
        "A: **1.** Aggiungi 2 sessioni di soglia da 20 min a settimana. "
        "**2.** Inserisci una sessione di VO2max (6x3 min) per stimolare la potenza. "
        "**3.** Monitora la recovery: se TSB <-15 riduci l'intensita."
    )


def _few_shot_recovery_examples() -> str:
    return (
        "ESEMPI:\n"
        "Q: Recupero dopo una gara?\n"
        "A: **1.** Dormi 8-10 ore per 48h e reintegra carboidrati entro 30 min. "
        "**2.** Fai 15-20 min di pedalata molto leggera per attivare il circolo. "
        "**3.** Evita sessioni intense per 24-48h se il TSB e molto negativo."
    )


def _rules_section() -> str:
    return (
        "REGOLE:\n"
        f"- {_LANG_INSTRUCTION}\n"
        "- Ogni consiglio inizia con numero e titolo in grassetto.\n"
        "- Massimo 2 righe per consiglio.\n"
        "- Non usare backtick, codice o emoji.\n"
        "- Non aggiungere saluti o chiusure.\n"
        "- Usa numeri interi quando possibile."
    )


def _generate_local_training_advice(athlete: AthleteProfile, rides: list[Ride]) -> str:
    level = (athlete.experience_level or "beginner").lower()
    terrain = (athlete.preferred_terrain or "").lower()
    goals = (athlete.goals or "").lower()

    queries: list[str] = [
        "weekly training plan periodization",
        f"training {level}" if level else "base training",
    ]
    if any(w in goals for w in ["granfondo", "gran fondo", "granfondo"]):
        queries.append("gran fondo endurance long distance")
    if any(w in goals for w in ["criterium", "crit", "sprint", "short", "veloce"]):
        queries.append("criterium sprint high intensity")
    if any(w in goals for w in ["downhill", "enduro", "tech", "technical"]):
        queries.append("downhill technique strength")
    if any(w in terrain for w in ["mountain", "hill", "climb", "salita", "montagna"]):
        queries.append("hill climbing training strength")
    if any(w in terrain for w in ["flat", "piana", "pianura", "time trial"]):
        queries.append("flat terrain aerobic threshold")
    if not rides:
        queries.append("base building off-season")

    seen: set[str] = set()
    kb_parts: list[str] = []
    for q in queries:
        chunk = _kb(q, max_chunks=2)
        if chunk and chunk not in seen:
            seen.add(chunk)
            kb_parts.append(chunk)

    kb_context = "\n\n".join(kb_parts[:4]) if kb_parts else ""

    suggestions: list[str] = []
    if kb_context:
        suggestions.append(f"**1. Knowledge-based advice**\n{kb_context[:1200]}")
        suggestions.append("**2. Progressive overload** Increase weekly volume by max 10% to avoid overtraining")
    else:
        suggestions.append(
            "**1. Aerobic base** Add 2-3 Zone 2 rides this week to build endurance without excessive fatigue"
        )
        suggestions.append(
            "**2. Controlled intensity** Add 1 short interval session, for example 5x3 min hard with 3 min easy"
        )
    suggestions.append("**3. Recovery** Keep at least 1 full rest day and sleep 7-9 hours")
    return "\n\n".join(suggestions)


def _generate_local_recovery_advice(athlete: AthleteProfile, rides: list[Ride], recovery_score: float) -> str:
    recent = rides[-1] if rides else None
    fatigue_flag = "fatigued" if recovery_score < 5 else "normal"

    queries = [
        "recovery stretching hydration sleep nutrition",
        f"recovery {fatigue_flag}" if recovery_score < 5 else "active recovery maintenance",
    ]
    if recent:
        if getattr(recent, "elevation_gain_m", 0) and recent.elevation_gain_m > 500:
            queries.append("recovery heavy climbing tired legs")
        if getattr(recent, "duration_minutes", 0) and recent.duration_minutes > 180:
            queries.append("recovery long ride ultra endurance")

    seen: set[str] = set()
    kb_parts: list[str] = []
    for q in queries:
        chunk = _kb(q, max_chunks=2)
        if chunk and chunk not in seen:
            seen.add(chunk)
            kb_parts.append(chunk)

    kb_context = "\n\n".join(kb_parts[:3]) if kb_parts else ""
    focus = "extra recovery" if recovery_score < 5 else "active maintenance"

    suggestions: list[str] = []
    if kb_context:
        suggestions.append(f"**1. {focus}**\n{kb_context[:1000]}")
    else:
        suggestions.append(f"**1. {focus}** Take a very easy spin or 10-15 minutes of stretching today")
    suggestions.append(
        "**2. Hydration and nutrition** Drink regularly and include carbohydrates and protein after training"
    )
    suggestions.append("**3. Sleep** Aim for 7-9 hours to support adaptation and recovery")
    return "\n\n".join(suggestions)


def validate_athlete_profile(athlete: AthleteProfile) -> tuple[bool, str]:
    missing = []
    if not athlete.name or athlete.name.strip() == "":
        missing.append("nome")
    if athlete.weight_kg and athlete.weight_kg > 0:
        pass
    else:
        missing.append("peso")
    if missing:
        return False, f"Campi mancanti: {', '.join(missing)}."
    return True, ""


def _build_athlete_context(athlete: AthleteProfile) -> str:
    parts = [
        f"Nome: {athlete.name or 'N/A'}",
        f"Livello: {athlete.experience_level}",
        f"Peso: {athlete.weight_kg} kg",
        f"Eta: {athlete.age} anni",
        f"Anni attivo: {athlete.years_active}",
        f"Settimane/anno: {athlete.annual_hours:.0f}h totali",
    ]
    if getattr(athlete, "goals", None):
        parts.append(f"Obiettivi: {athlete.goals}")
    if getattr(athlete, "preferred_terrain", None):
        parts.append(f"Terreno preferito: {athlete.preferred_terrain}")
    if getattr(athlete, "weekly_volume_km", 0):
        parts.append(f"Volume settimanale: {athlete.weekly_volume_km:.0f} km")
    if getattr(athlete, "best_segments", None):
        parts.append(f"Segmenti migliori: {athlete.best_segments}")
    return "\n".join(parts)


def _build_rag_context(athlete: AthleteProfile, rides: list[Ride], query_hint: str = "") -> str:
    kb_results: list[dict] = []
    if athlete.goals:
        kb_results.extend(search_knowledge_base(f"obiettivi {athlete.goals} {athlete.experience_level}", max_chunks=2))
    if athlete.preferred_terrain:
        kb_results.extend(search_knowledge_base(f"allenamento {athlete.preferred_terrain}", max_chunks=2))
    if rides:
        last = rides[-1]
        hints = []
        if last.avg_speed_kmh > 25:
            hints.append("alta velocita potenza")
        if getattr(last, "elevation_gain_m", 0) and last.elevation_gain_m > 200:
            hints.append("dislivello salita")
        if getattr(last, "heart_rate_avg", None) and last.heart_rate_avg > 160:
            hints.append("frequenza cardiaca alta")
        if hints:
            kb_results.extend(search_knowledge_base(" ".join(hints), max_chunks=2))
    if query_hint:
        kb_results.extend(search_knowledge_base(query_hint, max_chunks=2))
    seen_ids: set[str] = set()
    deduped: list[dict] = []
    for r in kb_results:
        cid = r.get("chunk_id", "")
        if cid and cid not in seen_ids:
            seen_ids.add(cid)
            deduped.append(r)
    return format_context_for_llm(deduped[:5])


def _chat_completion_text(client: object, model: str, prompt: str, max_tokens: int) -> str:
    chat = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return chat.choices[0].message.content or ""


def generate_training_advice(athlete: AthleteProfile, rides: list[Ride], athlete_id: int | None = None) -> str:
    is_valid, err = validate_athlete_profile(athlete)
    if not is_valid:
        return f"Completa il profilo atleta: {err}"
    if _use_local_coach():
        return _generate_local_training_advice(athlete, rides)

    stats = calculate_summary(rides) if rides else {}
    perf = calculate_performance_score(rides[-1]) if rides else 0
    recovery = calculate_recovery_score(rides[-1]) if rides else 0
    from datetime import datetime

    now = datetime.now(UTC)
    recent = rides[-3:] if rides else []
    recent_info = (
        "; ".join(
            [f"{r.date}: {r.distance_km:.1f}km, {r.avg_speed_kmh:.1f}km/h, {r.duration_minutes:.0f}min" for r in recent]
        )
        if recent
        else "nessuna uscita recente"
    )
    if len(rides) >= 2:
        first_date = min(r.date for r in rides if r.date)
        last_date = max(r.date for r in rides if r.date)
        try:
            first_dt = datetime.fromisoformat(first_date)
            last_dt = datetime.fromisoformat(last_date)
            days_span = (last_dt - first_dt).days
        except Exception:
            days_span = 0
    else:
        days_span = 0
    rag = _build_rag_context(athlete, rides, "piano allenamento settimanale")
    rag_section = f"\n\nCONOSCENZE APPLICATE:\n{rag}" if rag else ""
    history_section = ""
    if athlete_id:
        try:
            from ..db.database import get_chat_history, prune_chat_history
            from ..settings import get_settings

            prune_chat_history(athlete_id, None, get_settings().ai_coach_chat_retention_days)
            history = get_chat_history(athlete_id, limit=5)
            if history:
                history_section = (
                    "\n\nCONVERSAZIONE PRECEDENTE:\n"
                    + "\n".join(f"{h['role']}: {h['content'][:200]}" for h in reversed(history))
                )
        except Exception as exc:
            logger.debug("Chat history fetch failed (non-critical): %s", exc)
    total_rides = stats.get("total_rides", 0)
    avg_distance = stats.get("avg_distance_km", 0)
    today_str = now.strftime("%Y-%m-%d")
    prompt = (
        f"{_system_prompt()}\n"
        f"{_few_shot_training_examples()}\n"
        f"{history_section}{rag_section}\n\n"
        f"Profilo atleta:\n{_build_athlete_context(athlete)}\n\n"
        f"Dati recenti:\n"
        f"- Performance score: {perf}/10\n"
        f"- Recovery score: {recovery}/10\n"
        f"- Ultime 3 uscite: {recent_info}\n"
        f"- Totale uscite in archivio: {int(total_rides) if total_rides == int(total_rides) else total_rides}\n"
        f"- Distanza media: {int(avg_distance) if avg_distance == int(avg_distance) else avg_distance:.1f} km\n"
        f"- Giorno corrente: {today_str}\n"
        f"- Archivio temporale: {days_span} giorni\n\n"
        f"{_rules_section()}"
    )

    max_retries = 3
    attempt = 0
    while attempt < max_retries:
        try:
            client, provider = get_ai_coach_client()
        except ValueError:
            logger.warning("AI Coach no API key available, using fallback")
            from ..monitoring import record_ai_coach_query

            record_ai_coach_query("fallback", "fallback")
            return _generate_fallback_training_advice(athlete, rides)

        try:
            messages = [{"role": "user", "content": prompt}]
            result = chat_with_tools(messages, athlete_id=athlete_id, athlete=athlete, rides=rides)
            content = result.get("content", "")
            from ..monitoring import record_ai_coach_query

            record_ai_coach_query(provider, "success")
            return _clean_ai_output(content)
        except Exception as e:
            from ..monitoring import record_ai_coach_query

            record_ai_coach_query(provider, "error")
            logger.warning("AI Coach API call failed: %s: %s", type(e).__name__, e)
            logger.debug("AI Coach API error details", exc_info=True)
            _ban_provider(provider, "connection error" if "connection" in str(e).lower() else "auth error")
            if not _is_recoverable_provider_error(e):
                logger.error("AI Coach: non-recoverable error from %s, using fallback", provider)
                record_ai_coach_query("fallback", "fallback")
                return _generate_fallback_training_advice(athlete, rides)
            attempt += 1
            continue
    return _generate_fallback_training_advice(athlete, rides)


generate_workout_recommendations = generate_training_advice


def generate_recovery_advice(
    athlete: AthleteProfile,
    rides: list[Ride],
    fatigue_score: float = 5.0,
    athlete_id: int | None = None,
) -> str:
    from datetime import datetime

    is_valid, err = validate_athlete_profile(athlete)
    if not is_valid:
        return f"Completa il profilo atleta prima di usare l'AI Coach: {err}"
    if _use_local_coach():
        return _generate_local_recovery_advice(athlete, rides, fatigue_score)

    now = datetime.now(UTC)
    recovery = calculate_recovery_score(rides[-1]) if rides else fatigue_score
    stats = calculate_summary(rides) if rides else {}
    recent = rides[-1] if rides else None
    recent_info = f"{recent.distance_km:.1f}km a {recent.avg_speed_kmh:.1f}km/h" if recent else "nessuna uscita recente"
    rag = _build_rag_context(athlete, rides, "recupero stretching idratazione sonno alimentazione")
    rag_section = f"\n\nCONOSCENZE APPLICATE:\n{rag}" if rag else ""
    history_section = ""
    if athlete_id:
        try:
            from ..db.database import get_chat_history, prune_chat_history
            from ..settings import get_settings

            prune_chat_history(athlete_id, None, get_settings().ai_coach_chat_retention_days)
            history = get_chat_history(athlete_id, limit=5)
            if history:
                history_section = (
                    "\n\nCONVERSAZIONE PRECEDENTE:\n"
                    + "\n".join(f"{h['role']}: {h['content'][:200]}" for h in reversed(history))
                )
        except Exception as exc:
            logger.debug("Chat history fetch failed (non-critical): %s", exc)
    prompt = (
        f"{_system_prompt()}\n"
        f"{_few_shot_recovery_examples()}\n"
        f"{history_section}{rag_section}\n\n"
        f"Profilo atleta:\n{_build_athlete_context(athlete)}\n\n"
        f"Dati:\n"
        f"- Recovery score: {recovery}/10\n"
        f"- Ultima uscita: {recent_info}\n"
        f"- Allenamenti archiviati: {stats.get('total_rides', 0)}\n"
        f"- Giorno corrente: {now.strftime('%Y-%m-%d')}\n\n"
        f"{_rules_section()}"
    )

    max_retries = 3
    attempt = 0
    while attempt < max_retries:
        try:
            client, provider = get_ai_coach_client()
        except ValueError:
            from ..monitoring import record_ai_coach_query

            record_ai_coach_query("fallback", "fallback")
            return _generate_fallback_recovery_advice(athlete, rides, recovery)

        model = GROQ_MODEL if provider == "groq" else OLLAMA_MODEL if provider == "ollama" else OPENAI_MODEL
        try:
            content = _chat_completion_text(client, model, prompt, 300)
            from ..monitoring import record_ai_coach_query

            record_ai_coach_query(provider, "success")
            return _clean_ai_output(content)
        except Exception as e:
            from ..monitoring import record_ai_coach_query

            record_ai_coach_query(provider, "error")
            logger.warning("AI Coach API call failed: %s: %s", type(e).__name__, e)
            logger.debug("AI Coach API error details", exc_info=True)
            _ban_provider(provider, "connection error" if "connection" in str(e).lower() else "auth error")
            attempt += 1
            continue
    return _generate_fallback_recovery_advice(athlete, rides, recovery)


_FALLBACK_PREFIX = "(AI service temporarily unavailable - model-based advice)\n\n"


def _generate_fallback_training_advice(athlete: AthleteProfile, rides: list[Ride]) -> str:
    kb = search_knowledge_base("base training periodization", max_chunks=3)
    if kb:
        context = format_context_for_llm(kb)
        advice = (
            f"{context}\n\n**3. Progressive** Increase weekly volume "
            f"by max 10% per week to avoid overtraining\n"
            f"**4. Recovery** Include 1-2 full rest days per week"
        )
    else:
        advice = (
            "**1. Aerobic base** Do 80% of rides at low intensity "
            "(Zone 2) to build endurance\n"
            "**2. Progression** Increase weekly volume by max 10% per week "
            "to avoid overtraining\n"
            "**3. Recovery** Include 1-2 full rest days per week"
        )
    return f"{_FALLBACK_PREFIX}{advice}"


def _generate_fallback_recovery_advice(athlete: AthleteProfile, rides: list[Ride], recovery_score: float = 5.0) -> str:
    kb = search_knowledge_base("recupero sonno idratazione stretching", max_chunks=3)
    context = format_context_for_llm(kb) if kb else ""
    if context:
        advice = f"{context}\n\n**3. Consigli pratici** Applica questi principi di recupero nel tuo routine quotidiana"
    else:
        base = (
            "**1. Sonno** Dormi 7-9 ore per notte per ottimale recupero\n"
            "**2. Idratazione** Bevi 500ml d'acqua per ogni ora di allenamento"
        )
        advice = (
            f"{base}\n**3. Stretching** 10-15 min di stretching post-allenamento "
            "per flessibilita e prevenzione infortuni"
            if recovery_score < 5
            else f"{base}\n**3. Alimentazione** Consumate carboidrati e proteine "
            "nella ratio 3:1 entro 30 min dal termine"
        )
    return f"{_FALLBACK_PREFIX}{advice}"


generate_recovery_recommendations = generate_recovery_advice


def analyze_historical_trend(rides: list[Ride]) -> str:
    if len(rides) < 2:
        return "Insufficient data for trend."
    from .fatigue import calculate_fatigue_score

    avg_fatigue = sum(calculate_fatigue_score(r) for r in rides) / len(rides)
    avg_perf = sum(calculate_performance_score(r) for r in rides) / len(rides)
    trend = "crescente" if avg_perf > 5 else "stabile" if avg_perf > 3 else "da monitorare"
    return f"Trend: {trend}, fatigue media: {avg_fatigue:.1f}/10, performance media: {avg_perf:.1f}/10"


analyze_historical_trends = analyze_historical_trend


def get_fitness_state_explanation(athlete_id: int, session_factory=None) -> str:
    """Get transparent explanation of fitness state for AI context."""
    if not session_factory or not athlete_id:
        return ""

    import asyncio

    from ..repositories.fitness_state_repository import FitnessStateRepository

    async def _get():
        repo = FitnessStateRepository(session_factory=session_factory)
        state = await repo.get_latest(athlete_id)
        if not state:
            return ""
        return (
            f"TSB: {state.get('tsb', 0):.1f}, ATL: {state.get('atl', 0):.1f}, CTL: {state.get('ctl', 0):.1f}. "
            f"Recupero stimato: {state.get('recovery_hours_needed', 0):.0f}h."
        )

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_get())
    except Exception:
        return ""


def ai_coach_full(athlete: AthleteProfile, rides: list[Ride], athlete_id: int | None = None) -> dict:
    from pathlib import Path

    from ..analytics.performance import (
        calculate_efficiency_score,
        calculate_endurance_score,
        calculate_performance_score,
        calculate_recovery_score,
    )
    from ..processing.processing import build_segments

    recent = rides[-1] if rides else None
    perf = calculate_performance_score(recent) if recent else 0
    recovery = calculate_recovery_score(recent) if recent else 0
    endurance = calculate_endurance_score(rides)
    efficiency = calculate_efficiency_score(recent) if recent else 0
    static_dir = Path(__file__).parent.parent / "static"
    static_dir.mkdir(exist_ok=True)
    charts = []
    try:
        points_data = getattr(recent, "gps_points", []) if recent else []
        for old_chart in ["coach_speed.png", "coach_duration.png"]:
            with contextlib.suppress(Exception):
                (static_dir / old_chart).unlink(missing_ok=True)
        if points_data:
            from ..models.models import GPSPoint

            points = [GPSPoint(**p) for p in points_data]
            segments = build_segments(points)
            if segments:
                sp = static_dir / "coach_speed.png"
                create_speed_chart(segments, str(sp))
                charts.append("/static/coach_speed.png")
        if rides:
            dp = static_dir / "coach_duration.png"
            create_duration_chart(rides, str(dp))
            charts.append("/static/coach_duration.png")
    except Exception:
        pass
    training_advice = generate_workout_recommendations(athlete, rides, athlete_id)
    recovery_advice = generate_recovery_recommendations(athlete, rides, athlete_id)
    fitness_explanation = ""
    if athlete_id:
        fitness_explanation = get_fitness_state_explanation(athlete_id)
    return {
        "training_advice": training_advice,
        "recovery_advice": recovery_advice,
        "historical_analysis": analyze_historical_trends(rides),
        "fitness_explanation": fitness_explanation,
        "training_scores": [
            {"label": "Performance", "value": perf},
            {"label": "Endurance", "value": endurance},
            {"label": "Efficiency", "value": efficiency},
        ],
        "recovery_scores": [
            {"label": "Recovery", "value": recovery},
            {"label": "Fatigue", "value": round(10.0 - recovery, 1)},
        ],
        "charts": charts,
    }


def generate_training_plan(
    athlete: AthleteProfile,
    days: int = 7,
    include_recovery: bool = True,
    fitness_state: dict | None = None,
) -> dict:
    """Generate structured training plan using tool calling pattern."""
    plan = {
        "days": days,
        "athlete_name": athlete.name,
        "ftp_watts": athlete.ftp_watts or 250,
        "workouts": [],
    }

    zone2_duration = 60 if athlete.experience_level == "Beginner" else 90
    zone3_duration = int(zone2_duration * 0.7)
    zone4_duration = int(zone2_duration * 0.4)

    if fitness_state:
        tsb = fitness_state.get("tsb", 0)
        if tsb < -15:
            plan["workouts"] = [
                {"day": "Lunedi", "type": "Recupero", "duration_min": 30, "zone": "Base"},
                {"day": "Martedi", "type": "Recupero", "duration_min": 45, "zone": "Base"},
                {"day": "Mercoledi", "type": "Attivazione", "duration_min": zone2_duration, "zone": "Z2"},
                {"day": "Giovedi", "type": "Recupero", "duration_min": 45, "zone": "Base"},
                {"day": "Venerdi", "type": "Recupero", "duration_min": 30, "zone": "Base"},
            ]
        elif tsb > 10:
            plan["workouts"] = [
                {"day": "Lunedi", "type": "Qualita", "duration_min": zone4_duration, "zone": "Z4"},
                {"day": "Martedi", "type": "Endurance", "duration_min": zone2_duration, "zone": "Z2"},
                {"day": "Mercoledi", "type": "THRESHOLD", "duration_min": zone3_duration, "zone": "Z3"},
                {"day": "Giovedi", "type": "Recupero", "duration_min": 45, "zone": "Base"},
                {"day": "Venerdi", "type": "VO2max", "duration_min": zone4_duration, "zone": "Z5"},
            ]
        else:
            plan["workouts"] = [
                {"day": "Lunedi", "type": "Endurance", "duration_min": zone2_duration, "zone": "Z2"},
                {"day": "Martedi", "type": "Threshold", "duration_min": zone3_duration, "zone": "Z3"},
                {"day": "Mercoledi", "type": "Recupero", "duration_min": 45, "zone": "Base"},
                {"day": "Giovedi", "type": "Endurance", "duration_min": zone2_duration, "zone": "Z2"},
                {"day": "Venerdi", "type": "Threshold", "duration_min": zone3_duration, "zone": "Z3"},
            ]
    else:
        plan["workouts"] = [
            {"day": "Lunedi", "type": "Endurance", "duration_min": zone2_duration, "zone": "Z2"},
            {"day": "Martedi", "type": "Threshold", "duration_min": zone3_duration, "zone": "Z3"},
            {"day": "Mercoledi", "type": "Recupero", "duration_min": 45, "zone": "Base"},
            {"day": "Giovedi", "type": "Endurance", "duration_min": zone2_duration, "zone": "Z2"},
            {"day": "Venerdi", "type": "Threshold", "duration_min": zone3_duration, "zone": "Z3"},
        ]

    tsb = fitness_state.get("tsb", 0) if fitness_state else 0
    plan["explanation"] = (
        f"Piano basato su FTP {athlete.ftp_watts or 250}W. "
        f"{tsb:.1f} TSB indica "
        f"{'recupero prioritario' if tsb < -15 else 'forma ottimale' if tsb > 10 else 'forma buona'}."
        if fitness_state
        else "Piano generico basato su livello esperto."
    )
    return plan


generate_workout_plan = generate_training_plan


# ---------------------------------------------------------------------------
# Tool Calling Functions
# ---------------------------------------------------------------------------

GENERATE_WORKOUT_PLAN_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_workout_plan",
        "description": "Generate a structured cycling training plan",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "default": 7},
                "include_recovery": {"type": "boolean", "default": True},
            },
        },
    },
}

ANALYZE_ANOMALIES_TOOL = {
    "type": "function",
    "function": {
        "name": "analyze_anomalies",
        "description": "Analyze rides for anomalies like fatigue or heart rate drift",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}


def analyze_anomalies(rides: list[Ride]) -> dict:
    """Analyze rides for anomalies: fatigue, heart rate drift, overtraining signs."""
    if not rides:
        return {"status": "no_data", "anomalies": []}

    anomalies = []
    hr_values = [r.heart_rate_avg for r in rides if getattr(r, "heart_rate_avg", None)]
    if len(hr_values) >= 3:
        avg_hr = sum(hr_values) / len(hr_values)
        recent_hr = hr_values[-1]
        if recent_hr > avg_hr * 1.15:
            anomalies.append(
                {
                    "type": "heart_rate_elevation",
                    "severity": "warning",
                    "message": f"Frequenza cardiaca recente ({recent_hr:.0f}) sopra la media ({avg_hr:.0f})",
                }
            )

    durations = [r.duration_minutes for r in rides if r.duration_minutes]
    if len(durations) >= 2:
        avg_duration = sum(durations) / len(durations)
        if avg_duration > 240 and any(r.duration_minutes > 300 for r in rides[-3:]):
            anomalies.append(
                {
                    "type": "excessive_volume",
                    "severity": "info",
                    "message": f"Volume elevato: ultime uscite >5h, media {avg_duration:.0f}min",
                }
            )

    return {"status": "analyzed", "anomalies": anomalies[:5]}


def chat_with_tools(
    messages: list[dict],
    athlete_id: int | None = None,
    session_factory=None,
    athlete: AthleteProfile | None = None,
    rides: list[Ride] | None = None,
) -> dict:
    """LLM chat completion with tool calling support and execution loop.

    Args:
        messages: List of chat messages with {role, content}
        athlete_id: Athlete ID for context and persistence
        session_factory: Async session factory for tool execution
        athlete: AthleteProfile for tool execution context
        rides: List of Ride for tool execution context

    Returns:
        {"content": str, "tool_calls": list} or {"content": str} if no tools called
    """
    if _use_local_coach():
        return {"content": "Modalità locale: i tool calling non sono disponibili."}

    try:
        client, provider = get_ai_coach_client()
    except ValueError:
        return {"content": "Nessun provider LLM configurato."}

    model = GROQ_MODEL if provider == "groq" else OLLAMA_MODEL if provider == "ollama" else OPENAI_MODEL

    tools = [GENERATE_WORKOUT_PLAN_TOOL, ANALYZE_ANOMALIES_TOOL]

    tool_map = {
        "generate_workout_plan": lambda args: generate_training_plan(
            athlete or AthleteProfile(name="Atleta"),
            int(args.get("days", 7)),
            bool(args.get("include_recovery", True)),
        ),
        "analyze_anomalies": lambda args: analyze_anomalies(rides or []),
    }

    def _execute_tool_calls(tool_calls: list) -> list[dict]:
        results = []
        for tc in tool_calls:
            func_name = tc.function.name
            func_args = {}
            if tc.function.arguments:
                try:
                    func_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    func_args = {}
            if func_name in tool_map:
                try:
                    result = tool_map[func_name](func_args)
                    results.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result) if not isinstance(result, str) else result,
                        }
                    )
                except Exception as exc:
                    logger.warning("Tool execution failed %s: %s", func_name, exc)
                    results.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps({"error": str(exc)}),
                        }
                    )
            else:
                results.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps({"error": f"Unknown tool: {func_name}"}),
                    }
                )
        return results

    try:
        tool_calls = []
        response = (
            client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
            )
            .choices[0]
            .message
        )

        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_calls = response.tool_calls
            messages.append(
                {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )

            tool_results = _execute_tool_calls(tool_calls)
            messages.extend(tool_results)

            if athlete_id:
                from ..db.database import save_chat_message

                save_chat_message(athlete_id, "assistant", str(tool_results))

            response = (
                client.chat.completions.create(
                    model=model,
                    messages=messages,
                )
                .choices[0]
                .message
            )

        return {"content": response.content or ""}
    except Exception:
        raise
