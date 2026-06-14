"""restore_timestamp_defaults

Revision ID: a5f005
Revises: a5f004
Create Date: 2026-06-12 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "a5f005"
down_revision: Union[str, None] = "a5f004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CREATED_AT_TABLES = (
    "activity_log",
    "allowed_domains",
    "audit_log",
    "auth_sessions",
    "builder_activity_log",
    "categories",
    "course_modules",
    "course_progress",
    "courses",
    "enrollment_requests",
    "learner_activity_log",
    "learner_events",
    "learning_path_progress",
    "learning_paths",
    "lesson_block_progress",
    "media_assets",
    "memberships",
    "module_progress",
    "notifications",
    "org_invitations",
    "organization_branding",
    "organizations",
    "pal_quiz_scores",
    "pal_recommendations",
    "pal_topic_performance",
    "password_reset_tokens",
    "pending_verifications",
    "quiz_definitions",
    "role_permissions",
    "tasks",
    "users",
)


def upgrade() -> None:
    for table_name in CREATED_AT_TABLES:
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
                      AND column_name = 'created_at'
                ) THEN
                    ALTER TABLE {table_name}
                        ALTER COLUMN created_at SET DEFAULT now();
                END IF;
            END $$;
            """
        )


def downgrade() -> None:
    pass
