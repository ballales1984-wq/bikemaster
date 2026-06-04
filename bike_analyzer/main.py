"""Main entry point."""
from bike_analyzer.backend.models.models import Ride
from bike_analyzer.backend.analytics.analytics import calculate_summary, analyze_ride

def main():
    rides = [Ride(date="2024-06-01", distance_km=25.3, duration_minutes=65, avg_speed_kmh=22.7, weight_kg=70, calories=420, heart_rate_avg=145, elevation_gain_m=180), Ride(date="2024-06-03", distance_km=42.0, duration_minutes=100, avg_speed_kmh=25.2, weight_kg=70, calories=720, heart_rate_avg=155, elevation_gain_m=320)]
    s = calculate_summary(rides)
    print(f"=== BikeMaster ===\nRides: {s['total_rides']}\nDistance: {s['total_km']:.1f} km\nCalories: {s['total_calories']:.0f} kcal\nAvg Speed: {s['avg_speed']:.1f} km/h\nAvg Fatigue: {s['avg_fatigue']:.1f}/10")

if __name__ == "__main__":
    main()