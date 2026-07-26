"""restore section progress runtime table

Revision ID: b91f4e7a2c10
Revises: a787d161ccc5
Create Date: 2026-07-27 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b91f4e7a2c10"
down_revision: Union[str, None] = "a787d161ccc5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "course_sections" in inspector.get_table_names():
        section_columns = {column["name"] for column in inspector.get_columns("course_sections")}
        if "minimum_time_seconds" not in section_columns:
            with op.batch_alter_table("course_sections", schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "minimum_time_seconds",
                        sa.Integer(),
                        nullable=False,
                        server_default="0",
                        comment="Minimum required learning time in seconds",
                    )
                )

    if "section_progress" not in inspector.get_table_names():
        op.create_table(
            "section_progress",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.String(length=50), nullable=False),
            sa.Column("section_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="not_started"),
            sa.Column("completion_percentage", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("time_spent_seconds", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_entered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_left_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("org_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["section_id"], ["course_sections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_section_progress_org_id"), "section_progress", ["org_id"], unique=False)
        op.create_index(op.f("ix_section_progress_section_id"), "section_progress", ["section_id"], unique=False)
        op.create_index(op.f("ix_section_progress_user_id"), "section_progress", ["user_id"], unique=False)
        return

    progress_columns = {column["name"] for column in inspector.get_columns("section_progress")}
    with op.batch_alter_table("section_progress", schema=None) as batch_op:
        if "time_spent_seconds" not in progress_columns:
            batch_op.add_column(sa.Column("time_spent_seconds", sa.Integer(), nullable=False, server_default="0"))
        if "last_entered_at" not in progress_columns:
            batch_op.add_column(sa.Column("last_entered_at", sa.DateTime(timezone=True), nullable=True))
        if "last_left_at" not in progress_columns:
            batch_op.add_column(sa.Column("last_left_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if inspector.has_table("section_progress"):
        op.drop_index(op.f("ix_section_progress_user_id"), table_name="section_progress")
        op.drop_index(op.f("ix_section_progress_section_id"), table_name="section_progress")
        op.drop_index(op.f("ix_section_progress_org_id"), table_name="section_progress")
        op.drop_table("section_progress")
