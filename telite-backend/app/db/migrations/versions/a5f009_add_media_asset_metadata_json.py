"""add_media_asset_metadata_json

Revision ID: a5f009
Revises: a5f008
Create Date: 2026-06-16 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a5f009"
down_revision: Union[str, None] = "a5f008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    columns = [c["name"] for c in insp.get_columns("media_assets")]
    if "metadata_json" not in columns:
        op.add_column("media_assets", sa.Column("metadata_json", sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    columns = [c["name"] for c in insp.get_columns("media_assets")]
    if "metadata_json" in columns:
        op.drop_column("media_assets", "metadata_json")
