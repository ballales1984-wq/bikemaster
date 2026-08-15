import os
import sqlite3

from bike_analyzer.backend.db.database import init_db

db_path = "test_debug22.db"
os.environ["DB_PATH"] = db_path
init_db()

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute(
    "INSERT INTO rides (athlete_id, tenant_id, date, distance_km, duration_minutes, "
    "weight_kg, calories, gps_points, activity_type, is_official, source, created_at) "
    "VALUES (0, 0, ?, 25.0, 60.0, 70, 0, ?, ?, 1, ?, datetime('now'))",
    ("2024-06-15", '[{"lat": 45.0, "lon": 7.0}]', "ride", "manual"),
)
conn.commit()
cur.execute("SELECT * FROM rides WHERE id = 1")
row = cur.fetchone()
print("gps_points type:", type(row[11]))
print("gps_points value:", row[11])
