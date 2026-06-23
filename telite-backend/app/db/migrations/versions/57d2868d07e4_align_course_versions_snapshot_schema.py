"""align_course_versions_snapshot_schema

Revision ID: 57d2868d07e4
Revises: 57d2868d07e3
Create Date: 2026-06-21 17:15:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "57d2868d07e4"
down_revision: Union[str, None] = "57d2868d07e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _column_names("course_versions")

    with op.batch_alter_table("course_versions", schema=None) as batch_op:
        if "snapshot_json" not in columns:
            batch_op.add_column(sa.Column("snapshot_json", sa.JSON(), nullable=True))
        if "created_by" in columns:
            batch_op.alter_column(
                "created_by",
                existing_type=sa.String(length=50),
                nullable=True,
            )


def downgrade() -> None:
    columns = _column_names("course_versions")

    with op.batch_alter_table("course_versions", schema=None) as batch_op:
        if "created_by" in columns:
            batch_op.alter_column(
                "created_by",
                existing_type=sa.String(length=50),
                nullable=False,
            )
        if "snapshot_json" in columns:
            batch_op.drop_column("snapshot_json")
