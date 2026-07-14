import re

src = open("bike_analyzer/backend/api/routes.py", encoding="utf-8").read().splitlines()
funcs = [
    "register", "login", "logout", "refresh_token", "change_password",
    "get_current_user_info", "update_profile", "create_calendar_event",
    "update_calendar_event_endpoint", "delete_calendar_event_endpoint",
    "toggle_event_complete", "create_ride", "list_rides", "get_ride_segments",
    "ride_speed_path", "speed_chart", "distance_chart", "elevation_chart",
    "duration_chart", "get_ride_power_metrics", "get_dashboard", "get_weather",
    "get_weather_forecast", "nearby_places", "search_places_endpoint",
    "google_static_map", "generate_ride_map", "workout_recommendations",
    "recovery_recommendations", "generate_workouts", "ceo_analytics",
    "coach_full_data", "analyze_ride_safety", "get_route_suggestions",
    "get_my_athlete_profile", "reset_demo_data",
]
decos = {}
cur = None
for i, l in enumerate(src, 1):
    m = re.match(r"@router\.(get|post|put|delete|patch)\(([^)]*)\)", l)
    if m:
        path = m.group(2).strip().strip('"').strip("'")
        cur = (m.group(1).upper(), path)
    m2 = re.match(r"\s*async def (\w+)|def (\w+)", l)
    if m2 and cur:
        name = m2.group(1) or m2.group(2)
        if name in funcs:
            decos[name] = cur
        cur = None

for k in funcs:
    if k in decos:
        print(f"{k:34s} {decos[k][0]:6s} {decos[k][1]}")
    else:
        print(f"{k:34s} (not a router endpoint)")
