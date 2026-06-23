"""gradebook g0.6 grade change audit

Revision ID: h8d2e5f9a641
Revises: c99c89b4b321
Create Date: 2026-06-23
"""

from alembic import op
import sqlalchemy as sa


revision = "h8d2e5f9a641"
down_revision = "c99c89b4b321"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grade_change_audit",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("course_id", sa.String(length=50), nullable=False),
        sa.Column("course_version_id", sa.String(length=50), nullable=False, server_default="current"),
        sa.Column("user_id", sa.String(length=50), nullable=False),
        sa.Column("course_grade_id", sa.Integer(), nullable=True),
        sa.Column("grade_item_id", sa.Integer(), nullable=True),
        sa.Column("grade_result_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.String(length=50), nullable=True),
        sa.Column("actor_role", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("old_value_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("new_value_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["course_grade_id"], ["course_grades.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["grade_item_id"], ["grade_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["grade_result_id"], ["grade_results.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grade_change_audit_action", "grade_change_audit", ["action"])
    op.create_index("ix_grade_change_audit_actor_user_id", "grade_change_audit", ["actor_user_id"])
    op.create_index("ix_grade_change_audit_course_grade_id", "grade_change_audit", ["course_grade_id"])
    op.create_index("ix_grade_change_audit_course_id", "grade_change_audit", ["course_id"])
    op.create_index("ix_grade_change_audit_course_version_id", "grade_change_audit", ["course_version_id"])
    op.create_index("ix_grade_change_audit_grade_item_id", "grade_change_audit", ["grade_item_id"])
    op.create_index("ix_grade_change_audit_grade_result_id", "grade_change_audit", ["grade_result_id"])
    op.create_index("ix_grade_change_audit_org_id", "grade_change_audit", ["org_id"])
    op.create_index("ix_grade_change_audit_user_id", "grade_change_audit", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_grade_change_audit_user_id", table_name="grade_change_audit")
    op.drop_index("ix_grade_change_audit_org_id", table_name="grade_change_audit")
    op.drop_index("ix_grade_change_audit_grade_result_id", table_name="grade_change_audit")
    op.drop_index("ix_grade_change_audit_grade_item_id", table_name="grade_change_audit")
    op.drop_index("ix_grade_change_audit_course_version_id", table_name="grade_change_audit")
    op.drop_index("ix_grade_change_audit_course_id", table_name="grade_change_audit")
    op.drop_index("ix_grade_change_audit_course_grade_id", table_name="grade_change_audit")
    op.drop_index("ix_grade_change_audit_actor_user_id", table_name="grade_change_audit")
    op.drop_index("ix_grade_change_audit_action", table_name="grade_change_audit")
    op.drop_table("grade_change_audit")
