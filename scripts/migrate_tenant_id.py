"""Migration script: add multi-user tenant_id coverage to SQLite tables.

Ensures all tables have tenant_id column and adds composite indexes
for tenant-scoped queries.
"""

from __future__ import annotations

import sqlite3

DB_PATH = "rides.db"


def migrate():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        cur = conn.cursor()

        tables_to_check = [
            ("metrics", "tenant_id"),
            ("route_safety_scores", "tenant_id"),
            ("fitness_states", "tenant_id"),
            ("training_stress_days", "tenant_id"),
            ("training_goals", "tenant_id"),
            ("planned_workouts", "tenant_id"),
            ("strava_tokens", "tenant_id"),
            ("garmin_tokens", "tenant_id"),
            ("knowledge_chunks", "tenant_id"),
            ("chat_messages", "tenant_id"),
        ]

        for table, column in tables_to_check:
            cur.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cur.fetchall()]
            if column not in columns:
                default_val = "0"
                if table in ("metrics", "route_safety_scores"):
                    default_val = "0"
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER DEFAULT {default_val}")
                print(f"  Added {column} to {table}")

        indexes = [
            ("idx_metrics_athlete_tenant", "metrics", "athlete_id, tenant_id"),
            ("idx_route_safety_tenant", "route_safety_scores", "ride_id, tenant_id"),
            ("idx_fitness_states_tenant", "fitness_states", "athlete_id, tenant_id"),
            ("idx_training_stress_tenant", "training_stress_days", "athlete_id, tenant_id"),
            ("idx_training_goals_tenant", "training_goals", "athlete_id, tenant_id"),
            ("idx_planned_workouts_tenant", "planned_workouts", "athlete_id, tenant_id"),
        ]

        for idx_name, table, cols in indexes:
            try:
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({cols})")
                print(f"  Created index {idx_name}")
            except sqlite3.OperationalError as exc:
                print(f"  Index {idx_name}: {exc}")

        conn.commit()
        print("Migration completed.")


if __name__ == "__main__":
    migrate()
