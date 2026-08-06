"""change pois.type from enum poitype to string/varchar.

Revision ID: change_pois_type_to_string
Revises: add_athlete_history
Create Date: 2026-07-26
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "change_pois_type_to_string"
down_revision: str | Sequence[str] | None = "add_athlete_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE pois ALTER COLUMN type TYPE VARCHAR USING type::text")
        op.execute("DROP TYPE IF EXISTS poitype")
    elif bind.dialect.name == "sqlite":
        with op.batch_alter_table("pois") as batch_op:
            batch_op.alter_column("type", type_=sa.String())


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE TYPE poitype AS ENUM ('viewpoint','fountain','refuge','junction','danger','cultural','technical','parking','other')"
        )
        op.execute("ALTER TABLE pois ALTER COLUMN type TYPE poitype USING type::poitype")
    elif bind.dialect.name == "sqlite":
        with op.batch_alter_table("pois") as batch_op:
            batch_op.alter_column("type", type_=sa.String())
