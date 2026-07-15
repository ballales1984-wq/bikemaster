"""initial_models

Revision ID: 08ee39bfe529
Revises:
Create Date: 2026-07-15

Local-first schema: SQLite init_db() is the source of truth.
This migration creates the same tables for PostgreSQL cloud sync.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "08ee39bfe529"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("PRAGMA foreign_keys=ON")

    op.create_table(
        "users",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("username", sa.TEXT(), nullable=False),
        sa.Column("email", sa.TEXT(), nullable=True),
        sa.Column("password_hash", sa.TEXT(), nullable=True),
        sa.Column("is_admin", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("is_active", sa.INTEGER(), server_default="1", nullable=False),
        sa.Column("created_at", sa.TEXT(), nullable=True),
        sa.Column("updated_at", sa.TEXT(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "athletes",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("name", sa.TEXT(), nullable=False),
        sa.Column("email", sa.TEXT(), nullable=True),
        sa.Column("picture", sa.TEXT(), nullable=True),
        sa.Column("age", sa.INTEGER(), server_default="30", nullable=False),
        sa.Column("weight_kg", sa.Float(), server_default="70", nullable=False),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("fat_percentage", sa.Float(), nullable=True),
        sa.Column("years_active", sa.INTEGER(), server_default="1", nullable=False),
        sa.Column("weekly_sessions", sa.INTEGER(), server_default="3", nullable=False),
        sa.Column("monthly_hours", sa.Float(), server_default="0", nullable=False),
        sa.Column("annual_hours", sa.Float(), server_default="0", nullable=False),
        sa.Column("experience_level", sa.TEXT(), server_default="Beginner", nullable=False),
        sa.Column("goals", sa.TEXT(), nullable=True),
        sa.Column("preferred_terrain", sa.TEXT(), nullable=True),
        sa.Column("weekly_volume_km", sa.Float(), server_default="0", nullable=False),
        sa.Column("best_segments", sa.TEXT(), nullable=True),
        sa.Column("medical_notes", sa.TEXT(), nullable=True),
        sa.Column("equipment", sa.TEXT(), nullable=True),
        sa.Column("ftp_watts", sa.Float(), nullable=True),
        sa.Column("password_hash", sa.TEXT(), nullable=True),
        sa.Column("tenant_id", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("created_at", sa.TEXT(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_athletes_experience_level", "athletes", ["experience_level"], unique=False)
    op.create_index("ix_athletes_name", "athletes", ["name"], unique=False)
    op.create_index("ix_athletes_tenant", "athletes", ["tenant_id"], unique=False)

    op.create_table(
        "rides",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("athlete_id", sa.INTEGER(), nullable=True),
        sa.Column("tenant_id", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("date", sa.String(length=20), nullable=False),
        sa.Column("distance_km", sa.Float(), server_default="0", nullable=False),
        sa.Column("duration_minutes", sa.Float(), server_default="0", nullable=False),
        sa.Column("avg_speed_kmh", sa.Float(), server_default="0", nullable=False),
        sa.Column("weight_kg", sa.Float(), server_default="70", nullable=False),
        sa.Column("calories", sa.Float(), server_default="0", nullable=False),
        sa.Column("heart_rate_avg", sa.Float(), nullable=True),
        sa.Column("elevation_gain_m", sa.Float(), nullable=True),
        sa.Column("gps_points", sa.TEXT(), nullable=True),
        sa.Column("activity_type", sa.TEXT(), server_default="ride", nullable=False),
        sa.Column("is_official", sa.INTEGER(), server_default="1", nullable=False),
        sa.Column("source", sa.TEXT(), server_default="manual", nullable=False),
        sa.Column("external_source", sa.TEXT(), nullable=True),
        sa.Column("external_id", sa.TEXT(), nullable=True),
        sa.Column("title", sa.TEXT(), nullable=True),
        sa.Column("created_at", sa.TEXT(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rides_athlete_date", "rides", ["athlete_id", "date"], unique=False)
    op.create_index("ix_rides_athlete_id", "rides", ["athlete_id"], unique=False)
    op.create_index("ix_rides_date", "rides", ["date"], unique=False)
    op.create_index("ix_rides_distance", "rides", ["distance_km"], unique=False)
    op.create_index("ix_rides_elevation", "rides", ["elevation_gain_m"], unique=False)
    op.create_index("ix_rides_tenant", "rides", ["tenant_id"], unique=False)

    op.create_table(
        "chat_history",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("athlete_id", sa.INTEGER(), nullable=True),
        sa.Column("tenant_id", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("role", sa.TEXT(), nullable=False),
        sa.Column("content", sa.TEXT(), nullable=False),
        sa.Column("created_at", sa.TEXT(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "calendar_events",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("athlete_id", sa.INTEGER(), nullable=True),
        sa.Column("tenant_id", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("title", sa.TEXT(), nullable=False),
        sa.Column("event_type", sa.TEXT(), server_default="training", nullable=False),
        sa.Column("date", sa.TEXT(), nullable=False),
        sa.Column("duration_minutes", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("completed", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("weather_temp", sa.Float(), nullable=True),
        sa.Column("weather_humidity", sa.Float(), nullable=True),
        sa.Column("weather_description", sa.TEXT(), nullable=True),
        sa.Column("created_at", sa.TEXT(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_calendar_events_athlete_id", "calendar_events", ["athlete_id"], unique=False)
    op.create_index("ix_calendar_events_date", "calendar_events", ["date"], unique=False)
    op.create_index("ix_calendar_events_tenant", "calendar_events", ["tenant_id"], unique=False)

    op.create_table(
        "weather_cache",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("date", sa.TEXT(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("humidity", sa.Float(), nullable=True),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("cached_at", sa.TEXT(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lat", "lon", "date", name="uq_weather_cache"),
    )

    op.create_table(
        "training_stress_days",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("athlete_id", sa.INTEGER(), nullable=False),
        sa.Column("date", sa.TEXT(), nullable=False),
        sa.Column("tss", sa.Float(), nullable=True),
        sa.Column("atl", sa.Float(), nullable=True),
        sa.Column("ctl", sa.Float(), nullable=True),
        sa.Column("tsb", sa.Float(), nullable=True),
        sa.Column("created_at", sa.TEXT(), nullable=True),
        sa.Column("updated_at", sa.TEXT(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("athlete_id", "date", name="uq_training_stress_days"),
    )

    op.create_table(
        "metrics",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("athlete_id", sa.INTEGER(), nullable=True),
        sa.Column("ride_id", sa.INTEGER(), nullable=True),
        sa.Column("fatigue_score", sa.Float(), nullable=True),
        sa.Column("recovery_hours", sa.Float(), nullable=True),
        sa.Column("calories_per_km", sa.Float(), nullable=True),
        sa.Column("efficiency_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.TEXT(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.ForeignKeyConstraint(["ride_id"], ["rides.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_metrics_ride", "metrics", ["ride_id"], unique=False)
    op.create_index("ix_metrics_athlete_id", "metrics", ["athlete_id"], unique=False)

    op.create_table(
        "training_goals",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("athlete_id", sa.INTEGER(), nullable=False),
        sa.Column("tenant_id", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("title", sa.TEXT(), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("goal_type", sa.TEXT(), server_default="granfondo", nullable=False),
        sa.Column("target_date", sa.TEXT(), nullable=True),
        sa.Column("target_distance_km", sa.Float(), nullable=True),
        sa.Column("target_elevation_m", sa.Float(), nullable=True),
        sa.Column("status", sa.TEXT(), server_default="active", nullable=False),
        sa.Column("created_at", sa.TEXT(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "planned_workouts",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("athlete_id", sa.INTEGER(), nullable=False),
        sa.Column("tenant_id", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("goal_id", sa.INTEGER(), nullable=True),
        sa.Column("date", sa.TEXT(), nullable=False),
        sa.Column("title", sa.TEXT(), nullable=False),
        sa.Column("workout_type", sa.TEXT(), server_default="endurance", nullable=False),
        sa.Column("duration_minutes", sa.INTEGER(), server_default="60", nullable=False),
        sa.Column("target_intensity", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("completed", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("completed_at", sa.TEXT(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.ForeignKeyConstraint(["goal_id"], ["training_goals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "road_incidents",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("source_id", sa.TEXT(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("incident_date", sa.TEXT(), nullable=False),
        sa.Column("severity", sa.TEXT(), server_default="medium", nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("road_type", sa.TEXT(), nullable=True),
        sa.Column("source", sa.TEXT(), server_default="local", nullable=False),
        sa.Column("created_at", sa.TEXT(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "source", name="uq_road_incidents"),
    )

    op.create_table(
        "route_safety_scores",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("ride_id", sa.INTEGER(), nullable=True),
        sa.Column("athlete_id", sa.INTEGER(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("label", sa.TEXT(), nullable=True),
        sa.Column("advice", sa.TEXT(), nullable=True),
        sa.Column("road_type_counts", sa.TEXT(), nullable=True),
        sa.Column("has_bike_infrastructure", sa.INTEGER(), nullable=True),
        sa.Column("incident_count", sa.INTEGER(), nullable=True),
        sa.Column("route_length_km", sa.Float(), nullable=True),
        sa.Column("computed_at", sa.TEXT(), nullable=True),
        sa.Column("tenant_id", sa.INTEGER(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["ride_id"], ["rides.id"]),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_route_safety_scores_tenant", "route_safety_scores", ["tenant_id"], unique=False)

    op.create_table(
        "pois",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("name", sa.TEXT(), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("type", sa.TEXT(), nullable=False),
        sa.Column("photos", sa.TEXT(), nullable=True),
        sa.Column("video_url", sa.TEXT(), nullable=True),
        sa.Column("difficulty_note", sa.TEXT(), nullable=True),
        sa.Column("tags", sa.TEXT(), nullable=True),
        sa.Column("itinerary_id", sa.INTEGER(), nullable=True),
        sa.Column("created_by", sa.INTEGER(), nullable=True),
        sa.Column("tenant_id", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("created_at", sa.TEXT(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_pois_coords", "pois", ["lat", "lon"], unique=False)

    op.create_table(
        "fitness_states",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("athlete_id", sa.INTEGER(), nullable=True),
        sa.Column("tenant_id", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("date", sa.TEXT(), nullable=False),
        sa.Column("computed_at", sa.TEXT(), nullable=True),
        sa.Column("fitness", sa.Float(), server_default="0", nullable=False),
        sa.Column("fatigue", sa.Float(), server_default="0", nullable=False),
        sa.Column("form", sa.Float(), server_default="0", nullable=False),
        sa.Column("atl", sa.Float(), server_default="0", nullable=False),
        sa.Column("ctl", sa.Float(), server_default="0", nullable=False),
        sa.Column("tsb", sa.Float(), server_default="0", nullable=False),
        sa.Column("recovery_hours_needed", sa.Float(), server_default="0", nullable=False),
        sa.Column("weekly_tss", sa.Float(), server_default="0", nullable=False),
        sa.Column("monthly_tss", sa.Float(), server_default="0", nullable=False),
        sa.Column("trend_7d", sa.TEXT(), server_default="stable", nullable=False),
        sa.Column("trend_30d", sa.TEXT(), server_default="stable", nullable=False),
        sa.Column("risk_indicators", sa.TEXT(), nullable=True),
        sa.Column("recommendation", sa.TEXT(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_fitness_states_athlete", "fitness_states", ["athlete_id"], unique=False)
    op.create_index("ix_fitness_states_tenant", "fitness_states", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_fitness_states_tenant", table_name="fitness_states")
    op.drop_index("idx_fitness_states_athlete", table_name="fitness_states")
    op.drop_table("fitness_states")

    op.drop_index("idx_pois_coords", table_name="pois")
    op.drop_table("pois")

    op.drop_index("ix_route_safety_scores_tenant", table_name="route_safety_scores")
    op.drop_table("route_safety_scores")

    op.drop_table("road_incidents")

    op.drop_table("planned_workouts")
    op.drop_table("training_goals")

    op.drop_index("idx_metrics_ride", table_name="metrics")
    op.drop_index("ix_metrics_athlete_id", table_name="metrics")
    op.drop_table("metrics")

    op.drop_table("training_stress_days")

    op.drop_table("weather_cache")

    op.drop_index("ix_calendar_events_tenant", table_name="calendar_events")
    op.drop_index("ix_calendar_events_date", table_name="calendar_events")
    op.drop_index("ix_calendar_events_athlete_id", table_name="calendar_events")
    op.drop_table("calendar_events")

    op.drop_table("chat_history")

    op.drop_index("ix_rides_tenant", table_name="rides")
    op.drop_index("ix_rides_elevation", table_name="rides")
    op.drop_index("ix_rides_distance", table_name="rides")
    op.drop_index("ix_rides_date", table_name="rides")
    op.drop_index("ix_rides_athlete_id", table_name="rides")
    op.drop_index("ix_rides_athlete_date", table_name="rides")
    op.drop_table("rides")

    op.drop_index("ix_athletes_tenant", table_name="athletes")
    op.drop_index("ix_athletes_name", table_name="athletes")
    op.drop_index("ix_athletes_experience_level", table_name="athletes")
    op.drop_table("athletes")

    op.drop_table("users")
