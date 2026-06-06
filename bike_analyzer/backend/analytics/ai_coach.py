"""AI Coach with cycling knowledge base RAG and athlete memory."""
from __future__ import annotations
import traceback
from typing import List, Optional
from ..models.models import Ride, AthleteProfile
from .analytics import calculate_summary
from .performance import calculate_performance_score, calculate_recovery_score
from .knowledge_base import search_knowledge_base, format_context_for_llm
from ..config import GROQ_API_KEY, GROQ_MODEL

def validate_athlete_profile(athlete: AthleteProfile) -> tuple[bool, str]:
    missing = []
    if not athlete.name or athlete.name.strip() == "":
        missing.append("nome")
    if not athlete.experience_level or athlete.experience_level == "Beginner":
        pass  # Beginner e un valore valido, ma se e quello di default e non stato impostato
    if athlete.weight_kg == 70.0 and not getattr(athlete, "name", ""):
        missing.append("peso")
    if missing:
        return False, f"Profilo atleta incompleto. Campi mancanti: {', '.join(missing)}. Completa il tuo profilo nella Dashboard."
    return True, ""

def get_ai_coach_client():
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY non impostata nell'ambiente")
    from groq import Groq
    return Groq(api_key=GROQ_API_KEY)

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
            return f"Completa il profilo atleta prima di usare l'AI Coach: {err}"
        client = get_ai_coach_client()
        stats = calculate_summary(rides) if rides else {}
        perf = calculate_performance_score(rides[-1]) if rides else 0
        recovery = calculate_recovery_score(rides[-1]) if rides else 0
        recent = rides[-3:] if rides else []
        recent_info = "; ".join([f"{r.distance_km:.1f}km, {r.avg_speed_kmh:.1f}km/h, {r.duration_minutes:.0f}min" for r in recent]) if recent else "nessuna uscita recente"
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
        prompt = f"""Sei un coach ciclistico esperto. Genera 3 consigli di allenamento BREVI e SPECIFICI.{history_section}{rag_section}

Profilo atleta:
{_build_athlete_context(athlete)}

Dati recenti:
- Performance score: {perf}/10
- Recovery score: {recovery}/10
- Ultime 3 uscite: {recent_info}
- Totale uscite in archivio: {stats.get('total_rides', 0)}
- Distanza media: {stats.get('avg_distance_km', 0):.1f} km

REGOLE:
- Rispondi in italiano
- Ogni consiglio deve iniziare con un numero e un titolo in grassetto (es: **1. Obiettivo principale**)
- Massimo 2 righe per consiglio
- Usa i numeri con il PUNTO come separatore decimale (es: 70.5 non 70,5)
- Non usare backtick, codice o formattazione markdown speciale
- Non usare emoji
- Non aggiungere saluti o chiusure tipo "Buon allenamento!"
- Se la sezione CONOSCENZE APPLICATE e presente, integrale nei consigli in modo naturale
- Se la sezione CONVERSAZIONE PRECEDENTE e presente, NON chiedere informazioni gia fornite
"""
        chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], max_tokens=500)
        return chat.choices[0].message.content or "Nessun consiglio disponibile"
    except Exception as e:
        traceback.print_exc()
        return f"AI Coach non disponibile: {type(e).__name__}: {e}"

generate_workout_recommendations = generate_training_advice

def generate_recovery_advice(athlete: AthleteProfile, rides: List[Ride], fatigue_score: float = 5.0, athlete_id: Optional[int] = None) -> str:
    try:
        is_valid, err = validate_athlete_profile(athlete)
        if not is_valid:
            return f"Completa il profilo atleta prima di usare l'AI Coach: {err}"
        client = get_ai_coach_client()
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

REGOLE:
- Rispondi in italiano
- Ogni consiglio deve iniziare con un numero e un titolo in grassetto
- Massimo 2 righe per consiglio
- Sei CONCRETO: parla di durata sonno, idratazione, stretching, alimentazione
- Non ripetere numeri o dati gia forniti nella risposta
- Non usare backtick o markdown speciale
- Se la sezione CONOSCENZE APPLICATE e presente, integrale nei consigli in modo naturale
- Se la sezione CONVERSAZIONE PRECEDENTE e presente, NON chiedere informazioni gia fornite
"""
        chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], max_tokens=300)
        return chat.choices[0].message.content or "Recupera bene!"
    except Exception as e:
        traceback.print_exc()
        return f"Recupero non disponibile: {type(e).__name__}: {e}"

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
    from ..analytics.analytics import calculate_summary
    from ..analytics.performance import calculate_performance_score, calculate_recovery_score, calculate_endurance_score, calculate_efficiency_score
    from ..processing.processing import build_segments
    from ..analytics.analytics import create_speed_chart, create_duration_chart
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
