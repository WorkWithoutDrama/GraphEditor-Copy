"""Thin service to persist chunks (idempotent by chunk_hash)."""
from sqlalchemy.orm import Session

from app.db.repositories.chunk_repo import ChunkPayload, ChunkRepo


class ChunkPersistService:
    def __init__(self) -> None:
        self._chunk_repo = ChunkRepo()

    def persist_chunks(
        self,
        session: Session,
        document_id: str,
        chunk_payloads: list[ChunkPayload],
    ) -> dict[str, str]:
        """Persist chunks for a document. Returns mapping chunk_hash -> chunk id."""
        return self._chunk_repo.bulk_create_or_get(session, document_id, chunk_payloads)
