"""gradebook g0.3 course grades

Revision ID: f6b8c3d0e125
Revises: e5a7b2c9d014
Create Date: 2026-06-23
"""

from alembic import op
import sqlalchemy as sa


revision = "f6b8c3d0e125"
down_revision = "e5a7b2c9d014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "course_grades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("course_id", sa.String(length=50), nullable=False),
        sa.Column("course_version_id", sa.String(length=50), nullable=False, server_default="current"),
        sa.Column("user_id", sa.String(length=50), nullable=False),
        sa.Column("grading_scheme_id", sa.Integer(), nullable=True),
        sa.Column("points_awarded", sa.Float(), nullable=True),
        sa.Column("points_possible", sa.Float(), nullable=True),
        sa.Column("percentage", sa.Float(), nullable=True),
        sa.Column("display_grade", sa.String(length=50), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("override_by", sa.String(length=50), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["grading_scheme_id"], ["grading_schemes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["override_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id",
            "course_id",
            "user_id",
            "course_version_id",
            name="uq_course_grades_org_course_user_version",
        ),
    )
    op.create_index("ix_course_grades_course_id", "course_grades", ["course_id"])
    op.create_index("ix_course_grades_course_version_id", "course_grades", ["course_version_id"])
    op.create_index("ix_course_grades_grading_scheme_id", "course_grades", ["grading_scheme_id"])
    op.create_index("ix_course_grades_org_id", "course_grades", ["org_id"])
    op.create_index("ix_course_grades_passed", "course_grades", ["passed"])
    op.create_index("ix_course_grades_status", "course_grades", ["status"])
    op.create_index("ix_course_grades_user_id", "course_grades", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_course_grades_user_id", table_name="course_grades")
    op.drop_index("ix_course_grades_status", table_name="course_grades")
    op.drop_index("ix_course_grades_passed", table_name="course_grades")
    op.drop_index("ix_course_grades_org_id", table_name="course_grades")
    op.drop_index("ix_course_grades_grading_scheme_id", table_name="course_grades")
    op.drop_index("ix_course_grades_course_version_id", table_name="course_grades")
    op.drop_index("ix_course_grades_course_id", table_name="course_grades")
    op.drop_table("course_grades")
