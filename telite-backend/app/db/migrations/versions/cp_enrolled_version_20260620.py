"""add_enrolled_version_to_course_progress

Revision ID: cp_enrolled_version_20260620
Revises: assignment_v1_rls_force_20260620
Create Date: 2026-06-20 17:15:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "cp_enrolled_version_20260620"
down_revision: Union[str, None] = "assignment_v1_rls_force_20260620"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column("course_progress", "enrolled_version"):
        op.add_column(
            "course_progress",
            sa.Column(
                "enrolled_version",
                sa.Integer(),
                nullable=True,
                comment="The published version number the learner is pinned to",
            ),
        )


def downgrade() -> None:
    if _has_column("course_progress", "enrolled_version"):
        op.drop_column("course_progress", "enrolled_version")
