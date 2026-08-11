"""Training load analytics — ATL/CTL/TSB recalculation."""

from __future__ import annotations

from ..models.models import Ride
from ..db.database import get_rides_by_athlete, upsert_training_stress_day
from .training_stress import estimate_tss, exponentially_weighted_moving_average


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
