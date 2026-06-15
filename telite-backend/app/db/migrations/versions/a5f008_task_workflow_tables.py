"""task_workflow_tables

Revision ID: a5f008
Revises: a5f007
Create Date: 2026-06-15 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a5f008"
down_revision: Union[str, None] = "a5f007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tenant_policy(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = '{table}'
                  AND policyname = '{table}_tenant_isolation'
            ) THEN
                CREATE POLICY {table}_tenant_isolation
                ON {table}
                USING (
                    current_setting('app.bypass_rls', true) = 'on'
                    OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::integer
                )
                WITH CHECK (
                    current_setting('app.bypass_rls', true) = 'on'
                    OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::integer
                );
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    op.create_table(
        "task_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=50), nullable=False),
        sa.Column("learner_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="assigned"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=False, comment="Tenant organisation ID - used by RLS policies"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["learner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "learner_id", name="uq_task_assignments_task_learner"),
    )
    with op.batch_alter_table("task_assignments") as batch_op:
        batch_op.create_index(batch_op.f("ix_task_assignments_learner_id"), ["learner_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_task_assignments_org_id"), ["org_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_task_assignments_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_task_assignments_task_id"), ["task_id"], unique=False)

    op.create_table(
        "task_submissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("submission_notes", sa.Text(), nullable=True),
        sa.Column("attachment_url", sa.Text(), nullable=True),
        sa.Column("github_url", sa.Text(), nullable=True),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=False, comment="Tenant organisation ID - used by RLS policies"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assignment_id"], ["task_assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("task_submissions") as batch_op:
        batch_op.create_index(batch_op.f("ix_task_submissions_assignment_id"), ["assignment_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_task_submissions_org_id"), ["org_id"], unique=False)

    op.create_table(
        "task_reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("review_status", sa.String(length=30), nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=50), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=False, comment="Tenant organisation ID - used by RLS policies"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submission_id"], ["task_submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("task_reviews") as batch_op:
        batch_op.create_index(batch_op.f("ix_task_reviews_org_id"), ["org_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_task_reviews_review_status"), ["review_status"], unique=False)
        batch_op.create_index(batch_op.f("ix_task_reviews_reviewed_by"), ["reviewed_by"], unique=False)
        batch_op.create_index(batch_op.f("ix_task_reviews_submission_id"), ["submission_id"], unique=False)

    for table in ("task_assignments", "task_submissions", "task_reviews"):
        _tenant_policy(table)

    op.execute(
        """
        INSERT INTO task_assignments (
            task_id, learner_id, status, assigned_at, started_at, submitted_at, completed_at,
            org_id, created_at, updated_at
        )
        SELECT
            t.id,
            t.assigned_to_user_id,
            CASE
                WHEN t.status IN ('pending', 'overdue') THEN 'assigned'
                WHEN t.status = 'completed' THEN 'approved'
                ELSE t.status
            END,
            COALESCE(t.created_at, CURRENT_TIMESTAMP),
            CASE WHEN t.status IN ('in_progress', 'submitted', 'completed') THEN t.updated_at END,
            CASE WHEN t.status IN ('submitted', 'completed') THEN t.updated_at END,
            CASE WHEN t.status = 'completed' THEN t.updated_at END,
            t.org_id,
            COALESCE(t.created_at, CURRENT_TIMESTAMP),
            t.updated_at
        FROM tasks t
        WHERE t.assigned_to_user_id IS NOT NULL
        ON CONFLICT ON CONSTRAINT uq_task_assignments_task_learner DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("task_reviews")
    op.drop_table("task_submissions")
    op.drop_table("task_assignments")
