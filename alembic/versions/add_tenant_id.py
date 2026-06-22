"""add tenant_id columns for multi-tenant isolation.

Revision ID: add_tenant_id
Revises: add_fitness_states
Create Date: 2026-06-22

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "add_tenant_id"
down_revision: str | Sequence[str] | None = "add_fitness_states"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("rides", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("athletes", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("chat_history", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("calendar_events", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("training_stress_days", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("metrics", sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_rides_tenant", "rides", ["tenant_id"])
    op.create_index("ix_athletes_tenant", "athletes", ["tenant_id"])
    op.create_index("ix_fitness_states_tenant", "fitness_states", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_fitness_states_tenant", table_name="fitness_states")
    op.drop_index("ix_athletes_tenant", table_name="athletes")
    op.drop_index("ix_rides_tenant", table_name="rides")
    op.drop_column("metrics", "tenant_id")
    op.drop_column("training_stress_days", "tenant_id")
    op.drop_column("calendar_events", "tenant_id")
    op.drop_column("chat_history", "tenant_id")
    op.drop_column("athletes", "tenant_id")
    op.drop_column("rides", "tenant_id")
