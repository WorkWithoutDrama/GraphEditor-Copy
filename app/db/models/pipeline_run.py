"""PipelineRun, ChunkRun, ChunkExtraction ORM models (MVP orchestrator + Stage 1)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin


class PipelineRun(Base, IdMixin):
    """Pipeline run: document ingestion, Stage 1 extraction, etc. run_id = id."""

    __tablename__ = "pipeline_runs"

    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    llm_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    # Stage 1
    run_kind: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    stats_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    chunk_runs: Mapped[list["ChunkRun"]] = relationship(
        "ChunkRun",
        back_populates="pipeline_run",
        cascade="all, delete-orphan",
    )
    chunk_extractions: Mapped[list["ChunkExtraction"]] = relationship(
        "ChunkExtraction",
        back_populates="pipeline_run",
        cascade="all, delete-orphan",
        foreign_keys="ChunkExtraction.run_id",
    )
    produced_extractions: Mapped[list["ChunkExtraction"]] = relationship(
        "ChunkExtraction",
        foreign_keys="ChunkExtraction.produced_run_id",
        back_populates="produced_run",
    )
    llm_calls: Mapped[list["LlmCall"]] = relationship(
        "LlmCall",
        back_populates="pipeline_run",
        cascade="all, delete-orphan",
    )
    claims: Mapped[list["Claim"]] = relationship(
        "Claim",
        back_populates="pipeline_run",
        cascade="all, delete-orphan",
    )


class ChunkRun(Base, IdMixin):
    """Per-chunk processing status within a pipeline run (Stage 1: links to cache row)."""

    __tablename__ = "chunk_runs"

    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    chunk_extraction_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("chunk_extractions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cache_status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (UniqueConstraint("run_id", "chunk_id", name="uq_chunk_runs_run_chunk"),)

    pipeline_run: Mapped["PipelineRun"] = relationship("PipelineRun", back_populates="chunk_runs")


class ChunkExtraction(Base, IdMixin):
    """Global extraction cache: one row per (chunk_id, signature_hash). Also stores run_id for legacy."""

    __tablename__ = "chunk_extractions"

    chunk_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    usage_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_error: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    # Stage 1 cache key
    signature_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    chunk_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    produced_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    llm_call_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    extraction_status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        UniqueConstraint("run_id", "chunk_id", "prompt_name", name="uq_chunk_extractions_run_chunk_prompt"),
        UniqueConstraint("chunk_id", "signature_hash", name="uq_chunk_extractions_chunk_signature"),
    )

    pipeline_run: Mapped["PipelineRun"] = relationship(
        "PipelineRun", back_populates="chunk_extractions", foreign_keys=[run_id]
    )
    produced_run: Mapped["PipelineRun | None"] = relationship(
        "PipelineRun", back_populates="produced_extractions", foreign_keys=[produced_run_id]
    )
