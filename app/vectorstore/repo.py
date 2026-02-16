"""Qdrant vector store repository (async, workspace-enforced)."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from qdrant_client import AsyncQdrantClient, models as qdrant_models

from app.vectorstore.collections import EmbeddingSetSpec, ensure_collection
from app.vectorstore.errors import VectorSchemaMismatchError, VectorStoreError
from app.vectorstore.filters import VectorFilter, compile_filter
from app.vectorstore.models import ChunkPayload, ChunkPoint, ScoredChunk
from app.vectorstore.settings import VectorStoreSettings

logger = logging.getLogger(__name__)


def _payload_to_dict(payload: ChunkPayload) -> dict:
    """Convert ChunkPayload to JSON-serializable dict for Qdrant."""
    d = {
        "workspace_id": payload.workspace_id,
        "document_id": payload.document_id,
        "chunk_id": payload.chunk_id,
        "chunk_index": payload.chunk_index,
        "embedded_at": payload.embedded_at.isoformat(),
    }
    if payload.chunk_hash is not None:
        d["chunk_hash"] = payload.chunk_hash
    return d


async def _retry_transient(
    settings: VectorStoreSettings,
    coro_func,
    *args,
    **kwargs,
):
    """Execute coroutine with retries for transient errors."""
    last_exc = None
    for attempt in range(1, settings.retries + 1):
        try:
            return await coro_func(*args, **kwargs)
        except VectorSchemaMismatchError:
            raise
        except Exception as e:
            last_exc = e
            if attempt < settings.retries:
                delay = settings.retry_backoff_base_s * (2 ** (attempt - 1))
                logger.warning(
                    "Qdrant call failed (attempt %s/%s), retrying in %.2fs: %s",
                    attempt, settings.retries, delay, e,
                )
                await asyncio.sleep(delay)
    raise VectorStoreError(
        f"Qdrant call failed after {settings.retries} attempts"
    ) from last_exc


class QdrantVectorStoreRepo:
    """Async Qdrant repository. All operations require workspace_id."""

    def __init__(
        self,
        client: AsyncQdrantClient,
        settings: VectorStoreSettings | None = None,
    ) -> None:
        self._client = client
        self._settings = settings or VectorStoreSettings()

    async def health(self) -> bool:
        """Check connectivity to Qdrant."""
        try:
            await self._client.get_collections()
            return True
        except Exception:
            return False

    async def ensure_collection(self, embedding_set: EmbeddingSetSpec) -> None:
        """Ensure collection exists with correct schema."""
        await ensure_collection(
            self._client,
            embedding_set,
            self._settings,
        )

    async def upsert_points(
        self,
        embedding_set: EmbeddingSetSpec,
        points: list[ChunkPoint],
    ) -> None:
        """Upsert points in batches. Point id must equal chunk_id."""
        if not points:
            return

        async def _do_upsert() -> None:
            batch_size = self._settings.upsert_batch_size
            collection_name = embedding_set.qdrant_collection
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                qdrant_points = [
                    qdrant_models.PointStruct(
                        id=str(p.id),
                        vector=p.vector,
                        payload=_payload_to_dict(p.payload),
                    )
                    for p in batch
                ]
                await self._client.upsert(
                    collection_name=collection_name,
                    points=qdrant_points,
                )
                logger.info(
                    "Upserted %s points to %s (batch %s)",
                    len(batch), collection_name, i // batch_size + 1,
                )

        await _retry_transient(self._settings, _do_upsert)

    async def search(
        self,
        embedding_set: EmbeddingSetSpec,
        workspace_id: str,
        query_vector: list[float],
        document_id: str | None = None,
        limit: int = 10,
        offset: int | None = None,
    ) -> list[ScoredChunk]:
        """Search by vector similarity. workspace_id is mandatory."""
        vf = VectorFilter(
            workspace_id=workspace_id,
            document_id=document_id,
        )
        return await self._search_impl(
            embedding_set,
            query_vector,
            vf,
            limit,
            offset,
        )

    async def _search_impl(
        self,
        embedding_set: EmbeddingSetSpec,
        query_vector: list[float],
        vf: VectorFilter,
        limit: int,
        offset: int | None,
    ) -> list[ScoredChunk]:
        async def _do_search() -> list[ScoredChunk]:
            qf = compile_filter(vf)
            response = await self._client.query_points(
                collection_name=embedding_set.qdrant_collection,
                query=query_vector,
                query_filter=qf,
                limit=limit,
                offset=offset or 0,
            )
            return [
                ScoredChunk(
                    chunk_id=UUID(r.id) if isinstance(r.id, str) else UUID(int=r.id),
                    score=float(r.score or 0),
                    payload=dict(r.payload or {}),
                )
                for r in (response.points or [])
            ]

        return await _retry_transient(self._settings, _do_search)

    async def delete_by_document(
        self,
        embedding_set: EmbeddingSetSpec,
        workspace_id: str,
        document_id: str,
    ) -> int:
        """Delete all points for a document. Returns deleted count."""
        vf = VectorFilter(workspace_id=workspace_id, document_id=document_id)
        return await self.delete_by_filter(embedding_set, vf)

    async def delete_by_workspace(
        self,
        embedding_set: EmbeddingSetSpec,
        workspace_id: str,
    ) -> int:
        """Delete all points for a workspace. Returns deleted count."""
        vf = VectorFilter(workspace_id=workspace_id)
        return await self.delete_by_filter(embedding_set, vf)

    async def delete_by_filter(
        self,
        embedding_set: EmbeddingSetSpec,
        vf: VectorFilter,
    ) -> int:
        """Delete points matching filter. Returns deleted count."""

        async def _do_delete() -> int:
            qf = compile_filter(vf)
            await self._client.delete(
                collection_name=embedding_set.qdrant_collection,
                points_selector=qdrant_models.FilterSelector(filter=qf),
            )
            return 0

        return await _retry_transient(self._settings, _do_delete)

    async def count(
        self,
        embedding_set: EmbeddingSetSpec,
        workspace_id: str,
        document_id: str | None = None,
    ) -> int:
        """Count points in collection (optionally filtered by document)."""

        async def _do_count() -> int:
            vf = VectorFilter(workspace_id=workspace_id, document_id=document_id)
            qf = compile_filter(vf)
            result = await self._client.count(
                collection_name=embedding_set.qdrant_collection,
                count_filter=qf,
            )
            return result.count

        return await _retry_transient(self._settings, _do_count)

    def scroll_ids(
        self,
        embedding_set: EmbeddingSetSpec,
        vf: VectorFilter,
        batch_size: int = 100,
    ) -> AsyncIterator[list[UUID]]:
        """Scroll point IDs in batches. Use for reindex."""
        return _scroll_ids_impl(
            self._client,
            embedding_set.qdrant_collection,
            compile_filter(vf),
            batch_size,
        )

    def scroll_collection_ids(
        self,
        collection_name: str,
        vf: VectorFilter,
        batch_size: int = 100,
    ) -> AsyncIterator[list[UUID]]:
        """Scroll point IDs from any collection by name. Use for reindex from old collection."""
        return _scroll_ids_impl(
            self._client,
            collection_name,
            compile_filter(vf),
            batch_size,
        )


async def _scroll_ids_impl(
    client: AsyncQdrantClient,
    collection_name: str,
    qf: qdrant_models.Filter,
    batch_size: int,
) -> AsyncIterator[list[UUID]]:
    offset = None
    while True:
        records, offset = await client.scroll(
            collection_name=collection_name,
            scroll_filter=qf,
            limit=batch_size,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )
        if not records:
            break
        ids = [UUID(r.id) if isinstance(r.id, str) else UUID(int=r.id) for r in records]
        yield ids
        if offset is None:
            break
