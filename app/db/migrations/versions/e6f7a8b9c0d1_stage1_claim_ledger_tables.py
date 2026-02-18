"""stage1_claim_ledger_tables

Add Stage 1 claim ledger: extend pipeline_runs/chunk_extractions/chunk_runs,
add llm_calls, claims, claim_evidence.

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-02-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pipeline_runs: Stage 1 run metadata
    with op.batch_alter_table("pipeline_runs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("run_kind", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("config_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("stats_json", sa.Text(), nullable=True))

    # chunk_extractions: global cache keyed by (chunk_id, signature_hash)
    with op.batch_alter_table("chunk_extractions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("signature_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("chunk_content_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("produced_run_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("llm_call_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("extraction_status", sa.String(length=32), nullable=True))
        batch_op.create_foreign_key(
            "fk_chunk_extractions_produced_run_id",
            "pipeline_runs",
            ["produced_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_unique_constraint(
            "uq_chunk_extractions_chunk_signature",
            ["chunk_id", "signature_hash"],
        )
        batch_op.create_index("ix_chunk_extractions_signature_hash", ["signature_hash"], unique=False)

    # chunk_runs: link to cache row + cache status
    with op.batch_alter_table("chunk_runs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("chunk_extraction_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("cache_status", sa.String(length=32), nullable=True))
        batch_op.create_foreign_key(
            "fk_chunk_runs_chunk_extraction_id",
            "chunk_extractions",
            ["chunk_extraction_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # llm_calls: audit trail for every LLM request/response
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=36), nullable=True),
        sa.Column("signature_hash", sa.String(length=64), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("request_json", sa.Text(), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("response_json", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.String(length=4096), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("llm_calls", schema=None) as batch_op:
        batch_op.create_index("ix_llm_calls_run_id", ["run_id"], unique=False)
        batch_op.create_index("ix_llm_calls_chunk_id", ["chunk_id"], unique=False)

    # claims: claim ledger
    op.create_table(
        "claims",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_extraction_id", sa.String(length=36), nullable=True),
        sa.Column("claim_type", sa.String(length=32), nullable=False),
        sa.Column("subject_type", sa.String(length=64), nullable=True),
        sa.Column("subject_text", sa.String(length=512), nullable=True),
        sa.Column("predicate", sa.String(length=256), nullable=True),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("epistemic_tag", sa.String(length=32), nullable=False),
        sa.Column("rule_id", sa.String(length=128), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("review_status", sa.String(length=32), nullable=False, server_default="UNREVIEWED"),
        sa.Column("superseded_by_id", sa.String(length=36), nullable=True),
        sa.Column("embedding_status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("embedding_model_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["chunk_extraction_id"], ["chunk_extractions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["claims.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("claims", schema=None) as batch_op:
        batch_op.create_index("ix_claims_chunk_id", ["chunk_id"], unique=False)
        batch_op.create_index("ix_claims_run_id", ["run_id"], unique=False)
        batch_op.create_index("ix_claims_claim_type", ["claim_type"], unique=False)
        batch_op.create_index("ix_claims_embedding_status", ["embedding_status"], unique=False)

    # claim_evidence: evidence snippets per claim
    op.create_table(
        "claim_evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("claim_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=36), nullable=False),
        sa.Column("snippet_text", sa.Text(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("claim_evidence", schema=None) as batch_op:
        batch_op.create_index("ix_claim_evidence_claim_id", ["claim_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("claim_evidence", schema=None) as batch_op:
        batch_op.drop_index("ix_claim_evidence_claim_id")
    op.drop_table("claim_evidence")

    with op.batch_alter_table("claims", schema=None) as batch_op:
        batch_op.drop_index("ix_claims_embedding_status")
        batch_op.drop_index("ix_claims_claim_type")
        batch_op.drop_index("ix_claims_run_id")
        batch_op.drop_index("ix_claims_chunk_id")
    op.drop_table("claims")

    with op.batch_alter_table("llm_calls", schema=None) as batch_op:
        batch_op.drop_index("ix_llm_calls_chunk_id")
        batch_op.drop_index("ix_llm_calls_run_id")
    op.drop_table("llm_calls")

    with op.batch_alter_table("chunk_runs", schema=None) as batch_op:
        batch_op.drop_constraint("fk_chunk_runs_chunk_extraction_id", type_="foreignkey")
        batch_op.drop_column("cache_status")
        batch_op.drop_column("chunk_extraction_id")

    with op.batch_alter_table("chunk_extractions", schema=None) as batch_op:
        batch_op.drop_index("ix_chunk_extractions_signature_hash")
        batch_op.drop_constraint("uq_chunk_extractions_chunk_signature", type_="unique")
        batch_op.drop_constraint("fk_chunk_extractions_produced_run_id", type_="foreignkey")
        batch_op.drop_column("extraction_status")
        batch_op.drop_column("llm_call_id")
        batch_op.drop_column("produced_run_id")
        batch_op.drop_column("chunk_content_hash")
        batch_op.drop_column("signature_hash")

    with op.batch_alter_table("pipeline_runs", schema=None) as batch_op:
        batch_op.drop_column("stats_json")
        batch_op.drop_column("config_json")
        batch_op.drop_column("run_kind")
