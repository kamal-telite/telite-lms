"""add_question_version_timestamps

Revision ID: 9b2c7f4d1a6e
Revises: 8d1f3a9c4b20
Create Date: 2026-06-22 12:35:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9b2c7f4d1a6e"
down_revision: Union[str, None] = "8d1f3a9c4b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _column_names("question_versions")
    with op.batch_alter_table("question_versions", schema=None) as batch_op:
        if "created_at" not in columns:
            batch_op.add_column(
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.func.now(),
                    nullable=True,
                )
            )
        if "updated_at" not in columns:
            batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    columns = _column_names("question_versions")
    with op.batch_alter_table("question_versions", schema=None) as batch_op:
        if "updated_at" in columns:
            batch_op.drop_column("updated_at")
        if "created_at" in columns:
            batch_op.drop_column("created_at")
