"""classify_remaining_tables

Revision ID: a5f006
Revises: a5f005
Create Date: 2026-06-12 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "a5f006"
down_revision: Union[str, None] = "a5f005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TENANT_TABLES = ("alert_rules", "moodle_tenants", "moodle_sync_logs")


def upgrade() -> None:
    for table_name in TENANT_TABLES:
        _require_org_id(table_name)
        _add_org_fk(table_name)
        _enable_rls(table_name)


def downgrade() -> None:
    pass


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
