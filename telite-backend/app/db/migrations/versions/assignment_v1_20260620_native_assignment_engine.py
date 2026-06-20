"""native_assignment_engine_v1

Revision ID: assignment_v1_20260620
Revises: theme_pref_20260619
Create Date: 2026-06-20 00:20:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "assignment_v1_20260620"
down_revision: Union[str, None] = "theme_pref_20260619"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


STATUSES = "'draft', 'submitted', 'graded', 'returned', 'resubmitted'"


def _table_names(conn) -> set[str]:
    return set(sa.inspect(conn).get_table_names())


def _column_names(conn, table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(conn).get_columns(table)}


def _constraint_names(conn, table: str) -> set[str]:
    inspector = sa.inspect(conn)
    names = {constraint["name"] for constraint in inspector.get_unique_constraints(table)}
    names.update(constraint["name"] for constraint in inspector.get_check_constraints(table))
    names.update(constraint["name"] for constraint in inspector.get_foreign_keys(table))
    return names


def _index_names(conn, table: str) -> set[str]:
    return {index["name"] for index in sa.inspect(conn).get_indexes(table)}


def _create_table() -> None:
    op.create_table(
        "assignment_submissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("block_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=50), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("submission_text", sa.Text(), nullable=True),
        sa.Column("submission_files_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("grade", sa.Float(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("graded_by", sa.String(length=50), nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["block_id"], ["lesson_blocks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["graded_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("block_id", "user_id", name="uq_assignment_submission_block_user"),
        sa.CheckConstraint(f"status IN ({STATUSES})", name="chk_assignment_submissions_status"),
    )


def _ensure_indexes(conn) -> None:
    indexes = _index_names(conn, "assignment_submissions")
    for name, columns in {
        "ix_assignment_submissions_block_id": ["block_id"],
        "ix_assignment_submissions_user_id": ["user_id"],
        "ix_assignment_submissions_org_id": ["org_id"],
        "ix_assignment_submissions_status": ["status"],
        "ix_assignment_submissions_block_status": ["block_id", "status"],
        "ix_assignment_submissions_org_block": ["org_id", "block_id"],
    }.items():
        if name not in indexes:
            op.create_index(name, "assignment_submissions", columns, unique=False)


def _ensure_rls() -> None:
    op.execute("ALTER TABLE assignment_submissions ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS assignment_submissions_native_isolation ON assignment_submissions")
    op.execute(
        """
        CREATE POLICY assignment_submissions_native_isolation
        ON assignment_submissions
        USING (
            current_setting('app.bypass_rls', true) = 'on'
            OR (
                org_id = NULLIF(current_setting('app.current_org_id', true), '')::integer
                AND (
                    user_id = NULLIF(current_setting('app.current_user_id', true), '')
                    OR NULLIF(current_setting('app.current_user_role', true), '') IN (
                        'platform_admin', 'super_admin', 'category_admin', 'instructor', 'author', 'reviewer'
                    )
                )
            )
        )
        WITH CHECK (
            current_setting('app.bypass_rls', true) = 'on'
            OR (
                org_id = NULLIF(current_setting('app.current_org_id', true), '')::integer
                AND (
                    user_id = NULLIF(current_setting('app.current_user_id', true), '')
                    OR NULLIF(current_setting('app.current_user_role', true), '') IN (
                        'platform_admin', 'super_admin', 'category_admin', 'instructor', 'author', 'reviewer'
                    )
                )
            )
        )
        """
    )


def upgrade() -> None:
    conn = op.get_bind()
    if "assignment_submissions" not in _table_names(conn):
        _create_table()
    else:
        columns = _column_names(conn, "assignment_submissions")
        with op.batch_alter_table("assignment_submissions") as batch_op:
            if "file_path" not in columns:
                batch_op.add_column(sa.Column("file_path", sa.String(length=500), nullable=True))
            if "original_filename" not in columns:
                batch_op.add_column(sa.Column("original_filename", sa.String(length=255), nullable=True))
            if "mime_type" not in columns:
                batch_op.add_column(sa.Column("mime_type", sa.String(length=120), nullable=True))
            if "file_size" not in columns:
                batch_op.add_column(sa.Column("file_size", sa.Integer(), nullable=True))
            if "attempt_number" not in columns:
                batch_op.add_column(sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"))

        constraints = _constraint_names(conn, "assignment_submissions")
        if "chk_assignment_submissions_status" not in constraints:
            with op.batch_alter_table("assignment_submissions") as batch_op:
                batch_op.create_check_constraint(
                    "chk_assignment_submissions_status",
                    f"status IN ({STATUSES})",
                )
    _ensure_indexes(conn)
    _ensure_rls()


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS assignment_submissions_native_isolation ON assignment_submissions")
    conn = op.get_bind()
    if "assignment_submissions" not in _table_names(conn):
        return
    columns = _column_names(conn, "assignment_submissions")
    constraints = _constraint_names(conn, "assignment_submissions")
    for name in (
        "ix_assignment_submissions_org_block",
        "ix_assignment_submissions_block_status",
    ):
        if name in _index_names(conn, "assignment_submissions"):
            op.drop_index(name, table_name="assignment_submissions")
    with op.batch_alter_table("assignment_submissions") as batch_op:
        if "chk_assignment_submissions_status" in constraints:
            batch_op.drop_constraint("chk_assignment_submissions_status", type_="check")
        for column in ("attempt_number", "file_size", "mime_type", "original_filename", "file_path"):
            if column in columns:
                batch_op.drop_column(column)
