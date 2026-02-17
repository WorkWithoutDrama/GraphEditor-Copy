"""Query and QueryResult ORM models (optional query logging)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin


class Query(Base, IdMixin):
    __tablename__ = "queries"

    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    query_text: Mapped[str] = mapped_column(String(65536), nullable=False)
    embedding_set_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    filters_json: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meta_json: Mapped[str | None] = mapped_column(String(8192), nullable=True)

    __table_args__ = (
        Index("ix_queries_workspace_id_ts", "workspace_id", "ts"),
    )


class QueryResult(Base, IdMixin):
    __tablename__ = "query_results"

    query_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    rerank_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("query_id", "rank", name="uq_query_results_query_rank"),
    )
