"""ATL/CTL/TSB fitness-fatigue model for cycling training."""

from __future__ import annotations

from dataclasses import dataclass

from ..models.models import Ride


@dataclass
class TrainingLoadDay:
    """Singolo giorno del modello carico-allenamento con ATL/CTL/TSB."""

    date: str
    tss: float
    atl: float = 0.0
    ctl: float = 0.0
    tsb: float = 0.0


def calculate_rss(ride: Ride, ftp: float | None = None) -> float:
    """Calcola il Training Stress Score (TSS) per una singola uscita."""
    duration_h = ride.duration_hours
    if duration_h <= 0:
        return 0.0
    if ftp is None or ftp <= 0:
        ftp = 250.0
    if_val = 0.5
    if ride.avg_speed_kmh and ride.avg_speed_kmh > 0:
        if_val = min(ride.avg_speed_kmh / 40.0, 1.0)
    if ride.heart_rate_avg and ride.heart_rate_avg > 0:
        hr_pct = ride.heart_rate_avg / 190.0
        if_val = max(if_val, min(hr_pct / 0.9, 1.2))
    tss = duration_h * 100.0 * (if_val ** 2)
    return round(min(tss, 500.0), 1)


def calculate_atl_ctl_tsb(
    rides: list[Ride], ftp: float | None = None, target_date: str | None = None
) -> list[TrainingLoadDay]:
    """Calculate Acute Training Load (ATL), Chronic Training Load (CTL), and Training Stress Balance (TSB).

    Uses Banister's impulse-response model with 7-day ATL and 42-day CTL time constants.
    TSB = CTL - ATL (positive = fresh, negative = fatigued)
    """
    if not rides:
        return []

    sorted_rides = sorted(rides, key=lambda r: r.date)

    daily_tss: dict[str, float] = {}
    for ride in sorted_rides:
        date_key = ride.date[:10] if len(ride.date) >= 10 else ride.date
        tss = calculate_rss(ride, ftp)
        daily_tss[date_key] = daily_tss.get(date_key, 0.0) + tss

    dates = sorted(daily_tss.keys())
    if not dates:
        return []

    result: list[TrainingLoadDay] = []

    for i, date in enumerate(dates):
        tss = daily_tss[date]

        if i == 0:
            atl = tss
            ctl = tss
        else:
            prev_atl = result[i - 1].atl
            prev_ctl = result[i - 1].ctl

            atl = prev_atl * 6.0 / 7.0 + tss * 1.0 / 7.0
            ctl = prev_ctl * 41.0 / 42.0 + tss * 1.0 / 42.0

        tsb = ctl - atl

        result.append(TrainingLoadDay(date=date, tss=tss, atl=round(atl, 1), ctl=round(ctl, 1), tsb=round(tsb, 1)))

    return result


def get_current_training_status(rides: list[Ride], ftp: float | None = None) -> dict:
    """Get current ATL/CTL/TSB values and training recommendation."""
    if not rides:
        return {
            "atl": 0.0,
            "ctl": 0.0,
            "tsb": 0.0,
            "status": "no_data",
            "recommendation": "Start recording your rides",
        }

    load_history = calculate_atl_ctl_tsb(rides, ftp)
    if not load_history:
        return {
            "atl": 0.0,
            "ctl": 0.0,
            "tsb": 0.0,
            "status": "no_data",
            "recommendation": "Insufficient data",
        }

    latest = load_history[-1]
    atl, ctl, tsb = latest.atl, latest.ctl, latest.tsb

    if tsb > 10:
        status = "fresh"
        recommendation = "You're well rested. Intense training recommended today."
    elif tsb > 0:
        status = "optimal"
        recommendation = "Ideal state for quality training."
    elif tsb > -10:
        status = "fatigued"
        recommendation = "Light training or recovery recommended."
    elif tsb > -20:
        status = "overreached"
        recommendation = "Urgent recovery needed. Reduce volume/intensity."
    else:
        status = "burnout_risk"
        recommendation = "Overtraining risk. Total rest for 2-3 days."

    return {"atl": atl, "ctl": ctl, "tsb": tsb, "status": status, "recommendation": recommendation}


def get_7day_fitness_summary(rides: list[Ride], ftp: float | None = None) -> list[dict]:
    """Get ATL/CTL/TSB for last 7 days as list of dicts for API responses."""
    load_history = calculate_atl_ctl_tsb(rides, ftp)
    if not load_history:
        return []

    recent = load_history[-7:] if len(load_history) >= 7 else load_history
    return [{"date": d.date, "atl": d.atl, "ctl": d.ctl, "tsb": d.tsb, "tss": d.tss} for d in recent]


__all__ = [
    "calculate_rss",
    "calculate_atl_ctl_tsb",
    "get_current_training_status",
    "get_7day_fitness_summary",
    "TrainingLoadDay",
]
