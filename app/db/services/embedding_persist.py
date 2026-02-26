"""Thin service to persist Qdrant embedding pointers (idempotent by chunk_id, embedding_set_id)."""
from sqlalchemy.orm import Session

from app.db.repositories.embedding_repo import ChunkEmbeddingRepo


class EmbeddingPersistService:
    def __init__(self) -> None:
        self._ce_repo = ChunkEmbeddingRepo()

    def persist_qdrant_refs(
        self,
        session: Session,
        embedding_set_id: str,
        mapping: dict[str, str],
    ) -> None:
        """Persist chunk_id -> qdrant_point_id for the given embedding set."""
        items = [(chunk_id, qdrant_point_id) for chunk_id, qdrant_point_id in mapping.items()]
        self._ce_repo.upsert_pointers(session, embedding_set_id, items)
