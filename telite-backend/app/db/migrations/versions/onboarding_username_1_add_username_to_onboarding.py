"""Add username to onboarding

Revision ID: onboarding_username_1
Revises: 
Create Date: 2026-06-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'onboarding_username_1'
down_revision = '0e000a2a9613'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('org_invitations', sa.Column('username', sa.String(), nullable=True))
    op.add_column('pending_verifications', sa.Column('username', sa.String(), nullable=True))
    with op.batch_alter_table('pending_verifications', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_pending_verifications_username', ['username'])


def downgrade() -> None:
    with op.batch_alter_table('pending_verifications', schema=None) as batch_op:
        batch_op.drop_constraint('uq_pending_verifications_username', type_='unique')
    op.drop_column('pending_verifications', 'username')
    op.drop_column('org_invitations', 'username')
