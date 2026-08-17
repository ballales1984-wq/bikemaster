"""Convert rides.activity_type from activitytype enum to TEXT.

Revision ID: convert_activity_type_to_text
Revises: add_aethermap_tables
Create Date: 2026-08-17

"""
from collections.abc import Sequence

from alembic import op

revision: str = "convert_activity_type_to_text"
down_revision: str | Sequence[str] | None = "add_aethermap_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
            ALTER TABLE rides
                ALTER COLUMN activity_type TYPE TEXT
                USING activity_type::TEXT
            """
        )
        op.execute("DROP TYPE IF EXISTS activitytype")


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE TYPE activitytype AS ENUM (
                'ride', 'run', 'hike', 'virtual_ride', 'virtual_run', 'swim', 'other'
            )
            """
        )
        op.execute(
            """
            ALTER TABLE rides
                ALTER COLUMN activity_type TYPE activitytype
                USING activity_type::activitytype
            """
        )
