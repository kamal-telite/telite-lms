"""Reserve assignment submissions migration revision.

Revision ID: c1669e51aea9
Revises: a5f009
Create Date: 2026-06-17 09:09:32.685339

This revision previously contained a broad Alembic autogenerate diff that
attempted to mutate unrelated tables during the assignment rollout. The actual
assignment_submissions table is created by the following guarded migration
0e000a2a9613, and the V1 assignment engine is completed by the later
assignment_v1_* migrations.
"""
from __future__ import annotations

from typing import Sequence, Union


revision: str = "c1669e51aea9"
down_revision: Union[str, None] = "a5f009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Compatibility revision; schema changes are handled by later migrations."""


def downgrade() -> None:
    """Compatibility revision; no schema changes to reverse."""
