"""force_rls_for_native_assignments

Revision ID: assignment_v1_rls_force_20260620
Revises: assignment_v1_20260620
Create Date: 2026-06-20 02:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "assignment_v1_rls_force_20260620"
down_revision: Union[str, None] = "assignment_v1_20260620"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE assignment_submissions FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE assignment_submissions NO FORCE ROW LEVEL SECURITY")
