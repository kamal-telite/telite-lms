"""add_task_assignment_generation_tracking

Revision ID: task_gen_20260731
Revises: theme_pref_20260619
Create Date: 2026-07-31 13:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "task_gen_20260731"
down_revision: Union[str, None] = "theme_pref_20260619"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [column["name"] for column in inspector.get_columns("tasks")]

    if "assignment_generation_status" not in columns:
        op.add_column(
            "tasks",
            sa.Column(
                "assignment_generation_status",
                sa.String(length=20),
                nullable=False,
                server_default="completed",
            ),
        )

    if "generation_started_at" not in columns:
        op.add_column(
            "tasks",
            sa.Column(
                "generation_started_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )

    if "generation_completed_at" not in columns:
        op.add_column(
            "tasks",
            sa.Column(
                "generation_completed_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )

    if "generation_error" not in columns:
        op.add_column(
            "tasks",
            sa.Column(
                "generation_error",
                sa.Text(),
                nullable=True,
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [column["name"] for column in inspector.get_columns("tasks")]

    with op.batch_alter_table("tasks", schema=None) as batch_op:
        if "generation_error" in columns:
            batch_op.drop_column("generation_error")
        if "generation_completed_at" in columns:
            batch_op.drop_column("generation_completed_at")
        if "generation_started_at" in columns:
            batch_op.drop_column("generation_started_at")
        if "assignment_generation_status" in columns:
            batch_op.drop_column("assignment_generation_status")
