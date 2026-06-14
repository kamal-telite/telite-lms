"""rewrite_rls_policies_safe_context

Revision ID: a5f007
Revises: a5f006
Create Date: 2026-06-12 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "a5f007"
down_revision: Union[str, None] = "a5f006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TENANT_TABLES = (
    "activity_log",
    "alert_rules",
    "audit_log",
    "auth_sessions",
    "branding_assets",
    "branding_audit_logs",
    "branding_versions",
    "builder_activity_log",
    "categories",
    "course_edit_locks",
    "course_modules",
    "course_progress",
    "course_reviews",
    "course_sections",
    "course_versions",
    "courses",
    "enrollment_requests",
    "grading_events",
    "grading_rubrics",
    "interactive_tracking",
    "learner_activity_log",
    "learner_events",
    "learning_path_courses",
    "learning_path_progress",
    "learning_paths",
    "lesson_block_progress",
    "lesson_blocks",
    "media_assets",
    "memberships",
    "module_progress",
    "moodle_sync_logs",
    "moodle_tenants",
    "notifications",
    "org_invitations",
    "organization_branding",
    "pal_quiz_scores",
    "pal_recommendations",
    "pal_topic_performance",
    "password_reset_tokens",
    "pending_verifications",
    "question_banks",
    "question_versions",
    "questions",
    "quiz_answers",
    "quiz_attempt_events",
    "quiz_attempt_questions",
    "quiz_attempts",
    "quiz_definitions",
    "quiz_settings",
    "role_permissions",
    "rubric_criteria",
    "tasks",
    "users",
)


def upgrade() -> None:
    for table_name in TENANT_TABLES:
        _rewrite_policy(table_name)


def downgrade() -> None:
    pass


def _rewrite_policy(table_name: str) -> None:
    policy_name = f"telite_tenant_isolation_{table_name}"
    op.execute(
        f"""
        DO $$
        BEGIN
            IF to_regclass('public.{table_name}') IS NOT NULL
            AND EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = '{table_name}'
                  AND column_name = 'org_id'
            ) THEN
                ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

                DROP POLICY IF EXISTS {policy_name} ON {table_name};

                CREATE POLICY {policy_name}
                ON {table_name}
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
