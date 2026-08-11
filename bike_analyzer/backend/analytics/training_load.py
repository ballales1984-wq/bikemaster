"""Training load analytics — ATL/CTL/TSB recalculation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...core.models import Ride
from ..db.repositories.ride_repository import get_rides_by_athlete
from ..db.repositories.training_stress_repository import upsert_training_stress_day
from .training_stress import estimate_tss, exponentially_weighted_moving_average


@dataclass
class TrainingLoadDay:
    """Daily training load metrics."""

    date: str
    tss: float
    atl: float
    ctl: float
    tsb: float


def recalculate_training_stress_for_athlete(athlete_id: int, ftp: float = 250.0, tenant_id: int = 0) -> None:
    """Ricalcola ATL/CTL/TSB storici per tutti i giorni con attivita' dell'atleta.

    Per ogni giorno calcola il TSS cumulato, poi applica due EWMA:
    - ATL ( Acute Training Load ) con tau di 7 giorni.
    - CTL ( Chronic Training Load ) con tau di 42 giorni.
    Il TSB ( Form ) e' la differenza CTL - ATL.

    I risultati vengono salvati/aggiornati nella tabella
    ``training_stress_days`` tramite ``upsert_training_stress_day``.
    """
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id, tenant_id)]
    if not rides:
        return
    daily: dict[str, float] = {}
    for ride in rides:
        tss = estimate_tss(ride, ftp=ftp)
        day = ride.date[:10] if ride.date else "unknown"
        daily[day] = daily.get(day, 0.0) + tss
    sorted_days = sorted(daily.items())
    tss_series = [v for _, v in sorted_days]
    atl_series = [
        exponentially_weighted_moving_average(tss_series[: i + 1], tau_days=7.0) for i in range(len(tss_series))
    ]
    ctl_series = [
        exponentially_weighted_moving_average(tss_series[: i + 1], tau_days=42.0) for i in range(len(tss_series))
    ]
    for i, (date_str, _) in enumerate(sorted_days):
        tsb = round(ctl_series[i] - atl_series[i], 1)
        upsert_training_stress_day(
            athlete_id,
            date_str,
            round(tss_series[i], 1),
            atl_series[i],
            ctl_series[i],
            tsb,
            tenant_id,
        )


def _normalize_rides(rides: Any) -> list[Ride]:
    """Accetta una singola Ride o una lista e restituisce sempre una lista."""
    if hasattr(rides, "date") and hasattr(rides, "duration_minutes"):
        return [rides]
    return list(rides)


def calculate_atl_ctl_tsb(rides: Ride | list[Ride], ftp: float = 250.0) -> list[TrainingLoadDay]:
    """Calcola ATL, CTL, TSB per ogni giorno basandosi sulle ride fornite.

    Restituisce una lista di ``TrainingLoadDay`` ordinati per data crescente.
    """
    rides = _normalize_rides(rides)
    if not rides:
        return []

    daily: dict[str, float] = {}
    for ride in rides:
        tss = estimate_tss(ride, ftp=ftp)
        day = ride.date[:10] if ride.date else "unknown"
        daily[day] = daily.get(day, 0.0) + tss

    sorted_days = sorted(daily.items())
    tss_series = [v for _, v in sorted_days]
    atl_series = [
        exponentially_weighted_moving_average(tss_series[: i + 1], tau_days=7.0) for i in range(len(tss_series))
    ]
    ctl_series = [
        exponentially_weighted_moving_average(tss_series[: i + 1], tau_days=42.0) for i in range(len(tss_series))
    ]

    result: list[TrainingLoadDay] = []
    for i, (date_str, tss) in enumerate(sorted_days):
        result.append(
            TrainingLoadDay(
                date=date_str,
                tss=round(tss, 1),
                atl=round(atl_series[i], 1),
                ctl=round(ctl_series[i], 1),
                tsb=round(ctl_series[i] - atl_series[i], 1),
            )
        )
    return result


def calculate_rss(rides: Ride | list[Ride], ftp: float = 250.0) -> float:
    """Calcola il Recovery Stress Score (RSS) cumulato per le ride fornite.

    Il RSS e' la somma dei TSS pesati per un fattore di recupero basato sui giorni
    trascorsi dalla ride piu' recente.
    """
    rides = _normalize_rides(rides)
    if not rides:
        return 0.0

    loads = calculate_atl_ctl_tsb(rides, ftp=ftp)
    if not loads:
        return 0.0

    from datetime import datetime, UTC

    latest_date = max(datetime.fromisoformat(load.date) for load in loads)
    rss = 0.0
    for load in loads:
        ride_date = datetime.fromisoformat(load.date)
        days_ago = max((latest_date - ride_date).days, 0)
        recovery_factor = 1.0 / (1.0 + days_ago * 0.1)
        rss += load.tss * recovery_factor

    return round(rss, 1)


def get_current_training_status(rides: Ride | list[Ride], ftp: float = 250.0) -> dict[str, Any]:
    """Restituisce lo stato attuale di allenamento basato sulle ride recenti.

    Include ATL/CTL/TSB correnti e una raccomandazione testuale.
    """
    rides = _normalize_rides(rides)
    if not rides:
        return {"ctl": 0.0, "atl": 0.0, "tsb": 0.0, "status": "no_data", "recommendation": "No recent rides."}

    loads = calculate_atl_ctl_tsb(rides, ftp=ftp)
    if not loads:
        return {"ctl": 0.0, "atl": 0.0, "tsb": 0.0, "status": "no_data", "recommendation": "No recent rides."}

    current = loads[-1]
    tsb = current.tsb
    if tsb > 10:
        status = "fresh"
        recommendation = "You are well recovered. Ready for a hard session."
    elif tsb > 0:
        status = "balanced"
        recommendation = "Good balance between load and recovery."
    elif tsb > -10:
        status = "fatigued"
        recommendation = "Mild fatigue detected. Consider a recovery day."
    else:
        status = "overreaching"
        recommendation = "High fatigue. Rest or very light activity recommended."

    return {
        "ctl": current.ctl,
        "atl": current.atl,
        "tsb": tsb,
        "status": status,
        "recommendation": recommendation,
    }


def get_7day_fitness_summary(rides: Ride | list[Ride], ftp: float = 250.0) -> dict[str, Any] | list[Any]:
    """Restituisce un summary di fitness per gli ultimi 7 giorni.

    Per input vuoto restituisce lista vuota per compatibilita' con le attese dei test.
    """
    rides = _normalize_rides(rides)
    if not rides:
        return []

    from datetime import UTC, datetime, timedelta

    cutoff = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    recent = [r for r in rides if r.date and r.date >= cutoff]
    if not recent:
        return []

    loads = calculate_atl_ctl_tsb(recent, ftp=ftp)
    total_tss = sum(load.tss for load in loads)
    current = loads[-1]

    return {
        "rides": len(recent),
        "total_tss": round(total_tss, 1),
        "avg_tss": round(total_tss / len(recent), 1) if recent else 0.0,
        "ctl": current.ctl,
        "atl": current.atl,
        "tsb": current.tsb,
        "status": get_current_training_status(recent, ftp=ftp)["status"],
    }
