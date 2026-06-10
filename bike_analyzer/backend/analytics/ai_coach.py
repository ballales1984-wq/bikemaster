"""AI Coach with cycling knowledge base RAG and athlete memory."""
from __future__ import annotations

import os
import re
import traceback
from typing import List, Optional

from ..config import GROQ_API_KEY, GROQ_MODEL, OPENAI_API_KEY, OPENAI_MODEL
from ..models.models import AthleteProfile, Ride
from .analytics import calculate_summary
from .knowledge_base import format_context_for_llm, search_knowledge_base
from .performance import calculate_performance_score, calculate_recovery_score

LOCALE: str = os.getenv("LOCALE", "it")
_LANG_PROMPT = {"it": "Rispondi in italiano", "en": "Respond in English", "es": "Responde en español", "fr": "Réponds en français"}
_LANG_INSTRUCTION = _LANG_PROMPT.get(LOCALE, _LANG_PROMPT["it"])

_current_client: Optional[object] = None
_current_provider: Optional[str] = None

_fmt_clean_pattern = re.compile(r'(?<!\d)(\d+\.\d)0(?!\d)')
_fmt_int_pattern = re.compile(r'(?<!\d)(\d+)\.0(?!\d)')


def _clean_ai_output(text: str) -> str:
    text = _fmt_int_pattern.sub(lambda m: m.group(1), text)
    text = _fmt_clean_pattern.sub(lambda m: m.group(1), text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()


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


def get_ai_coach_client():
    global _current_client, _current_provider
    if _current_client:
        return _current_client, _current_provider
    if GROQ_API_KEY and GROQ_API_KEY.startswith("gsk_"):
        try:
            from groq import Groq
            _current_client = Groq(api_key=GROQ_API_KEY)
            _current_provider = "groq"
            return _current_client, _current_provider
        except Exception as e:
            print(f"Groq init error: {e}")
            _current_client = None
            _current_provider = None
    if OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-"):
        try:
            from openai import OpenAI
            _current_client = OpenAI(api_key=OPENAI_API_KEY)
            _current_provider = "openai"
            return _current_client, _current_provider
        except Exception as e:
            print(f"OpenAI init error: {e}")
            _current_client = None
            _current_provider = None
    raise ValueError("Nessuna API key valida configurata (GROQ o OPENAI)")


def _build_athlete_context(athlete: AthleteProfile) -> str:
    parts = [f"Nome: {athlete.name or 'N/A'}", f"Livello: {athlete.experience_level}", f"Peso: {athlete.weight_kg} kg", f"Eta: {athlete.age} anni", f"Anni attivo: {athlete.years_active}", f"Settimane/anno: {athlete.annual_hours:.0f}h totali"]
    if getattr(athlete, "goals", None):
        parts.append(f"Obiettivi: {athlete.goals}")
    if getattr(athlete, "preferred_terrain", None):
        parts.append(f"Terreno preferito: {athlete.preferred_terrain}")
    if getattr(athlete, "weekly_volume_km", 0):
        parts.append(f"Volume settimanale: {athlete.weekly_volume_km:.0f} km")
    if getattr(athlete, "best_segments", None):
        parts.append(f"Segmenti migliori: {athlete.best_segments}")
    if getattr(athlete, "medical_notes", None):
        parts.append(f"Note mediche: {athlete.medical_notes}")
    if getattr(athlete, "equipment", None):
        parts.append(f"Attrezzatura: {athlete.equipment}")
    return "\n".join(parts)


def _build_rag_context(athlete: AthleteProfile, rides: List[Ride], query_hint: str = "") -> str:
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


def generate_training_advice(athlete: AthleteProfile, rides: List[Ride], athlete_id: Optional[int] = None) -> str:
    try:
        is_valid, err = validate_athlete_profile(athlete)
        if not is_valid:
            return f"Completa il profilo atleta: {err}"
        try:
            client, provider = get_ai_coach_client()
        except ValueError as e:
            print(f"AI Coach no API key: {e}")
            return _generate_fallback_training_advice(athlete, rides)
        stats = calculate_summary(rides) if rides else {}
        perf = calculate_performance_score(rides[-1]) if rides else 0
        recovery = calculate_recovery_score(rides[-1]) if rides else 0
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        recent = rides[-3:] if rides else []
        recent_info = "; ".join([f"{r.date}: {r.distance_km:.1f}km, {r.avg_speed_kmh:.1f}km/h, {r.duration_minutes:.0f}min" for r in recent]) if recent else "nessuna uscita recente"
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
                from ..db.database import get_chat_history
                history = get_chat_history(athlete_id, limit=5)
                if history:
                    history_section = "\n\nCONVERSAZIONE PRECEDENTE:\n" + "\n".join([f"{h['role']}: {h['content'][:200]}" for h in reversed(history)])
            except Exception:
                pass
        total_rides = stats.get('total_rides', 0)
        avg_distance = stats.get('avg_distance_km', 0)
        today_str = now.strftime("%Y-%m-%d")
        prompt = f"""Sei un coach ciclistico esperto. Genera 3 consigli di allenamento BREVI e SPECIFICI.{history_section}{rag_section}

Profilo atleta:
{_build_athlete_context(athlete)}

Dati recenti:
- Performance score: {perf}/10
- Recovery score: {recovery}/10
- Ultime 3 uscite: {recent_info}
- Totale uscite in archivio: {int(total_rides) if total_rides == int(total_rides) else total_rides}
- Distanza media: {int(avg_distance) if avg_distance == int(avg_distance) else avg_distance:.1f} km
- Giorno corrente: {today_str}
- Archivio temporale: {days_span} giorni

REGOLE:
- {_LANG_INSTRUCTION}
- Ogni consiglio deve iniziare con un numero e un titolo in grassetto (es: **1. Obiettivo principale**)
- Massimo 2 righe per consiglio
- Usa i numeri interi quando possibile (es: 3 volte, non 3.0 volte)
- Non usare backtick, codice o formattazione markdown speciale
- Non usare emoji
- Non aggiungere saluti o chiusure tipo "Buon allenamento!"
- Se la sezione CONOSCENZE APPLICATE e presente, integrale nei consigli in modo naturale
- Se la sezione CONVERSAZIONE PRECEDENTE e presente, NON chiedere informazioni gia fornite
- Non mostrare valori con .0 se sono interi (es: scrivi "3 volte" non "3.0 volte")
        """
        model = GROQ_MODEL if provider == "groq" else OPENAI_MODEL
        chat = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], max_tokens=500)
        content = chat.choices[0].message.content or "Nessun consiglio disponibile"
        return _clean_ai_output(content)
    except Exception as e:
        print(f"DEBUG: API call failed: {type(e).__name__}: {e}")
        traceback.print_exc()
        if "401" in str(e) or "403" in str(e) or "invalid_api_key" in str(e).lower() or "PermissionDenied" in type(e).__name__:
            return _generate_fallback_training_advice(athlete, rides)
        return f"AI Coach non disponibile: {type(e).__name__}: {e}"


generate_workout_recommendations = generate_training_advice


def generate_recovery_advice(athlete: AthleteProfile, rides: List[Ride], fatigue_score: float = 5.0, athlete_id: Optional[int] = None) -> str:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    try:
        is_valid, err = validate_athlete_profile(athlete)
        if not is_valid:
            return f"Completa il profilo atleta prima di usare l'AI Coach: {err}"
        try:
            client, provider = get_ai_coach_client()
        except ValueError:
            return _generate_fallback_recovery_advice(athlete, rides, fatigue_score)
        recovery = calculate_recovery_score(rides[-1]) if rides else fatigue_score
        stats = calculate_summary(rides) if rides else {}
        recent = rides[-1] if rides else None
        recent_info = f"{recent.distance_km:.1f}km a {recent.avg_speed_kmh:.1f}km/h" if recent else "nessuna uscita recente"
        rag = _build_rag_context(athlete, rides, "recupero stretching idratazione sonno alimentazione")
        rag_section = f"\n\nCONOSCENZE APPLICATE:\n{rag}" if rag else ""
        history_section = ""
        if athlete_id:
            try:
                from ..db.database import get_chat_history
                history = get_chat_history(athlete_id, limit=5)
                if history:
                    history_section = "\n\nCONVERSAZIONE PRECEDENTE:\n" + "\n".join([f"{h['role']}: {h['content'][:200]}" for h in reversed(history)])
            except Exception:
                pass
        prompt = f"""Sei un coach di recupero ciclistico. Genera 2 consigli BREVI per il recupero di oggi.{history_section}{rag_section}

Profilo atleta:
{_build_athlete_context(athlete)}

        Dati:
- Recovery score: {recovery}/10
- Ultima uscita: {recent_info}
- Allenamenti archiviati: {stats.get('total_rides', 0)}
- Giorno corrente: {now.strftime('%Y-%m-%d')}

REGOLE:
- {_LANG_INSTRUCTION}
- Ogni consiglio deve iniziare con un numero e un titolo in grassetto
- Massimo 2 righe per consiglio
- Sei CONCRETO: parla di durata sonno, idratazione, stretching, alimentazione
- Non ripetere numeri o dati gia forniti nella risposta
- Non usare backtick o markdown speciale
- Se la sezione CONOSCENZE APPLICATE e presente, integrale nei consigli in modo naturale
- Se la sezione CONVERSAZIONE PRECEDENTE e presente, NON chiedere informazioni gia fornite
"""
        model = GROQ_MODEL if provider == "groq" else OPENAI_MODEL
        chat = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], max_tokens=300)
        content = chat.choices[0].message.content or "Recupera bene!"
        return _clean_ai_output(content)
    except Exception as e:
        if "401" in str(e) or "403" in str(e) or "invalid_api_key" in str(e).lower() or "PermissionDenied" in type(e).__name__:
            rec_score = recovery if isinstance(recovery, (int, float)) else 5.0
            return _generate_fallback_recovery_advice(athlete, rides, rec_score)
        traceback.print_exc()
        return f"Recupero non disponibile: {type(e).__name__}: {e}"


_FALLBACK_PREFIX = "(Servizio AI temporaneamente non disponibile - consiglio basato su modello)\n\n"


def _generate_fallback_training_advice(athlete: AthleteProfile, rides: List[Ride]) -> str:
    kb = search_knowledge_base("allenamento base periodizzazione", max_chunks=3)
    context = format_context_for_llm(kb) if kb else "**1. Allenamento Base** Fai 80% delle tue uscite a bassa intensita (Zona 2) per sviluppare l'aerobico"
    return f"{_FALLBACK_PREFIX}**1. Allenamento Base** Fai 80% delle tue uscite a bassa intensita (Zona 2) per sviluppare l'aerobico\n**2. Progressione** Aumenta il volume settimanale di massimo 10% a settimana per evitare sovrallenamento\n**3. Recupero** Inserisci 1-2 giorni di riposo completo a settimana"


def _generate_fallback_recovery_advice(athlete: AthleteProfile, rides: List[Ride], recovery_score: float = 5.0) -> str:
    kb = search_knowledge_base("recupero sonno idratazione stretching", max_chunks=3)
    context = format_context_for_llm(kb) if kb else ""
    base = "**1. Sonno** Dormi 7-9 ore per notte per ottimale recupero\n**2. Idratazione** Bevi 500ml d'acqua per ogni ora di allenamento"
    result = f"{base}\n**3. Stretching** 10-15 min di stretching post-allenamento per flessibilita e prevenzione infortuni" if recovery_score < 5 else f"{base}\n**3. Alimentazione** Consumate carboidrati e proteine nella ratio 3:1 entro 30 min dal termine"
    return f"{_FALLBACK_PREFIX}{result}"


generate_recovery_recommendations = generate_recovery_advice


def analyze_historical_trend(rides: List[Ride]) -> str:
    if len(rides) < 2:
        return "Dati insufficienti per trend."
    from .fatigue import calculate_fatigue_score
    avg_fatigue = sum(calculate_fatigue_score(r) for r in rides) / len(rides)
    avg_perf = sum(calculate_performance_score(r) for r in rides) / len(rides)
    trend = "crescente" if avg_perf > 5 else "stabile" if avg_perf > 3 else "da monitorare"
    return f"Trend: {trend}, fatigue media: {avg_fatigue:.1f}/10, performance media: {avg_perf:.1f}/10"


analyze_historical_trends = analyze_historical_trend


def ai_coach_full(athlete: AthleteProfile, rides: List[Ride], athlete_id: Optional[int] = None) -> dict:
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
            try:
                (static_dir / old_chart).unlink(missing_ok=True)
            except Exception:
                pass
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
    return {"training_advice": generate_workout_recommendations(athlete, rides, athlete_id), "recovery_advice": generate_recovery_recommendations(athlete, rides, athlete_id), "historical_analysis": analyze_historical_trends(rides), "training_scores": [{"label": "Performance", "value": perf}, {"label": "Endurance", "value": endurance}, {"label": "Efficiency", "value": efficiency}], "recovery_scores": [{"label": "Recovery", "value": recovery}, {"label": "Fatigue", "value": round(10.0 - recovery, 1)}], "charts": charts}
