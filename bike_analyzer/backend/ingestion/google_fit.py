"""Google Fit integration for activity import."""
from __future__ import annotations
import urllib.parse

from ..config import GOOGLE_FIT_SCOPE

def get_authorization_url(client_id: str, redirect_uri: str = "http://localhost:8000/callback", state: str = "") -> str:
    params = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code", "scope": GOOGLE_FIT_SCOPE, "access_type": "offline", "state": state}
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

def exchange_code_for_token(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    import requests
    resp = requests.post("https://oauth2.googleapis.com/token", data={"client_id": client_id, "client_secret": client_secret, "code": code, "grant_type": "authorization_code", "redirect_uri": redirect_uri}, timeout=10)
    resp.raise_for_status()
    return resp.json()

def fetch_cycling_activities(access_token: str) -> list[dict]:
    import requests
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get("https://fitness.googleapis.com/v1/users/me/dataset:aggregate", headers=headers, timeout=10)
    activities = []
    if resp.ok:
        for bucket in resp.json().get("bucket", []):
            for ds in bucket.get("dataset", []):
                activities.append({"startTime": ds.get("startTime"), "endTime": ds.get("endTime"), "value": ds.get("value", [])})
    return activities

def google_fit_to_ride(activities: list[dict]) -> list[dict]:
    rides = []
    for act in activities:
        if "cycling" in str(act).lower():
            duration_ms = 60000
            distance_m = 5000
            for v in act.get("value", []):
                if v.get("intVal"):
                    if "duration" in str(v): duration_ms = v["intVal"]
                    if "distance" in str(v): distance_m = v["intVal"]
            rides.append({"date": act.get("startTime", "")[:10], "distance_km": distance_m / 1000, "duration_minutes": duration_ms / 60000, "avg_speed_kmh": (distance_m / 1000) / (duration_ms / 60000) if duration_ms > 0 else 0})
    return rides