"""add_athlete_history_table.

Revision ID: add_athlete_history
Revises: 13a1d54d325f
Create Date: 2026-07-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "add_athlete_history"
down_revision: Union[str, Sequence[str], None] = "13a1d54d325f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "athletes",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "athlete_history",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), server_default="0", nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("picture", sa.String(), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("fat_percentage", sa.Float(), nullable=True),
        sa.Column("years_active", sa.Integer(), nullable=True),
        sa.Column("weekly_sessions", sa.Integer(), nullable=True),
        sa.Column("monthly_hours", sa.Float(), nullable=True),
        sa.Column("annual_hours", sa.Float(), nullable=True),
        sa.Column("experience_level", sa.String(), nullable=True),
        sa.Column("goals", sa.Text(), nullable=True),
        sa.Column("preferred_terrain", sa.Text(), nullable=True),
        sa.Column("weekly_volume_km", sa.Float(), nullable=True),
        sa.Column("best_segments", sa.Text(), nullable=True),
        sa.Column("medical_notes", sa.Text(), nullable=True),
        sa.Column("equipment", sa.Text(), nullable=True),
        sa.Column("ftp_watts", sa.Float(), nullable=True),
        sa.Column("body_water_percentage", sa.Float(), nullable=True),
        sa.Column("muscle_mass_percentage", sa.Float(), nullable=True),
        sa.Column("bmr_kcal", sa.Float(), nullable=True),
        sa.Column("fat_mass_kg", sa.Float(), nullable=True),
        sa.Column("subcutaneous_fat_kg", sa.Float(), nullable=True),
        sa.Column("subcutaneous_fat_percentage", sa.Float(), nullable=True),
        sa.Column("visceral_fat_level", sa.Float(), nullable=True),
        sa.Column("visceral_fat_percentage", sa.Float(), nullable=True),
        sa.Column("visceral_fat_kg", sa.Float(), nullable=True),
        sa.Column("muscle_mass_kg", sa.Float(), nullable=True),
        sa.Column("bone_mass_kg", sa.Float(), nullable=True),
        sa.Column("protein_percentage", sa.Float(), nullable=True),
        sa.Column("protein_kg", sa.Float(), nullable=True),
        sa.Column("body_age", sa.Integer(), nullable=True),
        sa.Column("apparent_age", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_history_athlete_recorded", "athlete_history", ["athlete_id", "recorded_at"]
    )
    op.create_index("ix_history_tenant", "athlete_history", ["tenant_id"])
    op.create_index(
        "ix_athletes_updated_at", "athletes", ["updated_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_history_tenant", table_name="athlete_history")
    op.drop_index("ix_history_athlete_recorded", table_name="athlete_history")
    op.drop_table("athlete_history")
    op.drop_index("ix_athletes_updated_at", table_name="athletes")
    op.drop_column("athletes", "updated_at")
