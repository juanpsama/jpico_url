"""create clickevent table

Revision ID: a2b3c4d5e6f7
Revises: 0b7218384886
Create Date: 2026-06-15 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "0b7218384886"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clickevent",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("url_map_id", sa.Integer(), nullable=False),
        sa.Column("clicked_at", sa.DateTime(), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("referer", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["url_map_id"], ["urlmap.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clickevent_url_map_id", "clickevent", ["url_map_id"])


def downgrade() -> None:
    op.drop_index("ix_clickevent_url_map_id", table_name="clickevent")
    op.drop_table("clickevent")
