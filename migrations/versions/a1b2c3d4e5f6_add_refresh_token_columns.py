"""Add refresh token columns (is_revoked, created_at, expires_at, index)

Revision ID: a1b2c3d4e5f6
Revises: 243141eb9881
Create Date: 2026-06-15 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "243141eb9881"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "refreshtoken",
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "refreshtoken",
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "refreshtoken",
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_refreshtoken_hashed_refresh_token",
        "refreshtoken",
        ["hashed_refresh_token"],
    )


def downgrade() -> None:
    op.drop_index("ix_refreshtoken_hashed_refresh_token", table_name="refreshtoken")
    op.drop_column("refreshtoken", "expires_at")
    op.drop_column("refreshtoken", "created_at")
    op.drop_column("refreshtoken", "is_revoked")
