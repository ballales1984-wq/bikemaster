"""consolidate_tenant_id

Consolidates duplicate tenant_id migrations into a single authoritative migration.
Previously split across add_tenant_id (6 tables) and abc123def456 (13 tables),
now unified. Also fixes missing tenant_id column on fitness_states.

Revision ID: cf_tenant_id_consolidated
Revises: add_fitness_states
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "cf_tenant_id_consolidated"
down_revision: str | Sequence[str] | None = "add_fitness_states"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("athletes", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_athletes_tenant", "athletes", ["tenant_id"])

    op.add_column("rides", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_rides_tenant", "rides", ["tenant_id"])

    op.add_column("fitness_states", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_fitness_states_tenant", "fitness_states", ["tenant_id"])

    op.add_column("calendar_events", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_calendar_events_tenant", "calendar_events", ["tenant_id"])

    op.add_column("chat_history", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_chat_history_tenant", "chat_history", ["tenant_id"])

    op.add_column("training_stress_days", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_training_stress_days_tenant", "training_stress_days", ["tenant_id"])

    op.add_column("metrics", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_metrics_tenant", "metrics", ["tenant_id"])

    op.add_column("training_goals", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_training_goals_tenant", "training_goals", ["tenant_id"])

    op.add_column("planned_workouts", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_planned_workouts_tenant", "planned_workouts", ["tenant_id"])

    op.add_column("knowledge_chunks", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_knowledge_chunks_tenant", "knowledge_chunks", ["tenant_id"])

    op.add_column("strava_tokens", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_strava_tokens_tenant", "strava_tokens", ["tenant_id"])

    op.add_column("garmin_tokens", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_garmin_tokens_tenant", "garmin_tokens", ["tenant_id"])

    op.add_column("route_safety_scores", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_route_safety_scores_tenant", "route_safety_scores", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_route_safety_scores_tenant", table_name="route_safety_scores")
    op.drop_column("route_safety_scores", "tenant_id")

    op.drop_index("ix_garmin_tokens_tenant", table_name="garmin_tokens")
    op.drop_column("garmin_tokens", "tenant_id")

    op.drop_index("ix_strava_tokens_tenant", table_name="strava_tokens")
    op.drop_column("strava_tokens", "tenant_id")

    op.drop_index("ix_knowledge_chunks_tenant", table_name="knowledge_chunks")
    op.drop_column("knowledge_chunks", "tenant_id")

    op.drop_index("ix_planned_workouts_tenant", table_name="planned_workouts")
    op.drop_column("planned_workouts", "tenant_id")

    op.drop_index("ix_training_goals_tenant", table_name="training_goals")
    op.drop_column("training_goals", "tenant_id")

    op.drop_index("ix_metrics_tenant", table_name="metrics")
    op.drop_column("metrics", "tenant_id")

    op.drop_index("ix_training_stress_days_tenant", table_name="training_stress_days")
    op.drop_column("training_stress_days", "tenant_id")

    op.drop_index("ix_chat_history_tenant", table_name="chat_history")
    op.drop_column("chat_history", "tenant_id")

    op.drop_index("ix_calendar_events_tenant", table_name="calendar_events")
    op.drop_column("calendar_events", "tenant_id")

    op.drop_index("ix_fitness_states_tenant", table_name="fitness_states")
    op.drop_column("fitness_states", "tenant_id")

    op.drop_index("ix_rides_tenant", table_name="rides")
    op.drop_column("rides", "tenant_id")

    op.drop_index("ix_athletes_tenant", table_name="athletes")
    op.drop_column("athletes", "tenant_id")
