"""Chunk repository — bulk create or get by (document_id, chunk_hash)."""
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models.chunk import Chunk


class ChunkPayload:
    def __init__(
        self,
        chunk_hash: str,
        chunk_index: int,
        text: str | None = None,
        text_uri: str | None = None,
        start_char: int | None = None,
        end_char: int | None = None,
        page_start: int | None = None,
        page_end: int | None = None,
        meta_json: str | None = None,
    ):
        self.chunk_hash = chunk_hash
        self.chunk_index = chunk_index
        self.text = text
        self.text_uri = text_uri
        self.start_char = start_char
        self.end_char = end_char
        self.page_start = page_start
        self.page_end = page_end
        self.meta_json = meta_json


class ChunkRepo:
    def bulk_create_or_get(
        self,
        session: Session,
        document_id: str,
        chunks: list[ChunkPayload],
    ) -> dict[str, str]:
        """Insert chunks; on conflict (document_id, chunk_hash) do nothing. Return mapping chunk_hash -> id."""
        if not chunks:
            return {}
        hashes = [c.chunk_hash for c in chunks]
        stmt = sqlite_insert(Chunk).values(
            [
                {
                    "id": str(uuid4()),
                    "document_id": document_id,
                    "chunk_index": c.chunk_index,
                    "chunk_hash": c.chunk_hash,
                    "text": c.text,
                    "text_uri": c.text_uri,
                    "start_char": c.start_char,
                    "end_char": c.end_char,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "meta_json": c.meta_json,
                }
                for c in chunks
            ]
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=["document_id", "chunk_hash"])
        session.execute(stmt)
        session.flush()
        rows = session.execute(
            select(Chunk.id, Chunk.chunk_hash).where(
                Chunk.document_id == document_id,
                Chunk.chunk_hash.in_(hashes),
            )
        ).all()
        return {r.chunk_hash: r.id for r in rows}

    def bulk_upsert_chunks(
        self,
        session: Session,
        document_id: str,
        chunks: list[ChunkPayload],
        *,
        batch_rows: int = 200,
        batch_max_bytes: int = 5 * 1024 * 1024,
    ) -> int:
        """Insert chunks in batches; ON CONFLICT DO NOTHING. Returns count of newly inserted rows."""
        if not chunks:
            return 0
        total_inserted = 0
        batch: list[ChunkPayload] = []
        batch_bytes = 0
        for c in chunks:
            text_len = (len(c.text) if c.text else 0) + (len(c.meta_json) if c.meta_json else 0)
            if batch and (len(batch) >= batch_rows or batch_bytes + text_len > batch_max_bytes):
                n = self._insert_batch(session, document_id, batch)
                total_inserted += n
                batch = []
                batch_bytes = 0
            batch.append(c)
            batch_bytes += text_len
        if batch:
            total_inserted += self._insert_batch(session, document_id, batch)
        return total_inserted

    def _insert_batch(
        self,
        session: Session,
        document_id: str,
        chunks: list[ChunkPayload],
    ) -> int:
        """Insert one batch; return number of rows actually inserted (no conflict)."""
        if not chunks:
            return 0
        hashes = [c.chunk_hash for c in chunks]
        existing = session.execute(
            select(Chunk.chunk_hash).where(
                Chunk.document_id == document_id,
                Chunk.chunk_hash.in_(hashes),
            )
        ).scalars().all()
        existing_set = set(existing)
        to_insert = [c for c in chunks if c.chunk_hash not in existing_set]
        if not to_insert:
            return 0
        stmt = sqlite_insert(Chunk).values(
            [
                {
                    "id": str(uuid4()),
                    "document_id": document_id,
                    "chunk_index": c.chunk_index,
                    "chunk_hash": c.chunk_hash,
                    "text": c.text,
                    "text_uri": c.text_uri,
                    "start_char": c.start_char,
                    "end_char": c.end_char,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "meta_json": c.meta_json,
                }
                for c in to_insert
            ]
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=["document_id", "chunk_hash"])
        session.execute(stmt)
        session.flush()
        return len(to_insert)

    def list_by_document(
        self, session: Session, document_id: str
    ) -> list[tuple[str, str | None, int]]:
        """Return list of (chunk_id, text, chunk_index) for document, ordered by chunk_index."""
        rows = session.execute(
            select(Chunk.id, Chunk.text, Chunk.chunk_index)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
        ).all()
        return [(r.id, r.text, r.chunk_index) for r in rows]
