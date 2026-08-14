"""Reproduce the OAuth user_creation_failed path against a local PostgreSQL.

Mirrors the exact sequence used by google_code_exchange/_create_athlete in
routes.py (lines ~1965-2032): save_athlete -> update_athlete(tenant_id) -> get_athlete.
"""
import os, traceback

os.environ["DATABASE_URL"] = "postgresql://postgres@127.0.0.1:5433/postgres"
os.environ["GOOGLE_CLIENT_ID"] = "x"
os.environ["GOOGLE_CLIENT_SECRET"] = "x"

from bike_analyzer.backend.db.async_db import init_async_db
import asyncio
asyncio.run(init_async_db())
print("schema created")

from bike_analyzer.backend.db.postgres_athlete import (
    has_postgres, save_athlete, get_athlete, get_athlete_by_email, update_athlete
)
print("has_postgres =", has_postgres())

# The exact dict built in routes.py google_code_exchange _create_athlete()
oauth_athlete = {
    "name": "Test OAuth User",
    "email": "oauth-repro@example.com",
    "picture": "https://example.com/pic.png",
    "experience_level": "Beginner",
}

def _create_athlete():
    result = get_athlete_by_email(oauth_athlete["email"])
    if not result:
        athlete_id = save_athlete(oauth_athlete)
        print("save_athlete returned", athlete_id)
        if athlete_id:
            try:
                update_athlete(athlete_id, {"tenant_id": athlete_id})
                print("update_athlete OK")
            except Exception as e:
                print("update_athlete warning:", type(e).__name__, e)
            result = get_athlete(athlete_id)
            print("get_athlete returned:", result)
            if result is None and athlete_id:
                result = {"id": athlete_id}
    return result

try:
    r = _create_athlete()
    print("FINAL result:", r)
except Exception:
    print("=== EXCEPTION RAISED (would trigger user_creation_failed) ===")
    traceback.print_exc()
