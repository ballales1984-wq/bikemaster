"""add_hr_24h_tracking_tables

Revision ID: add_hr_24h_tracking
Revises: bbe692252c5e
Create Date: 2026-08-02

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_hr_24h_tracking"
down_revision: str | Sequence[str] | None = "bbe692252c5e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "hr_24h_samples",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("athlete_id", sa.INTEGER(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("heart_rate", sa.INTEGER(), nullable=False),
        sa.Column("source", sa.String(), nullable=False, server_default="ble"),
        sa.Column("device_id", sa.String(), nullable=True),
        sa.Column("recorded_at", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes(id)", ], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_hr_samples_athlete_recorded", "hr_24h_samples", ["athlete_id", "recorded_at"])
    op.create_index("idx_hr_samples_athlete_date", "hr_24h_samples", ["athlete_id"])

    op.create_table(
        "hr_monitoring_settings",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("athlete_id", sa.INTEGER(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.INTEGER(), nullable=False, server_default="1"),
        sa.Column("interval_seconds", sa.INTEGER(), nullable=False, server_default="30"),
        sa.Column("source", sa.String(), nullable=False, server_default="ble"),
        sa.Column("device_id", sa.String(), nullable=True),
        sa.Column("max_hr", sa.INTEGER(), nullable=True),
        sa.Column("resting_hr", sa.INTEGER(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
        sa.Column("updated_at", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes(id", ], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("athlete_id"),
    )
    op.create_index("idx_hr_settings_athlete", "hr_monitoring_settings", ["athlete_id"])


def downgrade() -> None:
    op.drop_index("idx_hr_settings_athlete", table_name="hr_monitoring_settings")
    op.drop_table("hr_monitoring_settings")
    op.drop_index("idx_hr_samples_athlete_date", table_name="hr_24h_samples")
    op.drop_index("idx_hr_samples_athlete_recorded", table_name="hr_24h_samples")
    op.drop_table("hr_24h_samples")
