"""add_question_import_metadata

Revision ID: 8d1f3a9c4b20
Revises: 3ac877a47511
Create Date: 2026-06-22 01:05:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8d1f3a9c4b20"
down_revision: Union[str, None] = "3ac877a47511"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _column_names("question_import_jobs")
    if "metadata_json" not in columns:
        with op.batch_alter_table("question_import_jobs", schema=None) as batch_op:
            batch_op.add_column(sa.Column("metadata_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    columns = _column_names("question_import_jobs")
    if "metadata_json" in columns:
        with op.batch_alter_table("question_import_jobs", schema=None) as batch_op:
            batch_op.drop_column("metadata_json")
