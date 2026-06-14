"""schema_type_alignment

Revision ID: a5f004
Revises: a5f003
Create Date: 2026-06-12 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "a5f004"
down_revision: Union[str, None] = "a5f003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TIMESTAMPTZ_COLUMNS = (
    ("activity_log", "created_at", False),
    ("activity_log", "updated_at", True),
    ("allowed_domains", "created_at", False),
    ("allowed_domains", "updated_at", True),
    ("audit_log", "created_at", False),
    ("audit_log", "updated_at", True),
    ("auth_sessions", "created_at", False),
    ("auth_sessions", "updated_at", True),
    ("builder_activity_log", "created_at", False),
    ("builder_activity_log", "updated_at", True),
    ("categories", "created_at", False),
    ("categories", "updated_at", True),
    ("course_edit_locks", "expires_at", False),
    ("course_edit_locks", "locked_at", False),
    ("course_modules", "created_at", False),
    ("course_modules", "deleted_at", True),
    ("course_modules", "updated_at", True),
    ("course_progress", "completed_at", True),
    ("course_progress", "created_at", False),
    ("course_progress", "last_viewed_at", True),
    ("course_progress", "started_at", True),
    ("course_progress", "updated_at", True),
    ("course_reviews", "reviewed_at", False),
    ("course_sections", "deleted_at", True),
    ("course_versions", "created_at", True),
    ("course_versions", "published_at", True),
    ("courses", "created_at", False),
    ("courses", "updated_at", True),
    ("enrollment_requests", "created_at", False),
    ("enrollment_requests", "updated_at", True),
    ("grading_events", "timestamp", True),
    ("learner_activity_log", "created_at", False),
    ("learner_events", "created_at", False),
    ("learning_path_progress", "completed_at", True),
    ("learning_path_progress", "created_at", False),
    ("learning_path_progress", "started_at", True),
    ("learning_path_progress", "updated_at", True),
    ("learning_paths", "created_at", True),
    ("learning_paths", "deleted_at", True),
    ("lesson_block_progress", "completed_at", True),
    ("lesson_block_progress", "created_at", False),
    ("lesson_block_progress", "last_viewed_at", True),
    ("lesson_block_progress", "updated_at", True),
    ("lesson_blocks", "deleted_at", True),
    ("media_assets", "created_at", True),
    ("media_assets", "deleted_at", True),
    ("memberships", "created_at", False),
    ("memberships", "updated_at", True),
    ("module_progress", "completed_at", True),
    ("module_progress", "created_at", False),
    ("module_progress", "last_viewed_at", True),
    ("module_progress", "started_at", True),
    ("module_progress", "updated_at", True),
    ("notifications", "created_at", False),
    ("notifications", "updated_at", True),
    ("org_invitations", "created_at", False),
    ("org_invitations", "updated_at", True),
    ("organization_branding", "created_at", False),
    ("organization_branding", "updated_at", True),
    ("organizations", "created_at", False),
    ("organizations", "updated_at", True),
    ("pal_quiz_scores", "created_at", False),
    ("pal_quiz_scores", "updated_at", True),
    ("pal_recommendations", "created_at", False),
    ("pal_recommendations", "updated_at", True),
    ("pal_topic_performance", "created_at", False),
    ("pal_topic_performance", "updated_at", True),
    ("password_reset_tokens", "created_at", False),
    ("password_reset_tokens", "updated_at", True),
    ("pending_verifications", "created_at", False),
    ("pending_verifications", "updated_at", True),
    ("quiz_attempt_events", "event_timestamp", False),
    ("quiz_attempts", "started_at", True),
    ("quiz_attempts", "submitted_at", True),
    ("quiz_definitions", "created_at", True),
    ("quiz_definitions", "deleted_at", True),
    ("role_permissions", "created_at", False),
    ("role_permissions", "updated_at", True),
    ("tasks", "created_at", False),
    ("tasks", "updated_at", True),
    ("users", "created_at", False),
    ("users", "updated_at", True),
)


def upgrade() -> None:
    for table_name, column_name, nullable in TIMESTAMPTZ_COLUMNS:
        _normalize_timestamptz(table_name, column_name, nullable)

    _normalize_boolean("enrollment_requests", "domain_verified", default="false", nullable=False)
    _normalize_boolean("notifications", "is_read", default="false", nullable=False)
    _normalize_string("users", "invited_via", length=50, nullable=True)


def downgrade() -> None:
    pass


def _normalize_timestamptz(table_name: str, column_name: str, nullable: bool) -> None:
    null_clause = "DROP NOT NULL" if nullable else "SET NOT NULL"
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
                  AND column_name = '{column_name}'
            ) THEN
                ALTER TABLE {table_name}
                    ALTER COLUMN {column_name} DROP DEFAULT;

                ALTER TABLE {table_name}
                    ALTER COLUMN {column_name}
                    TYPE TIMESTAMPTZ
                    USING CASE
                        WHEN {column_name} IS NULL THEN NULL
                        WHEN btrim({column_name}::text) = '' THEN NULL
                        ELSE {column_name}::timestamptz
                    END;

                {"UPDATE " + table_name + " SET " + column_name + " = now() WHERE " + column_name + " IS NULL;" if not nullable else ""}

                ALTER TABLE {table_name}
                    ALTER COLUMN {column_name} {null_clause};
            END IF;
        END $$;
        """
    )


def _normalize_boolean(
    table_name: str,
    column_name: str,
    *,
    default: str,
    nullable: bool,
) -> None:
    null_clause = "DROP NOT NULL" if nullable else "SET NOT NULL"
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
                  AND column_name = '{column_name}'
            ) THEN
                ALTER TABLE {table_name}
                    ALTER COLUMN {column_name} DROP DEFAULT;

                ALTER TABLE {table_name}
                    ALTER COLUMN {column_name}
                    TYPE BOOLEAN
                    USING CASE
                        WHEN {column_name} IS NULL THEN {default}
                        WHEN {column_name}::text IN ('1', 't', 'true', 'TRUE', 'yes', 'on')
                            THEN TRUE
                        ELSE FALSE
                    END;

                ALTER TABLE {table_name}
                    ALTER COLUMN {column_name} SET DEFAULT {default};

                ALTER TABLE {table_name}
                    ALTER COLUMN {column_name} {null_clause};
            END IF;
        END $$;
        """
    )


def _normalize_string(table_name: str, column_name: str, *, length: int, nullable: bool) -> None:
    null_clause = "DROP NOT NULL" if nullable else "SET NOT NULL"
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
                  AND column_name = '{column_name}'
            ) THEN
                ALTER TABLE {table_name}
                    ALTER COLUMN {column_name} DROP DEFAULT;

                ALTER TABLE {table_name}
                    ALTER COLUMN {column_name}
                    TYPE VARCHAR({length})
                    USING {column_name}::text;

                ALTER TABLE {table_name}
                    ALTER COLUMN {column_name} {null_clause};
            END IF;
        END $$;
        """
    )
