"""EmbeddingSet and ChunkEmbedding repositories."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models.embedding import ChunkEmbedding, EmbeddingSet


class EmbeddingSetRepo:
    def create_or_get(
        self,
        session: Session,
        workspace_id: str,
        name: str,
        model: str,
        dims: int,
        distance: str,
        qdrant_collection: str,
    ) -> EmbeddingSet:
        existing = session.execute(
            select(EmbeddingSet).where(
                EmbeddingSet.workspace_id == workspace_id,
                EmbeddingSet.name == name,
            )
        ).scalar_one_or_none()
        if existing:
            return existing
        es = EmbeddingSet(
            workspace_id=workspace_id,
            name=name,
            model=model,
            dims=dims,
            distance=distance,
            qdrant_collection=qdrant_collection,
        )
        session.add(es)
        session.flush()
        return es


class ChunkEmbeddingRepo:
    def upsert_pointers(
        self,
        session: Session,
        embedding_set_id: str,
        items: list[tuple[str, str]],
    ) -> None:
        """Bulk insert (chunk_id, qdrant_point_id); on conflict do nothing."""
        if not items:
            return
        now = datetime.now(timezone.utc)
        stmt = sqlite_insert(ChunkEmbedding).values(
            [
                {
                    "id": str(uuid4()),
                    "chunk_id": chunk_id,
                    "embedding_set_id": embedding_set_id,
                    "qdrant_point_id": qdrant_point_id,
                    "embedded_at": now,
                }
                for chunk_id, qdrant_point_id in items
            ]
        )
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["chunk_id", "embedding_set_id"]
        )
        session.execute(stmt)
        session.flush()
