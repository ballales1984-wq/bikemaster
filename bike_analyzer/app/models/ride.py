from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Ride:
    """Model representing a cycling ride."""
    date: str
    distance_km: float
    duration_minutes: float
    avg_speed_kmh: float
    weight_kg: float
    calories: float
    heart_rate_avg: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create a Ride instance from a dictionary."""
        return cls(
            date=data.get('date'),
            distance_km=float(data.get('distance_km', 0)),
            duration_minutes=float(data.get('duration_minutes', 0)),
            avg_speed_kmh=float(data.get('avg_speed_kmh', 0)),
            weight_kg=float(data.get('weight_kg', 0)),
            calories=float(data.get('calories', 0)),
            heart_rate_avg=data.get('heart_rate_avg'),
            elevation_gain_m=data.get('elevation_gain_m')
        )
    
    def to_dict(self) -> dict:
        """Convert Ride instance to dictionary."""
        return {
            'date': self.date,
            'distance_km': self.distance_km,
            'duration_minutes': self.duration_minutes,
            'avg_speed_kmh': self.avg_speed_kmh,
            'weight_kg': self.weight_kg,
            'calories': self.calories,
            'heart_rate_avg': self.heart_rate_avg,
            'elevation_gain_m': self.elevation_gain_m
        }
    
    @property
    def duration_hours(self) -> float:
        """Get duration in hours."""
        return self.duration_minutes / 60.0
    
    @property
    def speed_kmh(self) -> float:
        """Alias for avg_speed_kmh."""
        return self.avg_speed_kmh