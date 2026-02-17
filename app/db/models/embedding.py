"""EmbeddingSet and ChunkEmbedding ORM models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin


def _utc_now() -> datetime:
    from datetime import timezone
    return datetime.now(timezone.utc)


class EmbeddingSet(Base, IdMixin):
    __tablename__ = "embedding_sets"

    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    dims: Mapped[int] = mapped_column(Integer, nullable=False)
    distance: Mapped[str] = mapped_column(String(32), nullable=False)
    qdrant_collection: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        server_default=func.datetime("now"),
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_embedding_sets_workspace_name"),
    )


class ChunkEmbedding(Base, IdMixin):
    __tablename__ = "chunk_embeddings"

    chunk_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    embedding_set_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("embedding_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    qdrant_point_id: Mapped[str] = mapped_column(String(256), nullable=False)
    embedded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "chunk_id",
            "embedding_set_id",
            name="uq_chunk_embeddings_chunk_set",
        ),
    )
