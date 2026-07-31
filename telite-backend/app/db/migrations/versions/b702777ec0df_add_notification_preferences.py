"""add_notification_preferences

Revision ID: b702777ec0df
Revises: a9508dcd5889
Create Date: 2026-07-31 16:42:13.358422

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b702777ec0df'
down_revision: Union[str, None] = 'a9508dcd5889'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('organization_notification_defaults',
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=False),
    sa.Column('channel_email', sa.Boolean(), nullable=False),
    sa.Column('channel_in_app', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('org_id', 'category')
    )
    
    op.create_table('notification_preferences',
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=False),
    sa.Column('channel_email', sa.Boolean(), nullable=False),
    sa.Column('channel_in_app', sa.Boolean(), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False, comment='Tenant organisation ID — used by RLS policies'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'category')
    )
    with op.batch_alter_table('notification_preferences', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_notification_preferences_org_id'), ['org_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('notification_preferences', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_notification_preferences_org_id'))
    op.drop_table('notification_preferences')
    op.drop_table('organization_notification_defaults')
