"""Bootstrap foundational Telite LMS schema.

Revision ID: 000_bootstrap
Revises:
Create Date: 2026-06-15

This migration captures the schema that existed before the Phase 3 tenant
isolation migration was introduced.  It intentionally creates only the
foundational/pre-Phase-3 tables; later historical migrations continue to own
their phase-specific additions.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "000_bootstrap"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    _create_table_if_missing(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("moodle_category_id", sa.Integer(), nullable=True),
        sa.Column("moodle_tenant_key", sa.String(100), nullable=True),
        sa.Column("admin_user_id", sa.String(50), nullable=True),
        sa.Column("created_by", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("name", name="uq_organizations_name"),
        sa.UniqueConstraint("domain", name="uq_organizations_domain"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )

    _create_table_if_missing(
        "users",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("category_scope", sa.String(100), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("avatar_initials", sa.String(5), nullable=False),
        sa.Column("gradient_start", sa.String(50), nullable=False),
        sa.Column("gradient_end", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("pal_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pal_completion_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pal_quiz_avg", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pal_time_spent_hours", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pal_task_completion_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("streak_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("courses_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_courses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cohort_rank", sa.Integer(), nullable=True),
        sa.Column("enrollment_type", sa.String(50), nullable=True),
        sa.Column("current_course_id", sa.String(50), nullable=True),
        sa.Column("course_progress_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("program", sa.String(100), nullable=True),
        sa.Column("branch", sa.String(100), nullable=True),
        sa.Column("id_number", sa.String(50), nullable=True),
        sa.Column("moodle_id", sa.Integer(), nullable=True),
        sa.Column("last_login", sa.String(20), nullable=True),
        sa.Column("invited_via", sa.String(50), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], name="fk_users_org", ondelete="CASCADE"),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    _create_table_if_missing(
        "categories",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("accent_color", sa.String(20), nullable=False, server_default="#2563EB"),
        sa.Column("admin_user_id", sa.String(50), nullable=True),
        sa.Column("planned_courses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_pal_target", sa.Float(), nullable=False, server_default="0"),
        sa.Column("moodle_category_id", sa.Integer(), nullable=True),
        sa.Column("org_type", sa.String(50), nullable=False, server_default="college"),
        sa.Column("archived_at", sa.String(20), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_categories_org", ondelete="SET NULL"
        ),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )

    _create_table_if_missing(
        "courses",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("moodle_course_id", sa.Integer(), nullable=True),
        sa.Column("category_slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("tier", sa.String(50), nullable=False, server_default="Basic"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("module_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("modules_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("lessons_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hours", sa.Float(), nullable=False, server_default="0"),
        sa.Column("enrolled_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("completion_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_quiz_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("prerequisite_course_id", sa.String(50), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], name="fk_courses_org", ondelete="CASCADE"),
        sa.UniqueConstraint("slug", name="uq_courses_slug"),
    )

    _create_table_if_missing(
        "enrollment_requests",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("category_slug", sa.String(100), nullable=False),
        sa.Column("request_type", sa.String(50), nullable=False),
        sa.Column("company_domain", sa.String(255), nullable=True),
        sa.Column("domain_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.String(20), nullable=False),
        sa.Column("reviewed_by", sa.String(50), nullable=True),
        sa.Column("reviewed_at", sa.String(20), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"], name="fk_enrollments_org", ondelete="CASCADE"
        ),
    )

    _create_table_if_missing(
        "tasks",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("assigned_label", sa.String(255), nullable=False),
        sa.Column("assigned_to_user_id", sa.String(50), nullable=True),
        sa.Column("assignment_scope", sa.String(50), nullable=False, server_default="individual"),
        sa.Column("category_slug", sa.String(100), nullable=False),
        sa.Column("due_at", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("assigned_by", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_cross_category", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], name="fk_tasks_org", ondelete="CASCADE"),
    )

    _create_table_if_missing(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("actor_user_id", sa.String(50), nullable=True),
        sa.Column("actor_name", sa.String(255), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("accent", sa.String(20), nullable=False, server_default="#2563EB"),
        sa.Column("result", sa.String(20), nullable=False, server_default="success"),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    _create_table_if_missing(
        "activity_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(50), nullable=True),
        sa.Column("category_slug", sa.String(100), nullable=True),
        sa.Column("icon", sa.String(50), nullable=False),
        sa.Column("accent", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    _create_table_if_missing(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, server_default="info"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    _create_table_if_missing(
        "auth_sessions",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("user_id", sa.String(50), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.String(20), nullable=False),
        sa.Column("revoked_at", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_sessions_user", ondelete="CASCADE"),
        sa.UniqueConstraint("refresh_token", name="uq_auth_sessions_refresh_token"),
    )

    _create_table_if_missing(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(50), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("expires_at", sa.String(), nullable=False),
        sa.Column("used_at", sa.String(), nullable=True),
        sa.Column("delivery_status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("delivery_error", sa.String(), nullable=True),
        sa.Column("delivery_attempted_at", sa.String(), nullable=True),
        sa.Column("delivered_at", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_prt_user", ondelete="CASCADE"),
        sa.UniqueConstraint("token", name="uq_password_reset_tokens_token"),
    )

    _create_table_if_missing(
        "organization_branding",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("favicon_url", sa.Text(), nullable=True),
        sa.Column("login_banner_url", sa.Text(), nullable=True),
        sa.Column("primary_color", sa.String(20), nullable=True),
        sa.Column("secondary_color", sa.String(20), nullable=True),
        sa.Column("font_family", sa.String(100), nullable=True),
        sa.Column("theme_mode", sa.String(20), nullable=False, server_default="light"),
        sa.Column("certificate_template_url", sa.Text(), nullable=True),
        sa.Column("email_template_id", sa.String(100), nullable=True),
        sa.Column("landing_page_config", sa.Text(), nullable=True),
        sa.Column("terminology_json", sa.Text(), nullable=True),
        sa.Column("seo_title", sa.String(255), nullable=True),
        sa.Column("seo_description", sa.Text(), nullable=True),
        sa.Column("custom_domain", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"], name="fk_organization_branding_org_id_organizations", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_organization_branding_organization_id", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("organization_id", name="uq_organization_branding_organization_id"),
    )

    _create_table_if_missing(
        "org_invitations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("category_scope", sa.String(), nullable=True),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("invited_by", sa.String(), nullable=True),
        sa.Column("expires_at", sa.String(), nullable=False),
        sa.Column("accepted_at", sa.String(), nullable=True),
        sa.Column("revoked_at", sa.String(), nullable=True),
        sa.Column("revoked_by", sa.String(), nullable=True),
        sa.Column("revoke_reason", sa.String(), nullable=True),
        sa.Column("resend_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_sent_at", sa.String(), nullable=True),
        sa.Column("last_resent_at", sa.String(), nullable=True),
        sa.Column("delivery_status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("delivery_error", sa.String(), nullable=True),
        sa.Column("delivery_attempted_at", sa.String(), nullable=True),
        sa.Column("delivered_at", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"], name="fk_org_invitations_org_id_organizations", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("token", name="uq_org_invitations_token"),
    )

    _create_table_if_missing(
        "pending_verifications",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role_name", sa.String(), nullable=False),
        sa.Column("domain_type", sa.String(), nullable=False),
        sa.Column("organization_name", sa.String(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("employee_id", sa.String(), nullable=True),
        sa.Column("department", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("rejection_reason", sa.String(), nullable=True),
        sa.Column("reviewed_by", sa.String(), nullable=True),
        sa.Column("reviewed_at", sa.String(), nullable=True),
        sa.Column("moodle_id", sa.Integer(), nullable=True),
        sa.Column("program", sa.String(), nullable=True),
        sa.Column("branch", sa.String(), nullable=True),
        sa.Column("id_number", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_pending_verifications_email"),
    )

    _create_table_if_missing(
        "allowed_domains",
        sa.Column("domain", sa.String(), primary_key=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("added_by", sa.String(), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    _create_table_if_missing(
        "platform_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("setting_key", sa.String(), nullable=False),
        sa.Column("setting_value_json", sa.String(), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.UniqueConstraint("setting_key", name="uq_platform_settings_setting_key"),
    )

    _create_indexes()


def downgrade() -> None:
    for table_name in (
        "platform_settings",
        "allowed_domains",
        "pending_verifications",
        "org_invitations",
        "organization_branding",
        "password_reset_tokens",
        "auth_sessions",
        "notifications",
        "activity_log",
        "audit_log",
        "tasks",
        "enrollment_requests",
        "courses",
        "categories",
        "users",
        "organizations",
    ):
        if _table_exists(table_name):
            op.drop_table(table_name)


def _create_indexes() -> None:
    indexes = (
        ("ix_users_username", "users", ["username"]),
        ("ix_users_email", "users", ["email"]),
        ("ix_users_role", "users", ["role"]),
        ("ix_users_org_id", "users", ["org_id"]),
        ("ix_categories_slug", "categories", ["slug"]),
        ("ix_categories_org_id", "categories", ["org_id"]),
        ("ix_courses_category_slug", "courses", ["category_slug"]),
        ("ix_courses_org_id", "courses", ["org_id"]),
        ("ix_enrollment_requests_email", "enrollment_requests", ["email"]),
        ("ix_enrollment_requests_category_slug", "enrollment_requests", ["category_slug"]),
        ("ix_enrollment_requests_status", "enrollment_requests", ["status"]),
        ("ix_enrollment_requests_org_id", "enrollment_requests", ["org_id"]),
        ("ix_tasks_assigned_to_user_id", "tasks", ["assigned_to_user_id"]),
        ("ix_tasks_category_slug", "tasks", ["category_slug"]),
        ("ix_tasks_status", "tasks", ["status"]),
        ("ix_tasks_org_id", "tasks", ["org_id"]),
        ("ix_audit_log_action", "audit_log", ["action"]),
        ("ix_audit_log_org_id", "audit_log", ["org_id"]),
        ("ix_activity_log_user_id", "activity_log", ["user_id"]),
        ("ix_notifications_user_id", "notifications", ["user_id"]),
        ("ix_auth_sessions_user_id", "auth_sessions", ["user_id"]),
        ("ix_organization_branding_org_id", "organization_branding", ["org_id"]),
    )
    for index_name, table_name, columns in indexes:
        _create_index_if_missing(index_name, table_name, columns)


def _create_table_if_missing(table_name: str, *columns, **kwargs) -> None:
    if not _table_exists(table_name):
        op.create_table(table_name, *columns, **kwargs)


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    if not _table_exists(table_name):
        return

    conn = op.get_bind()
    existing = {index["name"] for index in sa.inspect(conn).get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns)


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    return conn.dialect.has_table(conn, table_name)
