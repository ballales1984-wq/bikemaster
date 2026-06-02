"""
Fatigue calculation module for cycling activities.
Estimates fatigue level based on ride intensity, duration, and rider profile.
"""

from typing import Optional
from app.models.ride import Ride

def calculate_fatigue_score(ride: Ride) -> float:
    """
    Calculate fatigue score on a scale of 0-10.
    
    Factors considered:
    - Duration (longer rides = more fatigue)
    - Intensity (higher heart rate % max = more fatigue)
    - Speed (faster = more fatigue)
    - Elevation gain (more climbing = more fatigue)
    - Rider weight (heavier = more fatigue for same effort)
    
    Returns:
        Fatigue score from 0 (no fatigue) to 10 (extreme fatigue)
    """
    # Base fatigue from duration (normalized to 2-hour ride)
    duration_hours = ride.duration_hours
    duration_factor = min(duration_hours / 2.0, 3.0)  # Cap at 3x for very long rides
    
    # Intensity factor based on heart rate (if available)
    intensity_factor = 1.0  # Default
    if ride.heart_rate_avg:
        # Estimate max heart rate (simplified: 220 - age, assuming age 35)
        estimated_max_hr = 220 - 35  # This should be customized per user
        hr_percentage = ride.heart_rate_avg / estimated_max_hr
        # Normalize: 50% HR = 0.5 factor, 85% HR = 1.5 factor, 95%+ HR = 2.0 factor
        if hr_percentage <= 0.5:
            intensity_factor = 0.5
        elif hr_percentage <= 0.85:
            intensity_factor = 0.5 + (hr_percentage - 0.5) * 2.0  # 0.5 to 1.5
        else:
            intensity_factor = 1.5 + (hr_percentage - 0.85) * 3.33  # 1.5 to 2.0
    
    # Speed factor (faster = more fatigue)
    speed_factor = min(ride.avg_speed_kmh / 25.0, 2.0)  # Normalize to 25 km/h, cap at 2x
    
    # Elevation factor (more climbing = more fatigue)
    elevation_factor = 1.0
    if ride.elevation_gain_m and ride.distance_km > 0:
        elevation_per_km = ride.elevation_gain_m / ride.distance_km
        # Normalize: 0m/km = 1.0, 10m/km = 1.5, 20m/km+ = 2.0
        elevation_factor = 1.0 + min(elevation_per_km / 20.0, 1.0)
    
    # Weight factor (heavier riders experience more fatigue)
    weight_factor = ride.weight_kg / 70.0  # Normalize to 70kg reference
    
    # Combine factors (weighted average)
    fatigue_raw = (
        duration_factor * 0.3 +
        intensity_factor * 0.3 +
        speed_factor * 0.2 +
        elevation_factor * 0.1 +
        weight_factor * 0.1
    )
    
    # Scale to 0-10 range
    fatigue_score = min(fatigue_raw * 3.0, 10.0)  # Adjust multiplier as needed
    
    return round(fatigue_score, 1)

def estimate_recovery_hours(fatigue_score: float) -> float:
    """
    Estimate recommended recovery time in hours based on fatigue score.
    
    Args:
        fatigue_score: Fatigue score from 0-10
        
    Returns:
        Recommended recovery hours
    """
    if fatigue_score <= 3.0:
        return 8.0   # Light recovery
    elif fatigue_score <= 5.0:
        return 16.0  # Moderate recovery
    elif fatigue_score <= 7.0:
        return 24.0  # Significant recovery
    else:
        return 48.0  # Extensive recovery needed

def get_recovery_recommendation(fatigue_score: float) -> str:
    """
    Get recovery recommendation based on fatigue score.
    
    Args:
        fatigue_score: Fatigue score from 0-10
        
    Returns:
        Recovery recommendation string
    """
    if fatigue_score <= 2.0:
        return "Minimal fatigue - ready for another ride"
    elif fatigue_score <= 4.0:
        return "Light fatigue - easy recovery ride or rest recommended"
    elif fatigue_score <= 6.0:
        return "Moderate fatigue - rest day or very easy spin recommended"
    elif fatigue_score <= 8.0:
        return "High fatigue - rest day required, focus on recovery"
    else:
        return "Extreme fatigue - multiple rest days recommended, consider light activity only"

def fatigue_level_description(fatigue_score: float) -> str:
    """
    Get descriptive fatigue level.
    
    Args:
        fatigue_score: Fatigue score from 0-10
        
    Returns:
        Fatigue level description
    """
    if fatigue_score <= 2.0:
        return "Very Low"
    elif fatigue_score <= 4.0:
        return "Low"
    elif fatigue_score <= 6.0:
        return "Moderate"
    elif fatigue_score <= 8.0:
        return "High"
    else:
        return "Very High"