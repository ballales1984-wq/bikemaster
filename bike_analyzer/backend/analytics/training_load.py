"""ATL/CTL/TSB fitness-fatigue model for cycling training."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from dataclasses import dataclass
from ..models.models import Ride


@dataclass
class TrainingLoadDay:
    date: str
    tss: float
    atl: float = 0.0
    ctl: float = 0.0
    tsb: float = 0.0


def calculate_rss(ride: Ride, ftp: Optional[float] = None) -> float:
    """Calculate Ride Stress Score (similar to TSS without power meter).
    
    Uses duration, intensity factor, and elevation to estimate training load.
    """
    duration_h = ride.duration_hours
    if duration_h <= 0:
        return 0.0
    
    intensity = ride.intensity_factor if hasattr(ride, 'intensity_factor') else 0.5
    elevation_factor = 0.0
    if ride.elevation_gain_m and ride.distance_km > 0:
        elevation_factor = min(ride.elevation_gain_m / ride.distance_km / 100.0, 1.0)
    
    tss = duration_h * 3600 * (intensity + elevation_factor) / 3600
    return round(min(tss, 200.0), 1)


def calculate_atl_ctl_tsb(rides: List[Ride], ftp: Optional[float] = None, target_date: Optional[str] = None) -> List[TrainingLoadDay]:
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
    
    first_date = datetime.fromisoformat(dates[0])
    end_date = datetime.fromisoformat(target_date[:10]) if target_date else datetime.now()
    
    all_dates = []
    current = first_date
    while current <= end_date:
        all_dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    result: List[TrainingLoadDay] = []
    
    for i, date in enumerate(all_dates):
        tss = daily_tss.get(date, 0.0)
        
        if i == 0:
            atl = tss
            ctl = tss
        else:
            prev_atl = result[i - 1].atl
            prev_ctl = result[i - 1].ctl
            
            atl = prev_atl * 6.0 / 7.0 + tss * 1.0 / 7.0
            ctl = prev_ctl * 41.0 / 42.0 + tss * 1.0 / 42.0
        
        tsb = ctl - atl
        
        result.append(TrainingLoadDay(
            date=date,
            tss=tss,
            atl=round(atl, 1),
            ctl=round(ctl, 1),
            tsb=round(tsb, 1)
        ))
    
    return result


def get_current_training_status(rides: List[Ride], ftp: Optional[float] = None) -> dict:
    """Get current ATL/CTL/TSB values and training recommendation."""
    if not rides:
        return {"atl": 0.0, "ctl": 0.0, "tsb": 0.0, "status": "no_data", "recommendation": "Start recording your rides"}
    
    load_history = calculate_atl_ctl_tsb(rides, ftp)
    if not load_history:
        return {"atl": 0.0, "ctl": 0.0, "tsb": 0.0, "status": "no_data", "recommendation": "Insufficient data"}
    
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
    
    return {
        "atl": atl,
        "ctl": ctl,
        "tsb": tsb,
        "status": status,
        "recommendation": recommendation
    }


def get_7day_fitness_summary(rides: List[Ride], ftp: Optional[float] = None) -> List[dict]:
    """Get ATL/CTL/TSB for last 7 days as list of dicts for API responses."""
    load_history = calculate_atl_ctl_tsb(rides, ftp)
    if not load_history:
        return []
    
    recent = load_history[-7:] if len(load_history) >= 7 else load_history
    return [
        {"date": d.date, "atl": d.atl, "ctl": d.ctl, "tsb": d.tsb, "tss": d.tss}
        for d in recent
    ]


__all__ = [
    "calculate_rss",
    "calculate_atl_ctl_tsb", 
    "get_current_training_status",
    "get_7day_fitness_summary",
    "TrainingLoadDay"
]