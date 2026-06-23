"""gradebook g0.2 grade results

Revision ID: e5a7b2c9d014
Revises: d4f6a1b2c3e7
Create Date: 2026-06-23
"""

from alembic import op
import sqlalchemy as sa


revision = "e5a7b2c9d014"
down_revision = "d4f6a1b2c3e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grade_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("course_id", sa.String(length=50), nullable=False),
        sa.Column("course_version_id", sa.String(length=50), nullable=False, server_default="current"),
        sa.Column("grade_item_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=50), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.String(length=80), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=True),
        sa.Column("points_awarded", sa.Float(), nullable=True),
        sa.Column("points_possible", sa.Float(), nullable=False, server_default="100"),
        sa.Column("percentage", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="graded"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("graded_by", sa.String(length=50), nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["grade_item_id"], ["grade_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["graded_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id",
            "course_version_id",
            "grade_item_id",
            "user_id",
            name="uq_grade_results_org_version_item_user",
        ),
    )
    op.create_index("ix_grade_results_course_id", "grade_results", ["course_id"])
    op.create_index("ix_grade_results_course_version_id", "grade_results", ["course_version_id"])
    op.create_index("ix_grade_results_grade_item_id", "grade_results", ["grade_item_id"])
    op.create_index("ix_grade_results_is_current", "grade_results", ["is_current"])
    op.create_index("ix_grade_results_org_id", "grade_results", ["org_id"])
    op.create_index("ix_grade_results_source_id", "grade_results", ["source_id"])
    op.create_index("ix_grade_results_source_type", "grade_results", ["source_type"])
    op.create_index("ix_grade_results_status", "grade_results", ["status"])
    op.create_index("ix_grade_results_user_id", "grade_results", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_grade_results_user_id", table_name="grade_results")
    op.drop_index("ix_grade_results_status", table_name="grade_results")
    op.drop_index("ix_grade_results_source_type", table_name="grade_results")
    op.drop_index("ix_grade_results_source_id", table_name="grade_results")
    op.drop_index("ix_grade_results_org_id", table_name="grade_results")
    op.drop_index("ix_grade_results_is_current", table_name="grade_results")
    op.drop_index("ix_grade_results_grade_item_id", table_name="grade_results")
    op.drop_index("ix_grade_results_course_version_id", table_name="grade_results")
    op.drop_index("ix_grade_results_course_id", table_name="grade_results")
    op.drop_table("grade_results")
