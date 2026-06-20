"""Add status constraint

Revision ID: onboarding_username_2
Revises: onboarding_username_1
Create Date: 2026-06-19 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'onboarding_username_2'
down_revision = 'onboarding_username_1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        # We explicitly add the constraint
        batch_op.create_check_constraint(
            'chk_users_status',
            "status IN ('active', 'suspended', 'disabled')"
        )


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('chk_users_status', type_='check')
