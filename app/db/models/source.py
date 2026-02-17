"""Source and SourceVersion ORM models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin


class Source(Base, IdMixin, TimestampMixin):
    __tablename__ = "sources"

    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="sources")
    versions: Mapped[list["SourceVersion"]] = relationship(
        "SourceVersion",
        back_populates="source",
        cascade="all, delete-orphan",
    )


class SourceVersion(Base, IdMixin):
    __tablename__ = "source_versions"

    source_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingest_meta_json: Mapped[str | None] = mapped_column(String(4096), nullable=True)

    source: Mapped["Source"] = relationship("Source", back_populates="versions")
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="source_version",
        cascade="all, delete-orphan",
    )
