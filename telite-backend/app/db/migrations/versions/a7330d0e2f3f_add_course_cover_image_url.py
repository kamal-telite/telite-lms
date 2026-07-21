"""add_course_cover_image_url

Revision ID: a7330d0e2f3f
Revises: 4cc311cff7e4
Create Date: 2026-07-20 17:53:24.901895

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7330d0e2f3f'
down_revision: Union[str, None] = '4cc311cff7e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [column["name"] for column in inspector.get_columns("courses")]

    if "cover_image_url" not in columns:
        op.add_column(
            "courses",
            sa.Column(
                "cover_image_url",
                sa.String(length=500),
                nullable=True,
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [column["name"] for column in inspector.get_columns("courses")]

    if "cover_image_url" in columns:
        op.drop_column("courses", "cover_image_url")

