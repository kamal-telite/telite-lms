"""Phase 3 — Database refactor & tenant isolation

Revision ID: 001_phase3
Revises:
Create Date: 2026-05-30

Changes:
  1. Add org_id to 4 tables missing it (activity_log, notifications,
     auth_sessions, password_reset_tokens)
  2. Add branding + plan columns to organizations
  3. Add price_paise column to courses
  4. Create memberships table (multi-org user support)
  5. Create PAL tables in PostgreSQL (migrated from SQLite)
  6. Add composite indexes for tenant-scoped queries
  7. Add foreign key constraints
  8. Enable PostgreSQL Row-Level Security on all tenant tables
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_phase3"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


# ── Upgrade ───────────────────────────────────────────────────────────────────

def upgrade() -> None:
    conn = op.get_bind()
    postgres = _is_postgres()

    # ── 1. Add org_id to tables missing it ───────────────────────────────────

    for table in ("activity_log", "notifications", "auth_sessions", "password_reset_tokens"):
        _add_column_if_missing(table, "org_id", sa.Integer(), server_default="1", nullable=False)

    # ── 1b. Add device-tracking columns to auth_sessions ─────────────────────
    _add_column_if_missing("auth_sessions", "user_agent", sa.Text(), nullable=True)
    _add_column_if_missing("auth_sessions", "ip_address", sa.String(50), nullable=True)

    # ── 2. Add branding + plan columns to organizations ───────────────────────

    org_new_cols = [
        ("favicon_url",        sa.Text(),        True),
        ("login_banner_url",   sa.Text(),        True),
        ("primary_color",      sa.String(20),    True),
        ("secondary_color",    sa.String(20),    True),
        ("font_family",        sa.String(100),   True),
        ("theme_mode",         sa.String(20),    False),
        ("certificate_template", sa.Text(),      True),
        ("email_template",     sa.Text(),        True),
        ("custom_domain",      sa.String(255),   True),
        ("plan",               sa.String(50),    False),
    ]
    for col_name, col_type, nullable in org_new_cols:
        default = None if nullable else ("light" if col_name == "theme_mode" else "free")
        _add_column_if_missing("organizations", col_name, col_type,
                               server_default=default, nullable=nullable)

    # ── 3. Add price_paise to courses ─────────────────────────────────────────

    _add_column_if_missing("courses", "price_paise", sa.Integer(),
                           server_default="0", nullable=False)

    # ── 4. Create memberships table ───────────────────────────────────────────

    if not _table_exists("memberships"):
        op.create_table(
            "memberships",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.String(50),
                      sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("org_id", sa.Integer(),
                      sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role", sa.String(50), nullable=False),
            sa.Column("category_scope", sa.String(100), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("granted_by", sa.String(50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("user_id", "org_id", name="uq_membership_user_org"),
        )
        op.create_index("idx_memberships_user", "memberships", ["user_id"])
        op.create_index("idx_memberships_org", "memberships", ["org_id"])

    # ── 5. Create PAL tables in PostgreSQL ────────────────────────────────────

    if not _table_exists("pal_quiz_scores"):
        op.create_table(
            "pal_quiz_scores",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("org_id", sa.Integer(), nullable=False),
            sa.Column("enrollment_number", sa.String(50), nullable=False),
            sa.Column("user_id", sa.String(50), nullable=True),
            sa.Column("course_id", sa.Integer(), nullable=False),
            sa.Column("course_name", sa.String(255), nullable=True),
            sa.Column("quiz_id", sa.Integer(), nullable=True),
            sa.Column("quiz_name", sa.String(255), nullable=True),
            sa.Column("topic", sa.String(100), nullable=True),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("max_score", sa.Float(), nullable=False, server_default="100"),
            sa.Column("percentage", sa.Float(), nullable=True),
            sa.Column("branch", sa.String(100), nullable=True),
            sa.Column("college", sa.String(255), nullable=True),
            sa.Column("synced_from_moodle", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_pal_scores_org_enrol", "pal_quiz_scores",
                        ["org_id", "enrollment_number"])

    if not _table_exists("pal_recommendations"):
        op.create_table(
            "pal_recommendations",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("org_id", sa.Integer(), nullable=False),
            sa.Column("enrollment_number", sa.String(50), nullable=False),
            sa.Column("user_id", sa.String(50), nullable=True),
            sa.Column("level", sa.String(20), nullable=False),
            sa.Column("weak_topics", sa.Text(), nullable=True),
            sa.Column("strong_topics", sa.Text(), nullable=True),
            sa.Column("recommended_courses", sa.Text(), nullable=True),
            sa.Column("recommended_resources", sa.Text(), nullable=True),
            sa.Column("avg_score", sa.Float(), nullable=True),
            sa.Column("email_sent", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_pal_recs_org_enrol", "pal_recommendations",
                        ["org_id", "enrollment_number"])

    if not _table_exists("pal_topic_performance"):
        op.create_table(
            "pal_topic_performance",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("org_id", sa.Integer(), nullable=False),
            sa.Column("enrollment_number", sa.String(50), nullable=False),
            sa.Column("user_id", sa.String(50), nullable=True),
            sa.Column("topic", sa.String(100), nullable=False),
            sa.Column("avg_score", sa.Float(), nullable=True),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("last_updated", sa.String(20), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("enrollment_number", "topic", "org_id",
                                name="uq_pal_topic_enrollment_org"),
        )
        op.create_index("idx_pal_topics_org_enrol", "pal_topic_performance",
                        ["org_id", "enrollment_number"])

    # ── 6. Composite indexes for tenant-scoped queries ────────────────────────

    _create_index_if_missing("idx_users_org_role",     "users",     ["org_id", "role"])
    _create_index_if_missing("idx_users_org_active",   "users",     ["org_id", "is_active"])
    _create_index_if_missing("idx_cats_org_status",    "categories",["organization_id", "status"])
    _create_index_if_missing("idx_courses_org_cat",    "courses",   ["org_id", "category_slug"])
    _create_index_if_missing("idx_enrol_org_status",   "enrollment_requests", ["org_id", "status"])
    _create_index_if_missing("idx_tasks_org_user",     "tasks",     ["org_id", "assigned_to_user_id"])
    _create_index_if_missing("idx_audit_org_time",     "audit_log", ["org_id", "created_at"])
    _create_index_if_missing("idx_notif_user_read",    "notifications", ["user_id", "is_read"])
    _create_index_if_missing("idx_sessions_user",      "auth_sessions", ["user_id"])
    _create_index_if_missing("idx_invites_org_email",  "org_invitations", ["org_id", "email"])

    # ── 7. Foreign key constraints (PostgreSQL only) ──────────────────────────

    if postgres:
        _add_fk_if_missing("fk_users_org",
                           "users", "org_id", "organizations", "id")
        _add_fk_if_missing("fk_categories_org",
                           "categories", "organization_id", "organizations", "id")
        _add_fk_if_missing("fk_courses_org",
                           "courses", "org_id", "organizations", "id")
        _add_fk_if_missing("fk_enrollments_org",
                           "enrollment_requests", "org_id", "organizations", "id")
        _add_fk_if_missing("fk_tasks_org",
                           "tasks", "org_id", "organizations", "id")
        _add_fk_if_missing("fk_sessions_user",
                           "auth_sessions", "user_id", "users", "id",
                           ondelete="CASCADE")
        _add_fk_if_missing("fk_prt_user",
                           "password_reset_tokens", "user_id", "users", "id",
                           ondelete="CASCADE")

    # ── 8. PostgreSQL Row-Level Security ──────────────────────────────────────

    if postgres:
        _apply_rls_policies(conn)


# ── Downgrade ─────────────────────────────────────────────────────────────────

def downgrade() -> None:
    postgres = _is_postgres()

    # Remove RLS policies
    if postgres:
        rls_tables = [
            "users", "categories", "courses", "enrollment_requests", "tasks",
            "audit_log", "activity_log", "notifications", "auth_sessions",
            "password_reset_tokens", "org_feature_flags", "org_invitations",
            "moodle_tenants", "moodle_sync_logs", "alert_rules",
            "pal_quiz_scores", "pal_recommendations", "pal_topic_performance",
        ]
        for table in rls_tables:
            op.execute(f"DROP POLICY IF EXISTS telite_tenant_isolation_{table} ON {table}")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Drop PAL tables
    for table in ("pal_topic_performance", "pal_recommendations", "pal_quiz_scores"):
        op.execute(f"DROP TABLE IF EXISTS {table}")

    # Drop memberships
    op.execute("DROP TABLE IF EXISTS memberships")

    # Remove added columns (best-effort)
    for col in ("price_paise",):
        _drop_column_if_exists("courses", col)
    for col in ("favicon_url", "login_banner_url", "primary_color", "secondary_color",
                "font_family", "theme_mode", "certificate_template", "email_template",
                "custom_domain", "plan"):
        _drop_column_if_exists("organizations", col)
    for table in ("activity_log", "notifications", "auth_sessions", "password_reset_tokens"):
        _drop_column_if_exists(table, "org_id")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    return conn.dialect.has_table(conn, table_name)


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in cols


def _index_exists(index_name: str, table_name: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    indexes = [i["name"] for i in insp.get_indexes(table_name)]
    return index_name in indexes


def _fk_exists(fk_name: str, table_name: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    fks = [fk["name"] for fk in insp.get_foreign_keys(table_name)]
    return fk_name in fks


def _add_column_if_missing(
    table: str,
    column: str,
    col_type,
    server_default=None,
    nullable: bool = True,
) -> None:
    if _table_exists(table) and not _column_exists(table, column):
        op.add_column(
            table,
            sa.Column(
                column,
                col_type,
                server_default=str(server_default) if server_default is not None else None,
                nullable=nullable,
            ),
        )


def _drop_column_if_exists(table: str, column: str) -> None:
    if _table_exists(table) and _column_exists(table, column):
        op.drop_column(table, column)


def _create_index_if_missing(index_name: str, table: str, columns: list[str]) -> None:
    if _table_exists(table) and not _index_exists(index_name, table):
        op.create_index(index_name, table, columns)


def _add_fk_if_missing(
    fk_name: str,
    src_table: str,
    src_col: str,
    ref_table: str,
    ref_col: str,
    ondelete: str = "SET NULL",
) -> None:
    if _table_exists(src_table) and not _fk_exists(fk_name, src_table):
        op.create_foreign_key(
            fk_name, src_table, ref_table, [src_col], [ref_col], ondelete=ondelete
        )


def _apply_rls_policies(conn) -> None:
    """Enable RLS and create tenant isolation policies on all scoped tables."""
    rls_tables = {
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

    for table, org_col in rls_tables.items():
        if not _table_exists(table):
            continue

        policy_name = f"telite_tenant_isolation_{table}"

        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        conn.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        conn.execute(sa.text(f"DROP POLICY IF EXISTS {policy_name} ON {table}"))
        conn.execute(
            sa.text(
                f"""
                CREATE POLICY {policy_name} ON {table}
                USING (
                    {org_col} = current_setting('app.current_org_id', true)::INTEGER
                    OR current_setting('app.bypass_rls', true) = 'on'
                )
                """
            )
        )
