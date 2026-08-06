"""add_missing_athlete_body_columns

Revision ID: 12b75e7d9eda
Revises: merge_hr_tracking_head
Create Date: 2026-08-05 22:29:12.237548

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12b75e7d9eda'
down_revision: Union[str, Sequence[str], None] = 'merge_hr_tracking_head'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_BODY_COMPOSITION_COLS = [
    ("body_water_percentage", sa.Float(), None),
    ("muscle_mass_percentage", sa.Float(), None),
    ("bmr_kcal", sa.Float(), None),
    ("fat_mass_kg", sa.Float(), None),
    ("subcutaneous_fat_kg", sa.Float(), None),
    ("subcutaneous_fat_percentage", sa.Float(), None),
    ("visceral_fat_level", sa.Float(), None),
    ("visceral_fat_percentage", sa.Float(), None),
    ("visceral_fat_kg", sa.Float(), None),
    ("muscle_mass_kg", sa.Float(), None),
    ("bone_mass_kg", sa.Float(), None),
    ("protein_percentage", sa.Float(), None),
    ("protein_kg", sa.Float(), None),
    ("body_age", sa.Integer(), None),
    ("apparent_age", sa.Integer(), None),
    ("bmi", sa.Float(), None),
    ("lean_body_mass_kg", sa.Float(), None),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def _has_col(table_name, col_name):
        if not inspector.has_table(table_name):
            return False
        return any(c["name"] == col_name for c in inspector.get_columns(table_name))

    for col_name, col_type, _ in _BODY_COMPOSITION_COLS:
        if not _has_col("athletes", col_name):
            op.add_column("athletes", sa.Column(col_name, col_type, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def _has_col(table_name, col_name):
        if not inspector.has_table(table_name):
            return False
        return any(c["name"] == col_name for c in inspector.get_columns(table_name))

    for col_name, _, _ in reversed(_BODY_COMPOSITION_COLS):
        if _has_col("athletes", col_name):
            op.drop_column("athletes", col_name)
