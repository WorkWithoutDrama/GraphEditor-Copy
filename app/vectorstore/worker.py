"""Embed-and-index worker: compute embeddings and upsert to Qdrant."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Awaitable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import json

from app.db.models.chunk import Chunk
from app.db.models.document import Document
from app.db.models.embedding import EmbeddingSet
from app.db.models.run import Run, RunItem
from app.db.models.source import Source, SourceVersion
from app.db.session import session_scope
from app.vectorstore.models import ChunkPayload as VSChunkPayload, ChunkPoint
from app.vectorstore.repo import QdrantVectorStoreRepo
from app.vectorstore.stages import EMBED_AND_INDEX

logger = logging.getLogger(__name__)


def _fetch_chunks_with_workspace(
    session: Session,
    chunk_ids: list[str],
) -> list[dict]:
    """Fetch chunk id, text, document_id, workspace_id, chunk_index, chunk_hash."""
    rows = (
        session.execute(
            select(
                Chunk.id,
                Chunk.text,
                Chunk.document_id,
                Chunk.chunk_index,
                Chunk.chunk_hash,
                Source.workspace_id,
            )
            .join(Document, Chunk.document_id == Document.id)
            .join(SourceVersion, Document.source_version_id == SourceVersion.id)
            .join(Source, SourceVersion.source_id == Source.id)
            .where(Chunk.id.in_(chunk_ids))
        )
    ).all()
    return [
        {
            "chunk_id": r.id,
            "text": r.text or "",
            "document_id": r.document_id,
            "chunk_index": r.chunk_index,
            "chunk_hash": r.chunk_hash,
            "workspace_id": r.workspace_id,
        }
        for r in rows
    ]


def _fetch_pending_run_items(
    session: Session,
    stage: str = EMBED_AND_INDEX,
    limit: int = 50,
) -> list[RunItem]:
    """Fetch run_items with status=PENDING for the given stage."""
    rows = (
        session.execute(
            select(RunItem)
            .where(RunItem.stage == stage, RunItem.status == "PENDING")
            .limit(limit)
        )
    ).scalars().all()
    return list(rows)


async def embed_and_index_worker_tick(
    repo: QdrantVectorStoreRepo,
    embed_fn: Callable[[list[str]], Awaitable[list[list[float]]]],
    embedding_set_id: str | None = None,
    batch_size: int = 32,
) -> int:
    """Process one batch of pending EMBED_AND_INDEX run_items.

    Fetches chunks from SQL, computes embeddings via embed_fn, upserts to Qdrant,
    writes ChunkEmbedding pointers, marks run_items done.

    Returns number of items processed.
    """
    processed = 0

    def _db_phase() -> tuple[list[RunItem], EmbeddingSet | None, list[dict], str | None]:
        with session_scope() as session:
            items = _fetch_pending_run_items(session, EMBED_AND_INDEX, batch_size)
            if not items:
                return [], None, [], None

            es_id = embedding_set_id
            if not es_id and items:
                run = session.get(Run, items[0].run_id)
                if run and run.meta_json:
                    meta = json.loads(run.meta_json)
                    es_id = meta.get("embedding_set_id")
            if not es_id:
                logger.error("embedding_set_id not provided and not in run meta")
                return items, None, [], None

            chunk_ids = [i.target_id for i in items if i.target_type == "chunk"]
            if not chunk_ids:
                return items, None, [], es_id

            es = session.get(EmbeddingSet, es_id)
            if not es:
                logger.error("EmbeddingSet %s not found", es_id)
                return items, None, [], es_id

            chunks = _fetch_chunks_with_workspace(session, chunk_ids)
            return items, es, chunks, es_id

    items, embedding_set, chunks, es_id = await asyncio.to_thread(_db_phase)
    if not items or not embedding_set or not chunks:
        return processed

    texts = [c["text"] for c in chunks]
    vectors = await embed_fn(texts)
    if len(vectors) != len(chunks):
        logger.error("embed_fn returned %s vectors for %s chunks", len(vectors), len(chunks))
        return 0

    now = datetime.now(timezone.utc)
    points = [
        ChunkPoint(
            id=UUID(c["chunk_id"]),
            vector=vec,
            payload=VSChunkPayload(
                workspace_id=c["workspace_id"],
                document_id=c["document_id"],
                chunk_id=c["chunk_id"],
                chunk_index=c["chunk_index"],
                embedded_at=now,
                chunk_hash=c["chunk_hash"],
            ),
        )
        for c, vec in zip(chunks, vectors)
    ]

    await repo.ensure_collection(embedding_set)
    await repo.upsert_points(embedding_set, points)

    def _write_pointers_and_mark_done() -> None:
        with session_scope() as session:
            pointer_items = [(c["chunk_id"], c["chunk_id"]) for c in chunks]
            from app.db.repositories.embedding_repo import ChunkEmbeddingRepo
            from app.db.repositories.run_repo import RunItemRepo
            ce_repo = ChunkEmbeddingRepo()
            item_repo = RunItemRepo()
            ce_repo.upsert_pointers(session, es_id, pointer_items)
            for item in items:
                item_repo.upsert_item(
                    session,
                    item.run_id,
                    item.stage,
                    item.target_type,
                    item.target_id,
                    status="DONE",
                    metrics={"indexed": len(chunks)},
                )

    await asyncio.to_thread(_write_pointers_and_mark_done)
    return len(items)
