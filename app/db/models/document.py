"""Document ORM model (extraction output per source version + extractor)."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin


class Document(Base, IdMixin):
    __tablename__ = "documents"

    source_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("source_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    extractor: Mapped[str] = mapped_column(String(64), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    structure_json_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    plain_text_uri: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    stats_json: Mapped[str | None] = mapped_column(String(8192), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "source_version_id",
            "extractor",
            "extractor_version",
            name="uq_documents_source_version_extractor",
        ),
    )

    source_version: Mapped["SourceVersion"] = relationship(
        "SourceVersion",
        back_populates="documents",
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )
