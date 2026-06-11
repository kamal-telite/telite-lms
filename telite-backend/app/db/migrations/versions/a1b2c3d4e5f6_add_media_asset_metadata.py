"""add_media_asset_metadata

Revision ID: a1b2c3d4e5f6
Revises: f0d1c2b3a4e5
Create Date: 2026-06-10 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f0d1c2b3a4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("media_assets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("folder", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("tags_json", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("media_assets", schema=None) as batch_op:
        batch_op.drop_column("tags_json")
        batch_op.drop_column("folder")
