from bike_analyzer.backend.db.database import get_db_connection, init_db
init_db()
with get_db_connection() as conn:
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print("Tables:", tables)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(rides)").fetchall()]
    print("Ride columns:", cols)
