"""tenant_scoped_uniqueness

Revision ID: bc3094830c04
Revises: 6e517a3c92a8
Create Date: 2026-07-23 01:26:48.623906

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc3094830c04'
down_revision: Union[str, None] = '6e517a3c92a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Categories table
    op.drop_constraint('uq_categories_slug', 'categories', type_='unique')
    op.create_unique_constraint('uq_categories_org_id_slug', 'categories', ['org_id', 'slug'])
    
    # Courses table
    op.drop_constraint('uq_courses_slug', 'courses', type_='unique')
    op.create_unique_constraint('uq_courses_org_id_slug', 'courses', ['org_id', 'slug'])

def downgrade() -> None:
    # Courses table
    op.drop_constraint('uq_courses_org_id_slug', 'courses', type_='unique')
    op.create_unique_constraint('uq_courses_slug', 'courses', ['slug'])
    
    # Categories table
    op.drop_constraint('uq_categories_org_id_slug', 'categories', type_='unique')
    op.create_unique_constraint('uq_categories_slug', 'categories', ['slug'])
