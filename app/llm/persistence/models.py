"""LLM run ORM. Uses same Base as app (for Alembic)."""
from __future__ import annotations

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class LLMRun(Base, IdMixin, TimestampMixin):
    """One LLM call: audit, usage, and optional cache."""

    __tablename__ = "llm_runs"

    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    pipeline_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    profile: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # STARTED, SUCCEEDED, FAILED
    idempotency_key: Mapped[str | None] = mapped_column(String(256), nullable=True, unique=True)
    prompt_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    prompt_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    cost_usd: Mapped[float | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    error_details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # For cache replay: stored response text (when idempotency_key used)
    cached_response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cache_expires_at: Mapped[str | None] = mapped_column(String(32), nullable=True)  # ISO datetime or null

    __table_args__ = (
        Index("ix_llm_runs_workspace_created", "workspace_id", "created_at"),
        Index("ix_llm_runs_prompt_sha256", "prompt_sha256"),
    )
