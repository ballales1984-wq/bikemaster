"""Migration script to set tenant_id = athlete_id for existing rows.

This migrates data from the old single-tenant model to the new multi-tenant model.
Run this script once after deploying the multi-tenant changes.

Usage:
    python scripts/migrate_tenant_id.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DEFAULT_DB_PATH = "rides.db"


def migrate(db_path: str = DEFAULT_DB_PATH) -> dict:
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        return {"status": "error", "message": "database not found"}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    updates = {}

    tables_with_tenant = [
        ("athletes", "id"),
        ("rides", "id"),
        ("calendar_events", "id"),
        ("chat_history", "id"),
        ("training_stress_days", "id"),
        ("metrics", "id"),
        ("training_goals", "id"),
        ("planned_workouts", "id"),
        ("knowledge_chunks", "id"),
        ("chat_messages", "id"),
        ("strava_tokens", "id"),
        ("garmin_tokens", "id"),
        ("route_safety_scores", "id"),
    ]

    for table, pk in tables_with_tenant:
        try:
            cur.execute(f"PRAGMA table_info({table})")
            columns = [row["name"] for row in cur.fetchall()]
            if "tenant_id" not in columns:
                print(f"  SKIP {table}: tenant_id column not found")
                continue
            if "athlete_id" not in columns:
                print(f"  SKIP {table}: athlete_id column not found")
                continue

            cur.execute(
                f"SELECT COUNT(*) FROM {table} WHERE tenant_id = 0 OR tenant_id IS NULL"
            )
            count = cur.fetchone()[0]

            if count > 0:
                cur.execute(
                    f"UPDATE {table} SET tenant_id = athlete_id "
                    f"WHERE tenant_id = 0 OR tenant_id IS NULL"
                )
                conn.commit()
                updates[table] = cur.rowcount
                print(f"  OK {table}: updated {cur.rowcount} rows")
            else:
                updates[table] = 0
                print(f"  OK {table}: no rows to update")
        except sqlite3.OperationalError as exc:
            print(f"  ERR {table}: {exc}")
            updates[table] = f"error: {exc}"

    conn.close()
    return {"status": "completed", "updates": updates}


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH
    print(f"Migrating tenant_id in {db_path}...")
    result = migrate(db_path)
    print(f"\nResult: {result}")
