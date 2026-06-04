"""AI Coach powered by Groq LLM for cycling advice."""
from __future__ import annotations
import os
from typing import List, Optional
from ..models.models import Ride, AthleteProfile
from .analytics import calculate_summary
from .performance import calculate_performance_score, calculate_recovery_score

def get_ai_coach_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key: raise ValueError("GROQ_API_KEY non impostata nell'ambiente")
    from groq import Groq
    return Groq(api_key=api_key)

def generate_training_advice(athlete: AthleteProfile, rides: List[Ride]) -> str:
    try:
        client = get_ai_coach_client()
        summary = calculate_summary(rides) if rides else {}
        perf = calculate_performance_score(rides[-1]) if rides else 0
        recovery = calculate_recovery_score(rides[-1]) if rides else 0
        prompt = f"You are BikeMaster AI Coach. Atleta: {athlete.name}, livello: {athlete.experience_level}, peso: {athlete.weight_kg}kg. Ultimi dati: performance={perf}/10, recovery={recovery}/10. Fornisci 3 consigli brevi per l'allenamento oggi."
        chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], max_tokens=200)
        return chat.choices[0].message.content or "Nessun consiglio disponibile"
    except Exception:
        return "AI Coach non disponibile. Imposta GROQ_API_KEY."

def generate_recovery_advice(athlete: AthleteProfile, rides: List[Ride]) -> str:
    try:
        client = get_ai_coach_client()
        recovery = calculate_recovery_score(rides[-1]) if rides else 5
        prompt = f"Sei BikeMaster Recovery Coach. Recovery score: {recovery}/10. Dai un consiglio breve per recupero oggi (stretching, idratazione, sonno)."
        chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], max_tokens=100)
        return chat.choices[0].message.content or "Recupera bene!"
    except Exception:
        return "Idratazione e stretching raccomandati."

def analyze_historical_trend(rides: List[Ride]) -> str:
    if len(rides) < 2: return "Dati insufficienti per trend."
    from .fatigue import calculate_fatigue_score
    avg_fatigue = sum(calculate_fatigue_score(r) for r in rides) / len(rides)
    avg_perf = sum(calculate_performance_score(r) for r in rides) / len(rides)
    trend = "crescente" if avg_perf > 5 else "stabile" if avg_perf > 3 else "da monitorare"
    return f"Trend: {trend}, fatigue media: {avg_fatigue:.1f}/10, performance media: {avg_perf:.1f}/10"

def ai_coach_full(athlete: AthleteProfile, rides: List[Ride]) -> dict:
    return {"training_advice": generate_training_advice(athlete, rides), "recovery_advice": generate_recovery_advice(athlete, rides), "historical_analysis": analyze_historical_trend(rides)}