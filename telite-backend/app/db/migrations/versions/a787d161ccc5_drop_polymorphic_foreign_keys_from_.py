"""drop polymorphic foreign keys from progression_rules

Revision ID: a787d161ccc5
Revises: 2eda72aef2a4
Create Date: 2026-07-24 11:16:02.767587

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a787d161ccc5'
down_revision: Union[str, None] = '2eda72aef2a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # We use batch_alter_table to ensure cross-database compatibility (though this is Postgres)
    with op.batch_alter_table('progression_rules', schema=None) as batch_op:
        # We drop the constraints using their exact names from the original migration
        batch_op.drop_constraint('fk_progression_rules_module', type_='foreignkey')
        batch_op.drop_constraint('fk_progression_rules_section', type_='foreignkey')


def downgrade() -> None:
    with op.batch_alter_table('progression_rules', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_progression_rules_module',
            'course_modules',
            ['target_id'],
            ['id'],
            ondelete='CASCADE'
        )
        batch_op.create_foreign_key(
            'fk_progression_rules_section',
            'course_sections',
            ['target_id'],
            ['id'],
            ondelete='CASCADE'
        )
