"""Phase A.5 RLS and tenant isolation verification.

These tests are intentionally opt-in for live database execution because they
inspect PostgreSQL RLS metadata and may create transactional fixture rows.

Run against Docker/local Postgres with:
    $env:TELITE_RUN_LIVE_RLS_TESTS="1"
    $env:TELITE_TEST_DATABASE_URL="postgresql+psycopg://postgres:postgres123@localhost:55432/telite_backend"
    pytest tests/test_rls_isolation.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.rls import TENANT_SCOPED_TABLES  # noqa: E402

pytestmark = pytest.mark.skipif(
    os.getenv("TELITE_RUN_LIVE_RLS_TESTS") != "1",
    reason="Set TELITE_RUN_LIVE_RLS_TESTS=1 to run live RLS tests.",
)


def _engine():
    url = os.getenv("TELITE_TEST_DATABASE_URL") or os.getenv("TELITE_DATABASE_URL")
    if not url:
        pytest.skip("TELITE_TEST_DATABASE_URL or TELITE_DATABASE_URL is required")
    return create_engine(
        url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
        .replace("postgresql://", "postgresql+psycopg://", 1)
        .replace("postgres://", "postgresql+psycopg://", 1),
        future=True,
    )


def _probe_engine():
    base_url = make_url(str(_engine().url))
    probe_url = base_url.set(username="telite_rls_probe", password="telite_rls_probe")
    return create_engine(probe_url, future=True)


def test_tenant_owned_tables_have_rls_enabled():
    engine = _engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT c.relname, c.relrowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relkind = 'r'
                """
            )
        ).all()

    rls = {row.relname: bool(row.relrowsecurity) for row in rows}
    missing = sorted(table for table in TENANT_SCOPED_TABLES if table in rls and not rls[table])
    assert missing == []


def test_tenant_context_filters_users_when_rls_is_active():
    engine = _engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT c.relrowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname = 'users'
                """
            )
        ).scalar()
        assert row is True

        # This verifies the app-level tenant context is settable. Full data
        # isolation assertions should run with the non-owner app DB role because
        # PostgreSQL table owners and superusers can bypass RLS.
        conn.execute(text("SELECT set_config('app.current_org_id', '1', true)"))
        current_org = conn.execute(text("SELECT current_setting('app.current_org_id', true)")).scalar()
        assert current_org == "1"


def test_two_tenant_rls_blocks_unfiltered_cross_tenant_reads():
    engine = _engine()
    tenant_a = 920001
    tenant_b = 920002
    probe_role = "telite_rls_probe"
    table_checks = {
        "users": "id",
        "categories": "id",
        "courses": "id",
        "notifications": "id",
        "audit_log": "id",
        "media_assets": "id",
        "role_permissions": "id",
        "course_versions": "id",
        "builder_activity_log": "id",
    }

    cleanup_sql = [
        "DELETE FROM builder_activity_log WHERE org_id IN (:tenant_a, :tenant_b)",
        "DELETE FROM course_versions WHERE org_id IN (:tenant_a, :tenant_b)",
        "DELETE FROM media_assets WHERE org_id IN (:tenant_a, :tenant_b)",
        "DELETE FROM role_permissions WHERE org_id IN (:tenant_a, :tenant_b)",
        "DELETE FROM audit_log WHERE org_id IN (:tenant_a, :tenant_b)",
        "DELETE FROM notifications WHERE org_id IN (:tenant_a, :tenant_b)",
        "DELETE FROM courses WHERE org_id IN (:tenant_a, :tenant_b)",
        "DELETE FROM categories WHERE org_id IN (:tenant_a, :tenant_b)",
        "DELETE FROM users WHERE org_id IN (:tenant_a, :tenant_b)",
        "DELETE FROM organizations WHERE id IN (:tenant_a, :tenant_b)",
    ]

    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{probe_role}') THEN
                        DROP OWNED BY {probe_role};
                        DROP ROLE {probe_role};
                    END IF;
                END $$;
                """
            )
        )
        conn.execute(text(f"CREATE ROLE {probe_role} LOGIN PASSWORD 'telite_rls_probe'"))
        conn.execute(
            text(
                f"""
                DO $$
                BEGIN
                    EXECUTE format('GRANT CONNECT ON DATABASE %I TO {probe_role}', current_database());
                END $$;
                """
            )
        )
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {probe_role}"))
        conn.execute(text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {probe_role}"))
        conn.execute(text("SELECT set_config('app.bypass_rls', 'on', true)"))
        for statement in cleanup_sql:
            conn.execute(text(statement), {"tenant_a": tenant_a, "tenant_b": tenant_b})

        conn.execute(
            text(
                """
                INSERT INTO organizations (id, name, type, domain, slug, status, plan)
                VALUES
                    (:tenant_a, 'Phase A5 Tenant A', 'company', 'a5-a.example.test', 'phase-a5-a', 'active', 'test'),
                    (:tenant_b, 'Phase A5 Tenant B', 'company', 'a5-b.example.test', 'phase-a5-b', 'active', 'test')
                """
            ),
            {"tenant_a": tenant_a, "tenant_b": tenant_b},
        )
        conn.execute(
            text(
                """
                INSERT INTO users (
                    id, username, email, full_name, role, password_hash, avatar_initials,
                    gradient_start, gradient_end, org_id, organization_id, is_active,
                    is_platform_admin, status
                )
                VALUES
                    ('a5-user-a', 'a5_user_a', 'a5-user-a@example.test', 'A5 User A',
                     'superadmin', 'x', 'AA', '#111111', '#222222', :tenant_a, :tenant_a, true, false, 'active'),
                    ('a5-user-b', 'a5_user_b', 'a5-user-b@example.test', 'A5 User B',
                     'superadmin', 'x', 'BB', '#333333', '#444444', :tenant_b, :tenant_b, true, false, 'active')
                """
            ),
            {"tenant_a": tenant_a, "tenant_b": tenant_b},
        )
        conn.execute(
            text(
                """
                INSERT INTO categories (
                    id, name, slug, status, accent_color, org_id, organization_id, org_type
                )
                VALUES
                    ('a5-cat-a', 'A5 Category A', 'a5-cat-a', 'active', '#111111', :tenant_a, :tenant_a, 'company'),
                    ('a5-cat-b', 'A5 Category B', 'a5-cat-b', 'active', '#222222', :tenant_b, :tenant_b, 'company')
                """
            ),
            {"tenant_a": tenant_a, "tenant_b": tenant_b},
        )
        conn.execute(
            text(
                """
                INSERT INTO courses (id, category_slug, name, slug, description, tier, status, org_id)
                VALUES
                    ('a5-course-a', 'a5-cat-a', 'A5 Course A', 'a5-course-a', 'Tenant A course', 'Basic', 'active', :tenant_a),
                    ('a5-course-b', 'a5-cat-b', 'A5 Course B', 'a5-course-b', 'Tenant B course', 'Basic', 'active', :tenant_b)
                """
            ),
            {"tenant_a": tenant_a, "tenant_b": tenant_b},
        )
        conn.execute(
            text(
                """
                INSERT INTO notifications (user_id, title, body, type, org_id)
                VALUES
                    ('a5-user-a', 'A notification', 'Tenant A notification', 'info', :tenant_a),
                    ('a5-user-b', 'B notification', 'Tenant B notification', 'info', :tenant_b)
                """
            ),
            {"tenant_a": tenant_a, "tenant_b": tenant_b},
        )
        conn.execute(
            text(
                """
                INSERT INTO audit_log (
                    actor_user_id, actor_name, action, target_type, target_id,
                    message, accent, result, org_id
                )
                VALUES
                    ('a5-user-a', 'A5 User A', 'a5.test', 'course', 'a5-course-a',
                     'Tenant A audit', '#111111', 'success', :tenant_a),
                    ('a5-user-b', 'A5 User B', 'a5.test', 'course', 'a5-course-b',
                     'Tenant B audit', '#222222', 'success', :tenant_b)
                """
            ),
            {"tenant_a": tenant_a, "tenant_b": tenant_b},
        )
        conn.execute(
            text(
                """
                INSERT INTO media_assets (
                    org_id, filename, object_key, asset_version, size_bytes,
                    mime_type, uploaded_by
                )
                VALUES
                    (:tenant_a, 'a5-a.png', 'a5/a.png', 1, 10, 'image/png', 'a5-user-a'),
                    (:tenant_b, 'a5-b.png', 'a5/b.png', 1, 10, 'image/png', 'a5-user-b')
                """
            ),
            {"tenant_a": tenant_a, "tenant_b": tenant_b},
        )
        conn.execute(
            text(
                """
                INSERT INTO role_permissions (org_id, role, permission_key, enabled)
                VALUES
                    (:tenant_a, 'superadmin', 'a5.permission.a', true),
                    (:tenant_b, 'superadmin', 'a5.permission.b', true)
                """
            ),
            {"tenant_a": tenant_a, "tenant_b": tenant_b},
        )
        conn.execute(
            text(
                """
                INSERT INTO course_versions (course_id, org_id, version_number, status, published_by, snapshot_json)
                VALUES
                    ('a5-course-a', :tenant_a, 1, 'draft', 'a5-user-a', '{"tenant":"a"}'),
                    ('a5-course-b', :tenant_b, 1, 'draft', 'a5-user-b', '{"tenant":"b"}')
                """
            ),
            {"tenant_a": tenant_a, "tenant_b": tenant_b},
        )
        conn.execute(
            text(
                """
                INSERT INTO builder_activity_log (course_id, user_id, action, payload, org_id)
                VALUES
                    ('a5-course-a', 'a5-user-a', 'a5.builder', '{"tenant":"a"}', :tenant_a),
                    ('a5-course-b', 'a5-user-b', 'a5.builder', '{"tenant":"b"}', :tenant_b)
                """
            ),
            {"tenant_a": tenant_a, "tenant_b": tenant_b},
        )

    probe_engine = _probe_engine()
    try:
        with probe_engine.connect() as conn:
            for table_name, id_column in table_checks.items():
                conn.execute(text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": str(tenant_a)})
                rows = conn.execute(text(f"SELECT org_id FROM {table_name} ORDER BY {id_column}")).all()
                assert rows, table_name
                assert {row.org_id for row in rows} == {tenant_a}, table_name

                conn.execute(text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": str(tenant_b)})
                rows = conn.execute(text(f"SELECT org_id FROM {table_name} ORDER BY {id_column}")).all()
                assert rows, table_name
                assert {row.org_id for row in rows} == {tenant_b}, table_name

            conn.execute(text("SELECT set_config('app.bypass_rls', 'on', true)"))
            rows = conn.execute(text("SELECT DISTINCT org_id FROM users WHERE org_id IN (:tenant_a, :tenant_b)"), {"tenant_a": tenant_a, "tenant_b": tenant_b}).all()
            assert {row.org_id for row in rows} == {tenant_a, tenant_b}
    finally:
        probe_engine.dispose()
        with engine.begin() as conn:
            conn.execute(text("SELECT set_config('app.bypass_rls', 'on', true)"))
            for statement in cleanup_sql:
                conn.execute(text(statement), {"tenant_a": tenant_a, "tenant_b": tenant_b})
            conn.execute(text(f"DROP OWNED BY {probe_role}"))
            conn.execute(text(f"DROP ROLE IF EXISTS {probe_role}"))
