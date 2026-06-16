"""add_fitness_states table.

Revision ID: add_fitness_states
Revises: 08ee39bfe529
Create Date: 2026-06-16

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "add_fitness_states"
down_revision: str | Sequence[str] | None = "08ee39bfe529"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fitness_states",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("athlete_id", sa.INTEGER(), nullable=False),
        sa.Column("date", sa.String(length=20), nullable=False),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.Column("fitness", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fatigue", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("form", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("atl", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("ctl", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("tsb", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "recovery_hours_needed", sa.Float(), nullable=False, server_default="0.0"
        ),
        sa.Column("weekly_tss", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("monthly_tss", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("trend_7d", sa.String(length=20), nullable=False, server_default="stable"),
        sa.Column("trend_30d", sa.String(length=20), nullable=False, server_default="stable"),
        sa.Column("risk_indicators", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fitness_states_athlete_date", "fitness_states", ["athlete_id", "date"])
    op.create_index("ix_fitness_states_ctl", "fitness_states", ["ctl"])


def downgrade() -> None:
    op.drop_index("ix_fitness_states_ctl", table_name="fitness_states")
    op.drop_index("ix_fitness_states_athlete_date", table_name="fitness_states")
    op.drop_table("fitness_states")