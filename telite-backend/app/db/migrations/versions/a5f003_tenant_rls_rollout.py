"""tenant_rls_rollout

Revision ID: a5f003
Revises: a5f002
Create Date: 2026-06-12 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "a5f003"
down_revision: Union[str, None] = "a5f002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TENANT_TABLES = (
    "activity_log",
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
    _add_derivable_org_columns()
    _normalize_audit_log_org_id()
    _normalize_password_reset_timestamps()

    for table_name in TENANT_TABLES:
        _require_org_id(table_name)
        _add_org_fk(table_name)
        _enable_rls(table_name)


def downgrade() -> None:
    pass


def _add_derivable_org_columns() -> None:
    _add_org_id_from_join(
        table_name="learning_path_courses",
        source_table="learning_paths",
        join_condition="source.id = target.path_id",
        source_org_column="source.org_id",
    )
    _add_org_id_from_column(
        table_name="pending_verifications",
        source_column="organization_id",
    )
    _add_org_id_from_join(
        table_name="question_versions",
        source_table="questions",
        join_condition="source.id = target.question_id",
        source_org_column="source.org_id",
    )
    _add_org_id_from_join(
        table_name="quiz_answers",
        source_table="quiz_attempts",
        join_condition="source.id = target.attempt_id",
        source_org_column="source.org_id",
    )
    _add_org_id_from_join(
        table_name="quiz_settings",
        source_table="quiz_definitions",
        join_condition="source.id = target.quiz_id",
        source_org_column="source.org_id",
    )
    _add_org_id_from_join(
        table_name="rubric_criteria",
        source_table="grading_rubrics",
        join_condition="source.id = target.rubric_id",
        source_org_column="source.org_id",
    )


def _add_org_id_from_column(table_name: str, source_column: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF to_regclass('public.{table_name}') IS NOT NULL
            AND NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = '{table_name}'
                  AND column_name = 'org_id'
            ) THEN
                ALTER TABLE {table_name}
                    ADD COLUMN org_id INTEGER;

                UPDATE {table_name}
                SET org_id = {source_column}
                WHERE org_id IS NULL;

                CREATE INDEX IF NOT EXISTS ix_{table_name}_org_id
                    ON {table_name} (org_id);
            END IF;
        END $$;
        """
    )


def _add_org_id_from_join(
    *,
    table_name: str,
    source_table: str,
    join_condition: str,
    source_org_column: str,
) -> None:
    op.execute(
        f"""
        DO $$
        DECLARE
            default_org_id INTEGER;
        BEGIN
            SELECT id INTO default_org_id
            FROM organizations
            ORDER BY id
            LIMIT 1;

            IF to_regclass('public.{table_name}') IS NOT NULL
            AND NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = '{table_name}'
                  AND column_name = 'org_id'
            ) THEN
                ALTER TABLE {table_name}
                    ADD COLUMN org_id INTEGER;

                UPDATE {table_name} target
                SET org_id = {source_org_column}
                FROM {source_table} source
                WHERE {join_condition};

                UPDATE {table_name}
                SET org_id = default_org_id
                WHERE org_id IS NULL;

                CREATE INDEX IF NOT EXISTS ix_{table_name}_org_id
                    ON {table_name} (org_id);
            END IF;
        END $$;
        """
    )


def _normalize_audit_log_org_id() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            default_org_id INTEGER;
        BEGIN
            SELECT id INTO default_org_id
            FROM organizations
            ORDER BY id
            LIMIT 1;

            IF to_regclass('public.audit_log') IS NOT NULL THEN
                UPDATE audit_log
                SET org_id = default_org_id
                WHERE org_id IS NULL;
            END IF;
        END $$;
        """
    )


def _normalize_password_reset_timestamps() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.password_reset_tokens') IS NOT NULL THEN
                ALTER TABLE password_reset_tokens
                    ALTER COLUMN created_at DROP DEFAULT;

                ALTER TABLE password_reset_tokens
                    ALTER COLUMN created_at
                    TYPE TIMESTAMPTZ
                    USING CASE
                        WHEN created_at IS NULL THEN now()
                        ELSE created_at::timestamptz
                    END;

                ALTER TABLE password_reset_tokens
                    ALTER COLUMN created_at SET DEFAULT now();

                ALTER TABLE password_reset_tokens
                    ALTER COLUMN created_at SET NOT NULL;
            END IF;
        END $$;
        """
    )


def _require_org_id(table_name: str) -> None:
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
                ALTER TABLE {table_name}
                    ALTER COLUMN org_id SET NOT NULL;
            END IF;
        END $$;
        """
    )


def _add_org_fk(table_name: str) -> None:
    constraint_name = f"fk_{table_name}_org_id_organizations"
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
            )
            AND NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conrelid = 'public.{table_name}'::regclass
                  AND contype = 'f'
                  AND conkey = ARRAY[
                    (
                        SELECT attnum
                        FROM pg_attribute
                        WHERE attrelid = 'public.{table_name}'::regclass
                          AND attname = 'org_id'
                    )
                  ]::smallint[]
            ) THEN
                ALTER TABLE {table_name}
                    ADD CONSTRAINT {constraint_name}
                    FOREIGN KEY (org_id)
                    REFERENCES organizations(id)
                    ON DELETE CASCADE;
            END IF;
        END $$;
        """
    )


def _enable_rls(table_name: str) -> None:
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
                DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name};

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
