"""phase_e_scorm_certs_analytics

Revision ID: db5ba62f5025
Revises: 2b803db5bf76
Create Date: 2026-06-08 02:28:07.292764

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'db5ba62f5025'
down_revision: Union[str, None] = '2b803db5bf76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to organization_branding
    with op.batch_alter_table('organization_branding', schema=None) as batch_op:
        batch_op.add_column(sa.Column('certificate_primary_color', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('certificate_signature_url', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('certificate_qr_layout', sa.String(length=20), nullable=True, comment='bottom_left, bottom_right, hidden'))

    # Create certificates table
    op.create_table('certificates',
    sa.Column('id', sa.String(length=50), nullable=False, comment='Public unique ID for verification'),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('course_id', sa.String(length=50), nullable=False),
    sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('pdf_s3_key', sa.String(length=255), nullable=False),
    sa.Column('certificate_hash', sa.String(length=255), nullable=False),
    sa.Column('verification_token', sa.String(length=255), nullable=False),
    sa.Column('qr_code_url', sa.Text(), nullable=True),
    sa.Column('issued_version', sa.Integer(), nullable=False),
    sa.Column('metadata_json', sa.JSON(), nullable=True),
    sa.Column('org_id', sa.Integer(), nullable=False, comment='Tenant organisation ID — used by RLS policies'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], name='fk_certificates_course_id', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], name='fk_certificates_org_id', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_certificates_user_id', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('certificate_hash', name='uq_certificates_certificate_hash'),
    sa.UniqueConstraint('verification_token', name='uq_certificates_verification_token')
    )
    with op.batch_alter_table('certificates', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_certificates_course_id'), ['course_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_certificates_org_id'), ['org_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_certificates_user_id'), ['user_id'], unique=False)

    # Create interactive_tracking table
    op.create_table('interactive_tracking',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('attempt_id', sa.Integer(), nullable=False),
    sa.Column('protocol', sa.String(length=20), nullable=False, comment='scorm_12, scorm_2004, xapi'),
    sa.Column('element', sa.String(length=255), nullable=False, comment='e.g. cmi.suspend_data'),
    sa.Column('value', sa.Text(), nullable=True),
    sa.Column('org_id', sa.Integer(), nullable=False, comment='Tenant organisation ID — used by RLS policies'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['attempt_id'], ['module_progress.id'], name='fk_interactive_tracking_attempt_id', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], name='fk_interactive_tracking_org_id', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('interactive_tracking', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_interactive_tracking_attempt_id'), ['attempt_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_interactive_tracking_element'), ['element'], unique=False)
        batch_op.create_index(batch_op.f('ix_interactive_tracking_org_id'), ['org_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('interactive_tracking', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_interactive_tracking_org_id'))
        batch_op.drop_index(batch_op.f('ix_interactive_tracking_element'))
        batch_op.drop_index(batch_op.f('ix_interactive_tracking_attempt_id'))

    op.drop_table('interactive_tracking')

    with op.batch_alter_table('certificates', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_certificates_user_id'))
        batch_op.drop_index(batch_op.f('ix_certificates_org_id'))
        batch_op.drop_index(batch_op.f('ix_certificates_course_id'))

    op.drop_table('certificates')

    with op.batch_alter_table('organization_branding', schema=None) as batch_op:
        batch_op.drop_column('certificate_qr_layout')
        batch_op.drop_column('certificate_signature_url')
        batch_op.drop_column('certificate_primary_color')
