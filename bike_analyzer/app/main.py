from app.data.loader import load_rides
from app.core.analytics import calculate_summary

def run_app():
    """Main application entry point."""
    rides = load_rides()
    
    if not rides:
        print("No ride data found.")
        return
    
    summary = calculate_summary(rides)
    
    print("=== Cycling Analysis Summary ===")
    print(f"Total rides: {summary['total_rides']}")
    print(f"Total distance: {summary['total_km']:.1f} km")
    print(f"Total calories: {summary['total_calories']:.0f} kcal")
    print(f"Average speed: {summary['avg_speed']:.1f} km/h")
    print(f"Average fatigue: {summary['avg_fatigue']:.1f}/10")

if __name__ == "__main__":
    run_app()