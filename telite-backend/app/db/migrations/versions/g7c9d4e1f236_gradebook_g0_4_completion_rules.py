"""gradebook g0.4 completion rules

Revision ID: g7c9d4e1f236
Revises: f6b8c3d0e125
Create Date: 2026-06-23
"""

from alembic import op
import sqlalchemy as sa


revision = "g7c9d4e1f236"
down_revision = "f6b8c3d0e125"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "completion_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("course_id", sa.String(length=50), nullable=True),
        sa.Column("course_version_id", sa.String(length=50), nullable=True),
        sa.Column("grading_scheme_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("requires_content_completion", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("minimum_content_percentage", sa.Float(), nullable=False, server_default="100"),
        sa.Column("requires_grade_pass", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("minimum_final_percentage", sa.Float(), nullable=True),
        sa.Column("requires_instructor_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("certificate_eligible_on_completion", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("rule_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_by", sa.String(length=50), nullable=True),
        sa.Column("updated_by", sa.String(length=50), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["grading_scheme_id"], ["grading_schemes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id",
            "course_id",
            "course_version_id",
            name="uq_completion_rules_org_course_version",
        ),
    )
    op.create_index("ix_completion_rules_course_id", "completion_rules", ["course_id"])
    op.create_index("ix_completion_rules_course_version_id", "completion_rules", ["course_version_id"])
    op.create_index("ix_completion_rules_created_by", "completion_rules", ["created_by"])
    op.create_index("ix_completion_rules_grading_scheme_id", "completion_rules", ["grading_scheme_id"])
    op.create_index("ix_completion_rules_org_id", "completion_rules", ["org_id"])
    op.create_index("ix_completion_rules_status", "completion_rules", ["status"])
    op.create_index(
        "uq_completion_rules_active_org_default",
        "completion_rules",
        ["org_id"],
        unique=True,
        postgresql_where=sa.text("course_id IS NULL AND deleted_at IS NULL AND status = 'active'"),
    )
    op.create_index(
        "uq_completion_rules_active_course_default",
        "completion_rules",
        ["org_id", "course_id"],
        unique=True,
        postgresql_where=sa.text("course_id IS NOT NULL AND course_version_id IS NULL AND deleted_at IS NULL AND status = 'active'"),
    )
    op.create_index(
        "uq_completion_rules_active_course_version",
        "completion_rules",
        ["org_id", "course_id", "course_version_id"],
        unique=True,
        postgresql_where=sa.text("course_id IS NOT NULL AND course_version_id IS NOT NULL AND deleted_at IS NULL AND status = 'active'"),
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_completion_rules_active_course_version")
    op.execute("DROP INDEX IF EXISTS uq_completion_rules_active_course_default")
    op.execute("DROP INDEX IF EXISTS uq_completion_rules_active_org_default")
    op.drop_index("ix_completion_rules_status", table_name="completion_rules")
    op.drop_index("ix_completion_rules_org_id", table_name="completion_rules")
    op.drop_index("ix_completion_rules_grading_scheme_id", table_name="completion_rules")
    op.drop_index("ix_completion_rules_created_by", table_name="completion_rules")
    op.drop_index("ix_completion_rules_course_version_id", table_name="completion_rules")
    op.drop_index("ix_completion_rules_course_id", table_name="completion_rules")
    op.drop_table("completion_rules")
