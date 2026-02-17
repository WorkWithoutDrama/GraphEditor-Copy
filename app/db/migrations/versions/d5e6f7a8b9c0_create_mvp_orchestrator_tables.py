"""create_mvp_orchestrator_tables

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-02-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("llm_profile", sa.String(length=64), nullable=True),
        sa.Column("prompt_name", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.String(length=4096), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], name=op.f("fk_pipeline_runs_document_id_documents"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], name=op.f("fk_pipeline_runs_workspace_id_workspaces"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pipeline_runs")),
    )
    with op.batch_alter_table("pipeline_runs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_pipeline_runs_document_id"), ["document_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_pipeline_runs_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_pipeline_runs_workspace_id"), ["workspace_id"], unique=False)

    op.create_table(
        "chunk_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=4096), nullable=True),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["chunks.id"], name=op.f("fk_chunk_runs_chunk_id_chunks"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["pipeline_runs.id"], name=op.f("fk_chunk_runs_run_id_pipeline_runs"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chunk_runs")),
        sa.UniqueConstraint("run_id", "chunk_id", name="uq_chunk_runs_run_chunk"),
    )
    with op.batch_alter_table("chunk_runs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_chunk_runs_chunk_id"), ["chunk_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_chunk_runs_run_id"), ["run_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_chunk_runs_status"), ["status"], unique=False)

    op.create_table(
        "chunk_extractions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("prompt_name", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("parsed_json", sa.Text(), nullable=True),
        sa.Column("usage_json", sa.Text(), nullable=True),
        sa.Column("validation_error", sa.String(length=4096), nullable=True),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["chunks.id"], name=op.f("fk_chunk_extractions_chunk_id_chunks"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["pipeline_runs.id"], name=op.f("fk_chunk_extractions_run_id_pipeline_runs"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chunk_extractions")),
        sa.UniqueConstraint("run_id", "chunk_id", "prompt_name", name="uq_chunk_extractions_run_chunk_prompt"),
    )
    with op.batch_alter_table("chunk_extractions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_chunk_extractions_chunk_id"), ["chunk_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_chunk_extractions_run_id"), ["run_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("chunk_extractions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_chunk_extractions_run_id"))
        batch_op.drop_index(batch_op.f("ix_chunk_extractions_chunk_id"))
    op.drop_table("chunk_extractions")

    with op.batch_alter_table("chunk_runs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_chunk_runs_status"))
        batch_op.drop_index(batch_op.f("ix_chunk_runs_run_id"))
        batch_op.drop_index(batch_op.f("ix_chunk_runs_chunk_id"))
    op.drop_table("chunk_runs")

    with op.batch_alter_table("pipeline_runs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_pipeline_runs_workspace_id"))
        batch_op.drop_index(batch_op.f("ix_pipeline_runs_status"))
        batch_op.drop_index(batch_op.f("ix_pipeline_runs_document_id"))
    op.drop_table("pipeline_runs")
