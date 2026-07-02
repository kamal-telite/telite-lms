"""add_org_invitations_metadata_json

Revision ID: h8d2e5f9a642
Revises: h8d2e5f9a641
Create Date: 2026-06-27 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h8d2e5f9a642"
down_revision: Union[str, None] = "h8d2e5f9a641"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [column["name"] for column in inspector.get_columns("org_invitations")]
    if "metadata_json" not in columns:
        op.add_column("org_invitations", sa.Column("metadata_json", sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [column["name"] for column in inspector.get_columns("org_invitations")]
    if "metadata_json" in columns:
        op.drop_column("org_invitations", "metadata_json")
