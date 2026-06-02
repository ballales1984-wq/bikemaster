"""
Calorie calculation module for cycling activities.
Based on MET (Metabolic Equivalent of Task) values and cycling physics.
"""

from typing import Optional
from app.models.ride import Ride

def calculate_calories_met(ride: Ride) -> float:
    """
    Calculate calories burned using MET formula.
    MET for cycling varies by speed:
    - <16 km/h: MET = 4.0 (leisurely)
    - 16-19 km/h: MET = 6.0 (moderate)
    - 19-22 km/h: MET = 8.0 (vigorous)
    - >22 km/h: MET = 10.0+ (racing)
    
    Formula: Calories = MET * weight_kg * duration_hours
    """
    speed = ride.avg_speed_kmh
    
    if speed < 16:
        met = 4.0
    elif speed < 19:
        met = 6.0
    elif speed < 22:
        met = 8.0
    else:
        met = 10.0 + (speed - 22) * 0.5  # Increase MET with speed
    
    calories = met * ride.weight_kg * ride.duration_hours
    return calories

def calculate_calories_physics(ride: Ride) -> float:
    """
    Calculate calories based on physics model:
    Power = (Rolling resistance + Air resistance + Gravity resistance) * speed
    Calories = (Power * time) / (human_efficiency * joules_per_calorie)
    """
    # Constants
    g = 9.81  # m/s^2
    crr = 0.005  # coefficient of rolling resistance
    rho = 1.225  # air density kg/m^3
    cdA = 0.4  # drag area m^2 (typical for cyclist on road bike)
    efficiency = 0.25  # human efficiency (25%)
    joules_per_calorie = 4184  # joules in a kilocalorie
    
    # Convert speed to m/s
    speed_ms = ride.avg_speed_kmh * 1000 / 3600
    
    # Weight in Newtons
    weight_n = ride.weight_kg * g
    
    # Forces
    rolling_resistance = crr * weight_n
    air_resistance = 0.5 * rho * cdA * speed_ms**2
    gravity_resistance = 0  # Assume flat terrain for simplicity
    
    # Total power in watts
    power_watts = (rolling_resistance + air_resistance + gravity_resistance) * speed_ms
    
    # Energy in joules
    energy_joules = power_watts * (ride.duration_minutes * 60)
    
    # Convert to calories (accounting for human efficiency)
    calories = energy_joules / (efficiency * joules_per_calorie)
    
    return calories

def estimate_calories(ride: Ride, method: str = "met") -> float:
    """
    Estimate calories burned for a ride.
    
    Args:
        ride: Ride object
        method: Calculation method ("met" or "physics")
    
    Returns:
        Estimated calories burned
    """
    if method == "physics":
        return calculate_calories_physics(ride)
    else:
        return calculate_calories_met(ride)

def calories_per_km(ride: Ride) -> float:
    """Calculate calories burned per kilometer."""
    if ride.distance_km > 0:
        return ride.calories / ride.distance_km
    return 0.0