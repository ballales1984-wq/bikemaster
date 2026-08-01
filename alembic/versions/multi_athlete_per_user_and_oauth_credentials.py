"""multi_athlete_per_user_and_oauth_credentials

Revision ID: multi_athlete_per_user_and_oauth_credentials
Revises: change_pois_type_to_string
Create Date: 2026-08-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "multi_athlete_per_user_and_oauth_credentials"
down_revision: Union[str, Sequence[str], None] = "change_pois_type_to_string"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        try:
            with op.batch_alter_table("athletes", schema=None) as batch_op:
                batch_op.drop_constraint("uq_athletes_user_id", type_="unique")
        except Exception:
            pass

    op.create_table(
        "user_oauth_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("client_id", sa.String(), nullable=True),
        sa.Column("client_secret", sa.String(), nullable=True),
        sa.Column("redirect_uri", sa.String(), nullable=True),
        sa.Column("scope", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_oauth_credentials_user_provider"),
    )
    op.create_index("ix_user_oauth_credentials_user", "user_oauth_credentials", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_oauth_credentials_user", table_name="user_oauth_credentials")
    op.drop_table("user_oauth_credentials")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        try:
            with op.batch_alter_table("athletes", schema=None) as batch_op:
                batch_op.create_unique_constraint("uq_athletes_user_id", ["user_id"])
        except Exception:
            pass
