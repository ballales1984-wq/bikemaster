"""add_external_identity_dedup

Revision ID: 9f8e7d6c5b4a
Revises: a1b2c3d4e5f6
Create Date: 2026-06-14 19:50:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = "9f8e7d6c5b4a"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """DELETE FROM rides
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY external_source, external_id
                           ORDER BY id
                       ) AS duplicate_rank
                FROM rides
                WHERE external_source IS NOT NULL AND external_id IS NOT NULL
            ) duplicate_rows
            WHERE duplicate_rank > 1
        )"""
    )
    op.drop_index("ix_rides_external_source", table_name="rides")
    op.create_index(
        "uq_rides_external_identity",
        "rides",
        ["external_source", "external_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_rides_external_identity", table_name="rides")
    op.create_index(
        "ix_rides_external_source",
        "rides",
        ["external_source", "external_id"],
        unique=False,
    )
