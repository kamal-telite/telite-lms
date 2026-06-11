"""add_course_reviews

Revision ID: f0d1c2b3a4e5
Revises: b2d976c3de97
Create Date: 2026-06-10 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f0d1c2b3a4e5"
down_revision: Union[str, None] = "b2d976c3de97"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("course_id", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=50), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False, comment="Tenant organisation ID - used by RLS policies"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("course_reviews", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_course_reviews_action"), ["action"], unique=False)
        batch_op.create_index(batch_op.f("ix_course_reviews_course_id"), ["course_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_course_reviews_org_id"), ["org_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_course_reviews_reviewed_by"), ["reviewed_by"], unique=False)
        batch_op.create_index(batch_op.f("ix_course_reviews_to_status"), ["to_status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("course_reviews", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_course_reviews_to_status"))
        batch_op.drop_index(batch_op.f("ix_course_reviews_reviewed_by"))
        batch_op.drop_index(batch_op.f("ix_course_reviews_org_id"))
        batch_op.drop_index(batch_op.f("ix_course_reviews_course_id"))
        batch_op.drop_index(batch_op.f("ix_course_reviews_action"))
    op.drop_table("course_reviews")
