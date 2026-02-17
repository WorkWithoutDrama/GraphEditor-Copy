"""Reindex utilities for Qdrant collection migrations."""
from __future__ import annotations

import logging
from typing import Callable, Awaitable
from uuid import UUID

from app.vectorstore.collections import EmbeddingSetSpec
from app.vectorstore.filters import VectorFilter
from app.vectorstore.models import ChunkPayload, ChunkPoint
from app.vectorstore.repo import QdrantVectorStoreRepo

logger = logging.getLogger(__name__)


async def reindex_collection(
    repo: QdrantVectorStoreRepo,
    old_collection_name: str,
    new_embedding_set: EmbeddingSetSpec,
    workspace_id: str,
    embed_fn: Callable[[list[str]], Awaitable[list[list[float]]]],
    fetch_chunk_fn: Callable[[list[UUID]], Awaitable[list[tuple[UUID, str, ChunkPayload]]]],
    batch_size: int = 100,
) -> int:
    """Reindex from old collection to new. Scrolls old collection for point IDs (chunk_ids),
    fetches chunk texts via fetch_chunk_fn, computes embeddings, upserts to new collection.

    Returns total points reindexed.
    """
    vf = VectorFilter(workspace_id=workspace_id)
    total = 0
    async for ids_batch in repo.scroll_collection_ids(old_collection_name, vf, batch_size):
        if not ids_batch:
            continue
        chunks_data = await fetch_chunk_fn(ids_batch)
        texts = [t[1] for t in chunks_data]
        vectors = await embed_fn(texts)
        if len(vectors) != len(chunks_data):
            logger.warning("embed_fn returned %s vectors for %s chunks", len(vectors), len(chunks_data))
            continue
        points = [
            ChunkPoint(id=c[0], vector=vec, payload=c[2])
            for (c, vec) in zip(chunks_data, vectors)
        ]
        await repo.ensure_collection(new_embedding_set)
        await repo.upsert_points(new_embedding_set, points)
        total += len(points)
        logger.info("Reindexed batch of %s points", len(points))

    return total
