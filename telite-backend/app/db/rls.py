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
    "users",
    "categories",
    "courses",
    "enrollment_requests",
    "tasks",
    "audit_log",
    "activity_log",
    "notifications",
    "auth_sessions",
    "password_reset_tokens",
    "org_feature_flags",
    "org_invitations",
    "moodle_tenants",
    "moodle_sync_logs",
    "alert_rules",
    "pal_quiz_scores",
    "pal_recommendations",
    "pal_topic_performance",
]

# Column name used for tenant isolation per table
TABLE_ORG_COLUMN = {
    "users": "org_id",
    "categories": "organization_id",
    "courses": "org_id",
    "enrollment_requests": "org_id",
    "tasks": "org_id",
    "audit_log": "org_id",
    "activity_log": "org_id",
    "notifications": "org_id",
    "auth_sessions": "org_id",
    "password_reset_tokens": "org_id",
    "org_feature_flags": "org_id",
    "org_invitations": "org_id",
    "moodle_tenants": "org_id",
    "moodle_sync_logs": "org_id",
    "alert_rules": "org_id",
    "pal_quiz_scores": "org_id",
    "pal_recommendations": "org_id",
    "pal_topic_performance": "org_id",
}


def apply_rls_policies(session: Session) -> None:
    """
    Create PostgreSQL RLS policies on all tenant-scoped tables.

    Called once during database initialisation (init_db).
    Safe to call multiple times — uses CREATE POLICY IF NOT EXISTS pattern.
    """
    for table in TENANT_SCOPED_TABLES:
        org_col = TABLE_ORG_COLUMN.get(table, "org_id")
        policy_name = f"telite_tenant_isolation_{table}"

        # Enable RLS on the table
        session.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))

        # Force RLS even for table owner (prevents accidental bypass)
        session.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))

        # Drop existing policy if present (idempotent)
        session.execute(
            text(f"DROP POLICY IF EXISTS {policy_name} ON {table}")
        )

        # Create the tenant isolation policy
        # Rows are visible when:
        #   1. app.current_org_id matches the row's org column, OR
        #   2. app.bypass_rls is set to 'on' (platform admin)
        session.execute(
            text(
                f"""
                CREATE POLICY {policy_name} ON {table}
                USING (
                    {org_col} = current_setting('app.current_org_id', true)::INTEGER
                    OR current_setting('app.bypass_rls', true) = 'on'
                )
                """
            )
        )

        logger.debug("RLS policy applied to table: %s", table)

    logger.info("PostgreSQL RLS policies applied to %d tables.", len(TENANT_SCOPED_TABLES))


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
