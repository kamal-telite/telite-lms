"""phase_g_add_org_id_to_password_reset

Revision ID: b2d976c3de97
Revises: e40fc4255652
Create Date: 2026-06-08 18:59:54.721103

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2d976c3de97'
down_revision: Union[str, None] = 'e40fc4255652'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    columns = [c['name'] for c in insp.get_columns('password_reset_tokens')]
    if 'org_id' not in columns:
        op.add_column('password_reset_tokens', sa.Column('org_id', sa.Integer(), nullable=False, server_default='1'))

def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    columns = [c['name'] for c in insp.get_columns('password_reset_tokens')]
    if 'org_id' in columns:
        op.drop_column('password_reset_tokens', 'org_id')
