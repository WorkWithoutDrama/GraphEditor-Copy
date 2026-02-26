"""create_llm_runs_table

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-02-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(datetime('now'))"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(datetime('now'))"), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("pipeline_run_id", sa.String(length=36), nullable=True),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("profile", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=True),
        sa.Column("prompt_sha256", sa.String(length=64), nullable=False),
        sa.Column("prompt_preview", sa.Text(), nullable=True),
        sa.Column("response_sha256", sa.String(length=64), nullable=True),
        sa.Column("response_preview", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=4096), nullable=True),
        sa.Column("error_details_json", sa.Text(), nullable=True),
        sa.Column("cached_response_text", sa.Text(), nullable=True),
        sa.Column("cache_expires_at", sa.String(length=32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_runs_workspace_id", "llm_runs", ["workspace_id"], unique=False)
    op.create_index("ix_llm_runs_pipeline_run_id", "llm_runs", ["pipeline_run_id"], unique=False)
    op.create_index("ix_llm_runs_status", "llm_runs", ["status"], unique=False)
    op.create_index("ix_llm_runs_prompt_sha256", "llm_runs", ["prompt_sha256"], unique=False)
    op.create_index("ix_llm_runs_workspace_created", "llm_runs", ["workspace_id", "created_at"], unique=False)
    op.create_index("uq_llm_runs_idempotency_key", "llm_runs", ["idempotency_key"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_llm_runs_idempotency_key", table_name="llm_runs")
    op.drop_index("ix_llm_runs_workspace_created", table_name="llm_runs")
    op.drop_index("ix_llm_runs_prompt_sha256", table_name="llm_runs")
    op.drop_index("ix_llm_runs_status", table_name="llm_runs")
    op.drop_index("ix_llm_runs_pipeline_run_id", table_name="llm_runs")
    op.drop_index("ix_llm_runs_workspace_id", table_name="llm_runs")
    op.drop_table("llm_runs")
