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
    if not rides:
        return {
            "performance": 0.0,
            "endurance": 0.0,
            "recovery": 0.0,
            "efficiency": 0.0,
            "avg_fatigue": 0.0,
        }

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


def calculate_normalized_power(power_stream: list[float], rolling_s: int = 30) -> float | None:
    """Normalized Power (NP): media della 4° potenza su finestra mobile 30s, alla 1/4.

    Richiede uno stream di potenza (W) campionato a 1 Hz. Se lo stream e' vuoto o
    piatto (tutti i valori uguali), ritorna None perche' NP non e' definita.
    """
    if not power_stream or len(power_stream) < rolling_s:
        return None
    valid = [p for p in power_stream if p is not None and p >= 0]
    if not valid:
        return None

    # Media mobile su finestra rolling_s secondi (campioni = secondi a 1 Hz).
    rolling_avg: list[float] = []
    for i in range(len(valid)):
        window = valid[max(0, i - rolling_s + 1) : i + 1]
        rolling_avg.append(sum(window) / len(window))

    if not rolling_avg:
        return None
    mean_4th = sum(p**4 for p in rolling_avg) / len(rolling_avg)
    return round(mean_4th**0.25, 1)


def calculate_intensity_factor(normalized_power: float | None, ftp: float | None) -> float | None:
    """Intensity Factor (IF): NP / FTP. None se FTP mancante o non valido."""
    if not normalized_power or not ftp or ftp <= 0:
        return None
    return round(normalized_power / ftp, 3)


def calculate_tss(
    normalized_power: float | None,
    ftp: float | None,
    duration_seconds: float | None,
    intensity_factor: float | None = None,
) -> float | None:
    """Training Stress Score: (sec * NP * IF) / (FTP * 3600) * 100.

    ACCETTA l'IF pre-calcolato oppure lo deriva da NP/FTP. None se dati mancanti.
    """
    if duration_seconds is None or duration_seconds <= 0:
        return None
    if intensity_factor is None:
        intensity_factor = calculate_intensity_factor(normalized_power, ftp)
    if intensity_factor is None or not ftp or ftp <= 0:
        return None
    np_eff = normalized_power or (intensity_factor * ftp)
    return round((duration_seconds * np_eff * intensity_factor) / (ftp * 3600.0) * 100.0, 1)


def estimate_ftp_from_test(
    test_power: float,
    test_duration_min: float = 20.0,
    ftp_fraction: float = 0.95,
) -> float | None:
    """Stima FTP da un test di soglia.

    Default: media potenza su 20 min * 0.95 (test standard 20-min FTP).
    Per test da 60 min usare ftp_fraction=1.0; per 8 min usare ~0.90.
    """
    if not test_power or test_power <= 0:
        return None
    if test_duration_min <= 0:
        return None
    return round(test_power * ftp_fraction, 1)


def estimate_ftp_from_ride(
    power_stream: list[float],
    duration_seconds: float | None = None,
    ftp_fraction: float = 0.95,
) -> float | None:
    """Stima FTP da un'uscita: NP della power zone piu' lunga * frazione.

    Euristica semplificata: usa la NP dell'intera uscita come proxy del test di
    soglia e la scalai con ftp_fraction. Ritorna None se lo stream e' insufficiente.
    """
    if not duration_seconds or duration_seconds < 600:  # almeno 10 min
        return None
    np_value = calculate_normalized_power(power_stream)
    if not np_value:
        return None
    return round(np_value * ftp_fraction, 1)


def calculate_power_metrics(
    power_stream: list[float],
    ftp: float | None,
    duration_seconds: float | None,
) -> dict:
    """Aggrega tutti i metricatori di potenza per un'uscita in un unico dict.

    Campi: average_power, normalized_power, intensity_factor, tss.
    I campi non calcolabili sono None.
    """
    if not power_stream:
        return {
            "average_power": None,
            "normalized_power": None,
            "intensity_factor": None,
            "tss": None,
        }
    valid = [p for p in power_stream if p is not None and p >= 0]
    avg = round(sum(valid) / len(valid), 1) if valid else None
    np_value = calculate_normalized_power(power_stream)
    if_count = calculate_intensity_factor(np_value, ftp)
    tss = calculate_tss(np_value, ftp, duration_seconds, if_count)
    return {
        "average_power": avg,
        "normalized_power": np_value,
        "intensity_factor": if_count,
        "tss": tss,
    }


__all__ = [
    "calculate_performance_score",
    "calculate_endurance_score",
    "calculate_recovery_score",
    "calculate_efficiency_score",
    "calculate_monthly_scores",
    "calculate_annual_scores",
    "classify_athlete",
    "get_experience_level",
    "should_save_to_database",
    "calculate_normalized_power",
    "calculate_intensity_factor",
    "calculate_tss",
    "estimate_ftp_from_test",
    "estimate_ftp_from_ride",
    "calculate_power_metrics",
]
