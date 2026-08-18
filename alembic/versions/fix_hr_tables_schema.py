"""Fix HR tables schema drift on Render.

The SQLAlchemy models in ``db/models.py`` originally defined ``hr_24h_samples``
with ``timestamp`` / ``hr_bpm`` columns and ``hr_monitoring_settings`` without
the ``enabled`` / ``interval_seconds`` / ``source`` / ``device_id`` /
``created_at`` columns. Because the hub startup path on Render only runs
``init_async_db()`` (SQLAlchemy ``create_all``) and not Alembic migrations,
tables created by those stale models end up with the wrong schema and break
every PostgreSQL HR endpoint (500).

This migration repairs existing tables and also serves as the authoritative
``CREATE TABLE`` for fresh deployments.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision: str = "fix_hr_tables_schema"
down_revision: str | Sequence[str] | None = "convert_activity_type_to_text"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(c["name"] == column_name for c in inspector.get_columns(table_name))


def upgrade() -> None:
    with op.get_context().autocommit_block():
        if not _has_column("hr_24h_samples", "heart_rate"):
            if not inspect(op.get_bind()).has_table("hr_24h_samples"):
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
                    sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
                    sa.PrimaryKeyConstraint("id"),
                )
                op.create_index(
                    "idx_hr_samples_athlete_recorded",
                    "hr_24h_samples",
                    ["athlete_id", "recorded_at"],
                )
                op.create_index(
                    "idx_hr_samples_athlete_date",
                    "hr_24h_samples",
                    ["athlete_id"],
                )
            else:
                if _has_column("hr_24h_samples", "timestamp"):
                    op.execute(
                        "ALTER TABLE hr_24h_samples RENAME COLUMN timestamp TO recorded_at"
                    )
                if _has_column("hr_24h_samples", "hr_bpm"):
                    op.execute(
                        "ALTER TABLE hr_24h_samples RENAME COLUMN hr_bpm TO heart_rate"
                    )
                if not _has_column("hr_24h_samples", "device_id"):
                    op.add_column(
                        "hr_24h_samples",
                        sa.Column("device_id", sa.String(), nullable=True),
                    )
                if not _has_column("hr_24h_samples", "source"):
                    op.add_column(
                        "hr_24h_samples",
                        sa.Column("source", sa.String(), server_default="ble"),
                    )
                if not _has_column("hr_24h_samples", "tenant_id"):
                    op.add_column(
                        "hr_24h_samples",
                        sa.Column("tenant_id", sa.Integer(), server_default="0"),
                    )

        if not _has_column("hr_monitoring_settings", "enabled"):
            if not inspect(op.get_bind()).has_table("hr_monitoring_settings"):
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
                    sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
                    sa.PrimaryKeyConstraint("id"),
                    sa.UniqueConstraint("athlete_id"),
                )
                op.create_index(
                    "idx_hr_settings_athlete",
                    "hr_monitoring_settings",
                    ["athlete_id"],
                )
            else:
                for col_name, col_type in [
                    ("enabled", sa.INTEGER()),
                    ("interval_seconds", sa.INTEGER()),
                    ("source", sa.String()),
                    ("device_id", sa.String()),
                    ("created_at", sa.String()),
                ]:
                    if not _has_column("hr_monitoring_settings", col_name):
                        op.add_column(
                            "hr_monitoring_settings",
                            sa.Column(col_name, col_type, nullable=True),
                        )


def downgrade() -> None:
    pass
