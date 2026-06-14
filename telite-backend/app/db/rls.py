"""
PostgreSQL Row-Level Security (RLS) policy management.

PHASE 3: Implements database-level tenant isolation so that even if
application code forgets to filter by org_id, the database itself
prevents cross-tenant data access.

Architecture:
- Every tenant-scoped table has RLS enabled
- A policy checks app.current_org_id (set per-transaction)
- Platform admins set app.bypass_rls = 'on' to see all rows
- SQLite environments skip RLS (development only)
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("telite.db.rls")

# Tables that require tenant isolation via RLS
TENANT_SCOPED_TABLES = [
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
]

# Column name used for tenant isolation per table
TABLE_ORG_COLUMN = {
    table: "org_id" for table in TENANT_SCOPED_TABLES
}


def apply_rls_policies(session: Session) -> None:
    """
    Create PostgreSQL RLS policies on all tenant-scoped tables.

    Called once during database initialisation (init_db).
    Safe to call multiple times — idempotent via DROP/CREATE.
    Skips tables that don't exist yet (future migrations).
    Each table is processed independently so one failure never blocks others.
    """
    applied = 0
    skipped = 0

    for table in TENANT_SCOPED_TABLES:
        # Skip tables that haven't been created yet
        exists = session.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = current_schema() AND table_name = :t"
            ),
            {"t": table},
        ).fetchone()
        if not exists:
            logger.debug("Skipping RLS for non-existent table: %s", table)
            skipped += 1
            continue

        org_col = TABLE_ORG_COLUMN.get(table, "org_id")
        policy_name = f"telite_tenant_isolation_{table}"

        try:
            # Enable RLS on the table
            session.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))

            # Drop existing policy if present (idempotent)
            session.execute(text(f"DROP POLICY IF EXISTS {policy_name} ON {table}"))

            # Create the tenant isolation policy:
            #   1. app.current_org_id matches the row's org column, OR
            #   2. app.bypass_rls is 'on' (platform admin)
            session.execute(
                text(
                    f"""
                    CREATE POLICY {policy_name} ON {table}
                    USING (
                        current_setting('app.bypass_rls', true) = 'on'
                        OR {org_col} = NULLIF(current_setting('app.current_org_id', true), '')::INTEGER
                    )
                    WITH CHECK (
                        current_setting('app.bypass_rls', true) = 'on'
                        OR {org_col} = NULLIF(current_setting('app.current_org_id', true), '')::INTEGER
                    )
                    """
                )
            )
            applied += 1
            logger.debug("RLS policy applied to table: %s", table)

        except Exception as exc:
            logger.warning("RLS skipped for table %s: %s", table, exc)
            skipped += 1

    logger.info(
        "PostgreSQL RLS complete — %d policies applied, %d skipped.",
        applied,
        skipped,
    )


def set_rls_context(session: Session, org_id: int) -> None:
    """Set the RLS context for the current transaction."""
    session.execute(
        text("SET LOCAL app.current_org_id = :org_id"),
        {"org_id": org_id},
    )
    session.execute(text("SET LOCAL app.bypass_rls = 'off'"))


def set_platform_context(session: Session) -> None:
    """Bypass RLS for platform-level operations."""
    session.execute(text("SET LOCAL app.bypass_rls = 'on'"))


def verify_rls_active(session: Session, table: str) -> bool:
    """Check whether RLS is enabled on a table (for health checks)."""
    result = session.execute(
        text(
            """
            SELECT rowsecurity
            FROM pg_tables
            WHERE tablename = :table
            AND schemaname = current_schema()
            """
        ),
        {"table": table},
    ).fetchone()
    return bool(result and result[0])
