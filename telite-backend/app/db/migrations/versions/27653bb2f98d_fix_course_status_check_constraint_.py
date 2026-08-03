"""fix_course_status_check_constraint_include_active

Revision ID: 27653bb2f98d
Revises: a798e4568bfc
Create Date: 2026-08-01 17:39:22.909202

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27653bb2f98d'
down_revision: Union[str, None] = 'a798e4568bfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the incorrect CHECK constraint
    op.drop_constraint('chk_courses_status', 'courses')
    
    # Add the corrected CHECK constraint that includes 'active'
    op.create_check_constraint(
        'chk_courses_status',
        'courses',
        "status IN ('draft', 'active', 'published', 'archived')"
    )


def downgrade() -> None:
    # Drop the corrected CHECK constraint
    op.drop_constraint('chk_courses_status', 'courses')
    
    # Restore the incorrect CHECK constraint (without 'active')
    op.create_check_constraint(
        'chk_courses_status',
        'courses',
        "status IN ('draft', 'published', 'archived')"
    )
