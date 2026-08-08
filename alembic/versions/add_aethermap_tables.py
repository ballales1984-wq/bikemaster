"""add_aethermap_tables

Revision ID: add_aethermap_tables
Revises: 12b75e7d9eda
Create Date: 2026-08-08

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "add_aethermap_tables"
down_revision: str | Sequence[str] | None = "12b75e7d9eda"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        op.execute("CREATE EXTENSION IF NOT EXISTS hstore")

    if not inspector.has_table("aethermap_objects"):
        op.create_table(
            "aethermap_objects",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("tipo", sa.String(), nullable=False),
            sa.Column("lat", sa.Float(), nullable=False),
            sa.Column("lon", sa.Float(), nullable=False),
            sa.Column("alt", sa.Float(), server_default="0.0"),
            sa.Column("s2", sa.String(), nullable=True),
            sa.Column("h3", sa.String(), nullable=True),
            sa.Column("cube_face", sa.Integer(), nullable=True),
            sa.Column("cube_u", sa.Float(), nullable=True),
            sa.Column("cube_v", sa.Float(), nullable=True),
            sa.Column("data", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_aethermap_objects_tipo", "aethermap_objects", ["tipo"])
        op.create_index("ix_aethermap_objects_s2", "aethermap_objects", ["s2"])
        op.create_index("ix_aethermap_objects_h3", "aethermap_objects", ["h3"])

    if not inspector.has_table("aethermap_state_history"):
        op.create_table(
            "aethermap_state_history",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("object_id", sa.String(), nullable=False),
            sa.Column("campi", sa.JSON(), nullable=False),
            sa.Column("t", sa.DateTime(), nullable=False),
            sa.Column("confidence", sa.Float(), server_default="1.0"),
            sa.ForeignKeyConstraint(["object_id"], ["aethermap_objects.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_aethermap_state_history_object_id", "aethermap_state_history", ["object_id"])
        op.create_index("ix_aethermap_state_history_t", "aethermap_state_history", ["t"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("aethermap_state_history"):
        op.drop_index("ix_aethermap_state_history_t", table_name="aethermap_state_history")
        op.drop_index("ix_aethermap_state_history_object_id", table_name="aethermap_state_history")
        op.drop_table("aethermap_state_history")

    if inspector.has_table("aethermap_objects"):
        op.drop_index("ix_aethermap_objects_h3", table_name="aethermap_objects")
        op.drop_index("ix_aethermap_objects_s2", table_name="aethermap_objects")
        op.drop_index("ix_aethermap_objects_tipo", table_name="aethermap_objects")
        op.drop_table("aethermap_objects")
