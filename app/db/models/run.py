"""Run, RunItem, Event ORM models (pipeline observability)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class Run(Base, IdMixin):
    __tablename__ = "runs"

    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta_json: Mapped[str | None] = mapped_column(String(8192), nullable=True)

    __table_args__ = (
        Index("ix_runs_workspace_id_started_at", "workspace_id", "started_at"),
    )


class RunItem(Base, IdMixin, TimestampMixin):
    __tablename__ = "run_items"

    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    metrics_json: Mapped[str | None] = mapped_column(String(8192), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "stage",
            "target_type",
            "target_id",
            name="uq_run_items_run_stage_target",
        ),
        Index("ix_run_items_run_stage_status", "run_id", "stage", "status"),
    )


class Event(Base, IdMixin):
    __tablename__ = "events"

    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload_json: Mapped[str | None] = mapped_column(String(8192), nullable=True)

    __table_args__ = (
        Index("ix_events_run_id_ts", "run_id", "ts"),
    )
