"""Chunk ORM model."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin


class Chunk(Base, IdMixin):
    __tablename__ = "chunks"

    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    text: Mapped[str | None] = mapped_column(String(65536), nullable=True)
    text_uri: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    start_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meta_json: Mapped[str | None] = mapped_column(String(8192), nullable=True)

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_hash", name="uq_chunks_document_hash"),
    )

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
