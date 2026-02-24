"""claims_qdrant_columns

Add Qdrant indexing bookkeeping to claims: qdrant_collection, qdrant_point_id,
card_text, dedupe_key, embedding_error.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-02-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("claims", schema=None) as batch_op:
        batch_op.add_column(sa.Column("qdrant_collection", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("qdrant_point_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("card_text", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("dedupe_key", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("embedding_error", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("claims", schema=None) as batch_op:
        batch_op.drop_column("embedding_error")
        batch_op.drop_column("dedupe_key")
        batch_op.drop_column("card_text")
        batch_op.drop_column("qdrant_point_id")
        batch_op.drop_column("qdrant_collection")
