"""ExtractRun ORM model (per-workspace/source_version/extractor FSM)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class ExtractRun(Base, IdMixin, TimestampMixin):
    """Operational state for extraction pipeline. Unique on (workspace_id, source_version_id, extractor, extractor_version)."""

    __tablename__ = "extract_runs"

    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("source_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    extractor: Mapped[str] = mapped_column(String(64), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(default=1, nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    chunker_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "source_version_id",
            "extractor",
            "extractor_version",
            name="uq_extract_runs_workspace_source_extractor",
        ),
    )
