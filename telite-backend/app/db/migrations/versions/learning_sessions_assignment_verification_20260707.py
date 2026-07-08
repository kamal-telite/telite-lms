"""assignment verification and learning sessions

Revision ID: learning_sessions_20260707
Revises: add_section_progress
Create Date: 2026-07-07 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "learning_sessions_20260707"
down_revision: Union[str, None] = "add_section_progress"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


STATUSES = "'draft', 'submitted', 'graded', 'returned', 'resubmitted', 'pending_verification', 'approved', 'rejected'"


def _tables(conn) -> set[str]:
    return set(sa.inspect(conn).get_table_names())


def _columns(conn, table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(conn).get_columns(table)}


def upgrade() -> None:
    conn = op.get_bind()
    if "assignment_submissions" in _tables(conn):
        columns = _columns(conn, "assignment_submissions")
        with op.batch_alter_table("assignment_submissions") as batch:
            try:
                batch.drop_constraint("chk_assignment_submissions_status", type_="check")
            except Exception:
                pass
            if "course_time_seconds_at_submission" not in columns:
                batch.add_column(sa.Column("course_time_seconds_at_submission", sa.Integer(), nullable=False, server_default="0"))
            if "course_progress_pct_at_submission" not in columns:
                batch.add_column(sa.Column("course_progress_pct_at_submission", sa.Float(), nullable=False, server_default="0"))
            if "reviewed_by" not in columns:
                batch.add_column(sa.Column("reviewed_by", sa.String(length=50), nullable=True))
            if "reviewed_at" not in columns:
                batch.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
            batch.create_check_constraint("chk_assignment_submissions_status", f"status IN ({STATUSES})")
        try:
            op.create_foreign_key("fk_assignment_submissions_reviewed_by_users", "assignment_submissions", "users", ["reviewed_by"], ["id"], ondelete="SET NULL")
        except Exception:
            pass

    if "learning_sessions" not in _tables(conn):
        op.create_table(
            "learning_sessions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.String(length=50), nullable=False),
            sa.Column("course_id", sa.String(length=50), nullable=False),
            sa.Column("module_id", sa.Integer(), nullable=True),
            sa.Column("section_id", sa.Integer(), nullable=True),
            sa.Column("block_id", sa.Integer(), nullable=True),
            sa.Column("org_id", sa.Integer(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("active_seconds", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("end_reason", sa.String(length=50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["module_id"], ["course_modules.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["section_id"], ["course_sections.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["block_id"], ["lesson_blocks.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        )
        for name, columns in {
            "ix_learning_sessions_user_id": ["user_id"],
            "ix_learning_sessions_course_id": ["course_id"],
            "ix_learning_sessions_module_id": ["module_id"],
            "ix_learning_sessions_section_id": ["section_id"],
            "ix_learning_sessions_block_id": ["block_id"],
            "ix_learning_sessions_org_id": ["org_id"],
            "ix_learning_sessions_status": ["status"],
            "ix_learning_sessions_org_course_user": ["org_id", "course_id", "user_id"],
        }.items():
            op.create_index(name, "learning_sessions", columns)
        op.execute("ALTER TABLE learning_sessions ENABLE ROW LEVEL SECURITY")
        op.execute(
            """
            CREATE POLICY learning_sessions_tenant_isolation
            ON learning_sessions
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::integer
            )
            WITH CHECK (
                current_setting('app.bypass_rls', true) = 'on'
                OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::integer
            )
            """
        )


def downgrade() -> None:
    conn = op.get_bind()
    if "learning_sessions" in _tables(conn):
        op.execute("DROP POLICY IF EXISTS learning_sessions_tenant_isolation ON learning_sessions")
        op.drop_table("learning_sessions")
    if "assignment_submissions" in _tables(conn):
        with op.batch_alter_table("assignment_submissions") as batch:
            try:
                batch.drop_constraint("chk_assignment_submissions_status", type_="check")
            except Exception:
                pass
            for column in ("reviewed_at", "reviewed_by", "course_progress_pct_at_submission", "course_time_seconds_at_submission"):
                if column in _columns(conn, "assignment_submissions"):
                    batch.drop_column(column)
            batch.create_check_constraint("chk_assignment_submissions_status", "status IN ('draft', 'submitted', 'graded', 'returned', 'resubmitted')")
