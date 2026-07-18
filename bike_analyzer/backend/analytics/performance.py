"""Performance Engine: Scoring system for cycling performance."""

from __future__ import annotations

from ..models.models import AthleteProfile, Ride
from .fatigue import calculate_fatigue_score


def calculate_performance_score(ride: Ride) -> float:
    """Punteggio di performance (0-10) di una singola uscita.

    Combina velocità (40%), durata (40%) e dislivello (20%) normalizzati su
    soglie (30 km/h, 2 h, 500 m), poi scala su 10. Premia uscite veloci,
    lunghe e con salite.
    """
    speed_factor = min(ride.avg_speed_kmh / 30.0, 1.0)
    duration_factor = min(ride.duration_hours / 2.0, 1.0)
    elevation_factor = min(ride.elevation_gain_m / 500.0, 1.0) if ride.elevation_gain_m else 0
    return round((speed_factor * 0.4 + duration_factor * 0.4 + elevation_factor * 0.2) * 10.0, 1)


def calculate_endurance_score(rides: list[Ride]) -> float:
    """Punteggio di resistenza (0-10) su tutto lo storico dell'atleta.

    Peso: proporzione di uscite "lunghe" >=2h (40%), costanza nel numero di
    uscite (30%, satura a 20) e volume totale (30%, satura a 500 km).
    """
    if not rides:
        return 0.0
    long_rides = sum(1 for r in rides if r.duration_hours >= 2.0)
    long_ride_ratio = long_rides / len(rides)
    consistency = min(len(rides) / 20.0, 1.0)
    total_distance = sum(r.distance_km for r in rides)
    distance_factor = min(total_distance / 500.0, 1.0)
    return round((long_ride_ratio * 0.4 + consistency * 0.3 + distance_factor * 0.3) * 10.0, 1)


def calculate_recovery_score(ride: Ride) -> float:
    """Punteggio di recupero (0-10): inverso della fatica della stessa uscita."""
    fatigue = calculate_fatigue_score(ride)
    return round(10.0 - fatigue, 1)


def calculate_efficiency_score(ride: Ride) -> float:
    """Efficienza energetica (0-10): quanto poco kcal/km rispetto al benchmark.

    kcal/km sotto i 30 (benchmark) dà 10; sopra, decresce linearmente di 1 punto
    ogni 5 kcal/km in eccesso (clamp a 0). Meno calorie per km = più efficiente.
    """
    if ride.distance_km <= 0:
        return 0.0
    calories_per_km = ride.calories / ride.distance_km
    benchmark = 30.0
    efficiency = max(0, min(10, 10 - (calories_per_km - benchmark) / 5.0))
    return round(efficiency, 1)


def calculate_monthly_scores(rides: list[Ride]) -> dict:
    """Aggrega gli score medi (performance, endurance, recovery, efficiency, fatica) sul mese."""

    return {
        "performance": round(sum(calculate_performance_score(r) for r in rides) / len(rides), 1),
        "endurance": calculate_endurance_score(rides),
        "recovery": round(sum(calculate_recovery_score(r) for r in rides) / len(rides), 1),
        "efficiency": round(sum(calculate_efficiency_score(r) for r in rides) / len(rides), 1),
        "avg_fatigue": round(sum(calculate_fatigue_score(r) for r in rides) / len(rides), 1),
    }


def calculate_annual_scores(rides: list[Ride]) -> dict:
    """Aggrega score annuali + totali (km, kcal, fatica media) sullo storico."""
    if not rides:
        return {
            "performance": 0,
            "endurance": 0,
            "total_km": 0,
            "total_calories": 0,
            "avg_fatigue": 0,
        }
    from .analytics import calculate_summary

    s = calculate_summary(rides)
    return {
        "performance": round(sum(calculate_performance_score(r) for r in rides) / len(rides), 1),
        "endurance": calculate_endurance_score(rides),
        "total_km": s["total_km"],
        "total_calories": s["total_calories"],
        "avg_fatigue": s["avg_fatigue"],
    }


def classify_athlete(rides: list[Ride]) -> str:
    """Classifica l'atleta per volume (km totali e n° uscite) in 5 livelli.

    Beginner → Amateur → Intermediate → Advanced → Elite, con soglie crescenti
    su km e numero di uscite.
    """
    if not rides:
        return "Unclassified"
    total_km = sum(r.distance_km for r in rides)
    total_rides = len(rides)
    if total_km < 100 and total_rides < 10:
        return "Beginner"
    if total_km < 500 and total_rides < 50:
        return "Amateur"
    if total_km < 1500 and total_rides < 150:
        return "Intermediate"
    if total_km < 3000:
        return "Advanced"
    return "Elite"


def get_experience_level(athlete: AthleteProfile) -> str:
    """Ritorna il livello di esperienza dichiarato nel profilo atleta."""
    return athlete.experience_level


def should_save_to_database(points: list) -> bool:
    """True se tutti i GPS point superano la validazione (coordinate + timestamp)."""
    from ..processing.processing import validate_gps_point

    return all(validate_gps_point(p) for p in points) if points else False
