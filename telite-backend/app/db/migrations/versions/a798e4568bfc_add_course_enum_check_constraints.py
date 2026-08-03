"""add_course_enum_check_constraints

Revision ID: a798e4568bfc
Revises: 82a9a3f48a00
Create Date: 2026-08-01 17:31:47.002782

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a798e4568bfc'
down_revision: Union[str, None] = '82a9a3f48a00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add CHECK constraint for courses.status
    op.create_check_constraint(
        'chk_courses_status',
        'courses',
        "status IN ('draft', 'published', 'archived')"
    )
    
    # Add CHECK constraint for courses.tier
    op.create_check_constraint(
        'chk_courses_tier',
        'courses',
        "tier IN ('Basic', 'Premium', 'Enterprise')"
    )


def downgrade() -> None:
    # Remove CHECK constraint for courses.status
    op.drop_constraint('chk_courses_status', 'courses')
    
    # Remove CHECK constraint for courses.tier
    op.drop_constraint('chk_courses_tier', 'courses')
