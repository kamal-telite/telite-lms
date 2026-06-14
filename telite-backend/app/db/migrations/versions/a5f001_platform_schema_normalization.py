"""phase_a5_platform_schema_normalization

Revision ID: a5f001
Revises: a1b2c3d4e5f6
Create Date: 2026-06-12 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "a5f001"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CORE_TIMESTAMP_TABLES = (
    "organizations",
    "users",
    "categories",
    "courses",
    "organization_branding",
    "auth_sessions",
    "enrollment_requests",
    "notifications",
    "role_permissions",
)

CORE_TENANT_TABLES = (
    "users",
    "categories",
    "courses",
    "organization_branding",
    "auth_sessions",
    "enrollment_requests",
    "notifications",
    "role_permissions",
)


def upgrade() -> None:
    _create_role_permissions_table()
    _normalize_core_timestamps()
    _normalize_core_booleans()
    _normalize_core_org_ids()
    _enable_core_rls()


def downgrade() -> None:
    # Phase A.5 normalization is intentionally forward-only for data safety.
    # Reverting strong types back to TEXT/INTEGER would reintroduce production
    # failures and can lose timezone/boolean semantics.
    pass


def _create_role_permissions_table() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS role_permissions (
            id SERIAL PRIMARY KEY,
            org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            role VARCHAR(50) NOT NULL,
            permission_key VARCHAR(120) NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NULL,
            UNIQUE (org_id, role, permission_key)
        );
        CREATE INDEX IF NOT EXISTS ix_role_permissions_org_id
            ON role_permissions (org_id);
        CREATE INDEX IF NOT EXISTS ix_role_permissions_role
            ON role_permissions (role);
        CREATE INDEX IF NOT EXISTS ix_role_permissions_permission_key
            ON role_permissions (permission_key);
        """
    )


def _normalize_core_timestamps() -> None:
    for table_name in CORE_TIMESTAMP_TABLES:
        _alter_timestamp_if_exists(table_name, "created_at", nullable=False)
        _alter_timestamp_if_exists(table_name, "updated_at", nullable=True)


def _alter_timestamp_if_exists(table_name: str, column_name: str, nullable: bool) -> None:
    null_clause = "DROP NOT NULL" if nullable else "SET NOT NULL"
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = '{table_name}'
                  AND column_name = '{column_name}'
            ) THEN
                UPDATE {table_name}
                SET {column_name} = now()
                WHERE {column_name} IS NULL;

                ALTER TABLE {table_name}
                    ALTER COLUMN {column_name}
                    TYPE TIMESTAMPTZ
                    USING CASE
                        WHEN {column_name} IS NULL THEN now()
                        ELSE {column_name}::timestamptz
                    END;

                ALTER TABLE {table_name}
                    ALTER COLUMN {column_name}
                    SET DEFAULT now();

                ALTER TABLE {table_name}
                    ALTER COLUMN {column_name}
                    {null_clause};
            END IF;
        END $$;
        """
    )


def _normalize_core_booleans() -> None:
    _alter_boolean_if_exists("users", "is_active", default="true", nullable=False)
    _alter_boolean_if_exists("users", "is_platform_admin", default="false", nullable=False)
    _alter_boolean_if_exists("role_permissions", "enabled", default="true", nullable=False)


def _alter_boolean_if_exists(
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
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = '{table_name}'
                  AND column_name = '{column_name}'
            ) THEN
                ALTER TABLE {table_name}
                    ALTER COLUMN {column_name}
                    DROP DEFAULT;

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
                    ALTER COLUMN {column_name}
                    SET DEFAULT {default};

                ALTER TABLE {table_name}
                    ALTER COLUMN {column_name}
                    {null_clause};
            END IF;
        END $$;
        """
    )


def _normalize_core_org_ids() -> None:
    _add_org_id_to_organization_branding()

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

            IF default_org_id IS NULL THEN
                RAISE EXCEPTION 'Cannot normalize tenant tables without at least one organization';
            END IF;

            UPDATE users
            SET org_id = COALESCE(org_id, organization_id, default_org_id)
            WHERE org_id IS NULL;

            UPDATE categories
            SET org_id = COALESCE(org_id, organization_id, default_org_id)
            WHERE org_id IS NULL;

            UPDATE courses
            SET org_id = default_org_id
            WHERE org_id IS NULL;
        END $$;
        """
    )

    for table_name in CORE_TENANT_TABLES:
        _require_org_id(table_name)
        _add_org_fk_if_missing(table_name)


def _add_org_id_to_organization_branding() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.organization_branding') IS NOT NULL
            AND NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'organization_branding'
                  AND column_name = 'org_id'
            ) THEN
                ALTER TABLE organization_branding
                    ADD COLUMN org_id INTEGER;

                UPDATE organization_branding
                SET org_id = organization_id;

                CREATE INDEX IF NOT EXISTS ix_organization_branding_org_id
                    ON organization_branding (org_id);
            END IF;
        END $$;
        """
    )


def _require_org_id(table_name: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
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


def _add_org_fk_if_missing(table_name: str) -> None:
    constraint_name = f"fk_{table_name}_org_id_organizations"
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = '{table_name}'
                  AND column_name = 'org_id'
            )
            AND NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = '{constraint_name}'
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


def _enable_core_rls() -> None:
    for table_name in CORE_TENANT_TABLES:
        policy_name = f"{table_name}_tenant_isolation"
        op.execute(
            f"""
            DO $$
            BEGIN
                IF to_regclass('public.{table_name}') IS NOT NULL THEN
                    ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_policies
                        WHERE schemaname = 'public'
                          AND tablename = '{table_name}'
                          AND policyname = '{policy_name}'
                    ) THEN
                        CREATE POLICY {policy_name}
                        ON {table_name}
                        USING (
                            current_setting('app.current_org_id', true) = ''
                            OR current_setting('app.current_org_id', true) IS NULL
                            OR org_id = current_setting('app.current_org_id', true)::integer
                        )
                        WITH CHECK (
                            current_setting('app.current_org_id', true) = ''
                            OR current_setting('app.current_org_id', true) IS NULL
                            OR org_id = current_setting('app.current_org_id', true)::integer
                        );
                    END IF;
                END IF;
            END $$;
            """
        )
