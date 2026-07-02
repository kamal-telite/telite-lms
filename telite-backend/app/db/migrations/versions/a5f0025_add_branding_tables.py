"""add_branding_tables

Revision ID: a5f0025
Revises: a5f002
Create Date: 2026-07-02

This migration creates the enterprise branding engine tables that were
defined in the SQLAlchemy models but missing from the migration chain.
These tables are referenced by subsequent RLS migrations (a5f003, a5f007).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a5f0025"
down_revision: Union[str, None] = "a5f002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create branding_versions table
    if not _table_exists("branding_versions"):
        op.create_table(
            "branding_versions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("org_id", sa.Integer(), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("configuration_json", sa.Text(), nullable=False),
            sa.Column("created_by", sa.String(50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["org_id"], ["organizations.id"], name="fk_branding_versions_org_id_organizations", ondelete="CASCADE"
            ),
            sa.Index("ix_branding_versions_org_id", "org_id"),
        )

    # Create branding_assets table
    if not _table_exists("branding_assets"):
        op.create_table(
            "branding_assets",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("org_id", sa.Integer(), nullable=False),
            sa.Column("asset_type", sa.String(50), nullable=False),
            sa.Column("file_path", sa.Text(), nullable=False),
            sa.Column("uploaded_by", sa.String(50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["org_id"], ["organizations.id"], name="fk_branding_assets_org_id_organizations", ondelete="CASCADE"
            ),
            sa.Index("ix_branding_assets_org_id", "org_id"),
        )

    # Create branding_audit_logs table
    if not _table_exists("branding_audit_logs"):
        op.create_table(
            "branding_audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("org_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(50), nullable=False),
            sa.Column("user_id", sa.String(50), nullable=True),
            sa.Column("changes_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["org_id"], ["organizations.id"], name="fk_branding_audit_logs_org_id_organizations", ondelete="CASCADE"
            ),
            sa.Index("ix_branding_audit_logs_org_id", "org_id"),
        )


def downgrade() -> None:
    op.drop_table("branding_audit_logs")
    op.drop_table("branding_assets")
    op.drop_table("branding_versions")


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    return conn.dialect.has_table(conn, table_name)
