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
from sqlalchemy import inspect

from alembic import op

revision: str = "cf_tenant_id_consolidated"
down_revision: str | Sequence[str] | None = "add_fitness_states"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(c["name"] == column_name for c in inspector.get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def _add_tenant_id(table_name: str, index_name: str) -> None:
    if not inspect(op.get_bind()).has_table(table_name):
        return
    if not _has_column(table_name, "tenant_id"):
        op.add_column(
            table_name,
            sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"),
        )
    if not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, ["tenant_id"])


def upgrade() -> None:
    _add_tenant_id("athletes", "ix_athletes_tenant")
    _add_tenant_id("rides", "ix_rides_tenant")
    _add_tenant_id("fitness_states", "ix_fitness_states_tenant")
    _add_tenant_id("calendar_events", "ix_calendar_events_tenant")
    _add_tenant_id("chat_history", "ix_chat_history_tenant")
    _add_tenant_id("training_stress_days", "ix_training_stress_days_tenant")
    _add_tenant_id("metrics", "ix_metrics_tenant")
    _add_tenant_id("training_goals", "ix_training_goals_tenant")
    _add_tenant_id("planned_workouts", "ix_planned_workouts_tenant")
    _add_tenant_id("knowledge_chunks", "ix_knowledge_chunks_tenant")
    _add_tenant_id("strava_tokens", "ix_strava_tokens_tenant")
    _add_tenant_id("garmin_tokens", "ix_garmin_tokens_tenant")
    _add_tenant_id("route_safety_scores", "ix_route_safety_scores_tenant")


def downgrade() -> None:
    for table_name, index_name in [
        ("route_safety_scores", "ix_route_safety_scores_tenant"),
        ("garmin_tokens", "ix_garmin_tokens_tenant"),
        ("strava_tokens", "ix_strava_tokens_tenant"),
        ("knowledge_chunks", "ix_knowledge_chunks_tenant"),
        ("planned_workouts", "ix_planned_workouts_tenant"),
        ("training_goals", "ix_training_goals_tenant"),
        ("metrics", "ix_metrics_tenant"),
        ("training_stress_days", "ix_training_stress_days_tenant"),
        ("chat_history", "ix_chat_history_tenant"),
        ("calendar_events", "ix_calendar_events_tenant"),
        ("fitness_states", "ix_fitness_states_tenant"),
        ("rides", "ix_rides_tenant"),
        ("athletes", "ix_athletes_tenant"),
    ]:
        if _has_index(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)
        if _has_column(table_name, "tenant_id"):
            op.drop_column(table_name, "tenant_id")
