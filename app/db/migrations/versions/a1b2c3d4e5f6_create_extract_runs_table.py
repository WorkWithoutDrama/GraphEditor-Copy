"""create_extract_runs_table

Revision ID: a1b2c3d4e5f6
Revises: 82aaac20c4c7
Create Date: 2026-02-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "82aaac20c4c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "extract_runs",
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("source_version_id", sa.String(length=36), nullable=False),
        sa.Column("extractor", sa.String(length=64), nullable=False),
        sa.Column("extractor_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=4096), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(datetime('now'))"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(datetime('now'))"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_version_id"], ["source_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id", "source_version_id", "extractor", "extractor_version",
            name="uq_extract_runs_workspace_source_extractor",
        ),
    )
    op.create_index("ix_extract_runs_workspace_id", "extract_runs", ["workspace_id"], unique=False)
    op.create_index("ix_extract_runs_source_version_id", "extract_runs", ["source_version_id"], unique=False)
    op.create_index("ix_extract_runs_status", "extract_runs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_extract_runs_status", table_name="extract_runs")
    op.drop_index("ix_extract_runs_source_version_id", table_name="extract_runs")
    op.drop_index("ix_extract_runs_workspace_id", table_name="extract_runs")
    op.drop_table("extract_runs")
