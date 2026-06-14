"""normalize_tasks_table

Revision ID: a5f002
Revises: a5f001
Create Date: 2026-06-12 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "a5f002"
down_revision: Union[str, None] = "a5f001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
                RAISE EXCEPTION 'Cannot normalize tasks without at least one organization';
            END IF;

            UPDATE tasks
            SET org_id = default_org_id
            WHERE org_id IS NULL;

            ALTER TABLE tasks
                ALTER COLUMN org_id SET NOT NULL;

            ALTER TABLE tasks
                ALTER COLUMN created_at DROP DEFAULT;

            ALTER TABLE tasks
                ALTER COLUMN created_at
                TYPE TIMESTAMPTZ
                USING CASE
                    WHEN created_at IS NULL THEN now()
                    ELSE created_at::timestamptz
                END;

            ALTER TABLE tasks
                ALTER COLUMN created_at SET DEFAULT now();

            ALTER TABLE tasks
                ALTER COLUMN created_at SET NOT NULL;

            ALTER TABLE tasks
                ALTER COLUMN updated_at
                TYPE TIMESTAMPTZ
                USING CASE
                    WHEN updated_at IS NULL THEN NULL
                    ELSE updated_at::timestamptz
                END;

            ALTER TABLE tasks
                ALTER COLUMN updated_at DROP NOT NULL;

            ALTER TABLE tasks
                ALTER COLUMN is_cross_category DROP DEFAULT;

            ALTER TABLE tasks
                ALTER COLUMN is_cross_category
                TYPE BOOLEAN
                USING CASE
                    WHEN is_cross_category IS NULL THEN FALSE
                    WHEN is_cross_category::text IN ('1', 't', 'true', 'TRUE', 'yes', 'on')
                        THEN TRUE
                    ELSE FALSE
                END;

            ALTER TABLE tasks
                ALTER COLUMN is_cross_category SET DEFAULT false;

            ALTER TABLE tasks
                ALTER COLUMN is_cross_category SET NOT NULL;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_tasks_org_id_organizations'
            ) THEN
                ALTER TABLE tasks
                    ADD CONSTRAINT fk_tasks_org_id_organizations
                    FOREIGN KEY (org_id)
                    REFERENCES organizations(id)
                    ON DELETE CASCADE;
            END IF;

            ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'tasks'
                  AND policyname = 'tasks_tenant_isolation'
            ) THEN
                CREATE POLICY tasks_tenant_isolation
                ON tasks
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
        END $$;
        """
    )


def downgrade() -> None:
    pass
