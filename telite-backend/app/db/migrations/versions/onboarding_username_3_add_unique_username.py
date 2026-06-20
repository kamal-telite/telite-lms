"""Add UNIQUE username constraint

Revision ID: onboarding_username_3
Revises: onboarding_username_2
Create Date: 2026-06-19 01:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'onboarding_username_3'
down_revision = 'onboarding_username_2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Check if constraint or index already exists to avoid crashing
    unique_constraints = [c['name'] for c in inspector.get_unique_constraints('users')]
    indexes = [i['name'] for i in inspector.get_indexes('users')]
    
    if 'uq_users_username' not in unique_constraints and 'uq_users_username' not in indexes:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.create_unique_constraint('uq_users_username', ['username'])


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('uq_users_username', type_='unique')
