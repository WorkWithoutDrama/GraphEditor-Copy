"""Integration tests for Qdrant vector store repo. Require Docker Qdrant on localhost:6333."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

# Skip all integration tests if Qdrant is not available
try:
    from qdrant_client import AsyncQdrantClient
    _client = AsyncQdrantClient(url="http://localhost:6333", timeout=2.0)
    import asyncio
    _ok = asyncio.run(_client.get_collections())
    del _client, _ok
    QDRANT_AVAILABLE = True
except Exception:
    QDRANT_AVAILABLE = False

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not QDRANT_AVAILABLE, reason="Qdrant not available at localhost:6333"),
]

from app.vectorstore import (
    ChunkPayload,
    ChunkPoint,
    ScoredChunk,
    VectorFilter,
    build_qdrant_client,
    compute_collection_name,
    get_vectorstore_repo,
)
from app.vectorstore.collections import ensure_collection
from app.vectorstore.settings import VectorStoreSettings


@pytest.fixture
def qdrant_settings() -> VectorStoreSettings:
    return VectorStoreSettings(
        url="http://localhost:6333",
        upsert_batch_size=16,
    )


@pytest.fixture
def repo(qdrant_settings: VectorStoreSettings) -> "QdrantVectorStoreRepo":
    from app.vectorstore import QdrantVectorStoreRepo
    client = build_qdrant_client(qdrant_settings)
    return QdrantVectorStoreRepo(client, qdrant_settings)


class _EmbeddingSetSpec:
    def __init__(self, id: str, workspace_id: str, qdrant_collection: str, dims: int, distance: str):
        self.id = id
        self.workspace_id = workspace_id
        self.qdrant_collection = qdrant_collection
        self.dims = dims
        self.distance = distance


@pytest.mark.asyncio
async def test_health(repo: "QdrantVectorStoreRepo") -> None:
    ok = await repo.health()
    assert ok is True


@pytest.mark.asyncio
async def test_ensure_collection_creates_and_upsert_search(repo: "QdrantVectorStoreRepo") -> None:
    ws_id = "test-ws"
    es_id = str(uuid4())
    coll_name = compute_collection_name(ws_id, es_id, 1)
    spec = _EmbeddingSetSpec(es_id, ws_id, coll_name, dims=8, distance="Cosine")

    await repo.ensure_collection(spec)

    now = datetime.now(timezone.utc)
    points = [
        ChunkPoint(
            id=uuid4(),
            vector=[0.1] * 8,
            payload=ChunkPayload(
                workspace_id=ws_id,
                document_id="doc-1",
                chunk_id=str(uuid4()),
                chunk_index=i,
                embedded_at=now,
            ),
        )
        for i in range(3)
    ]
    for p in points:
        p.payload.chunk_id = str(p.id)

    await repo.upsert_points(spec, points)

    results = await repo.search(spec, workspace_id=ws_id, query_vector=[0.1] * 8, limit=5)
    assert len(results) == 3
    assert all(isinstance(r, ScoredChunk) for r in results)


@pytest.mark.asyncio
async def test_delete_by_document(repo: "QdrantVectorStoreRepo") -> None:
    ws_id = "test-ws-del"
    es_id = str(uuid4())
    coll_name = compute_collection_name(ws_id, es_id, 1)
    spec = _EmbeddingSetSpec(es_id, ws_id, coll_name, dims=8, distance="Cosine")

    await repo.ensure_collection(spec)
    doc_id = "doc-to-delete"
    pt_id = uuid4()
    now = datetime.now(timezone.utc)
    points = [
        ChunkPoint(
            id=pt_id,
            vector=[0.2] * 8,
            payload=ChunkPayload(
                workspace_id=ws_id,
                document_id=doc_id,
                chunk_id=str(pt_id),
                chunk_index=0,
                embedded_at=now,
            ),
        )
    ]
    await repo.upsert_points(spec, points)

    await repo.delete_by_document(spec, ws_id, doc_id)

    results = await repo.search(spec, workspace_id=ws_id, query_vector=[0.2] * 8, limit=5)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_workspace_isolation(repo: "QdrantVectorStoreRepo") -> None:
    """Search returns only points from the requested workspace."""
    ws_a = "ws-a"
    ws_b = "ws-b"
    es_id = str(uuid4())
    coll_name = compute_collection_name(ws_a, es_id, 1)
    spec = _EmbeddingSetSpec(es_id, ws_a, coll_name, dims=8, distance="Cosine")

    await repo.ensure_collection(spec)
    now = datetime.now(timezone.utc)
    pt_a = uuid4()
    pt_b = uuid4()
    await repo.upsert_points(
        spec,
        [
            ChunkPoint(
                id=pt_a,
                vector=[0.3] * 8,
                payload=ChunkPayload(
                    workspace_id=ws_a,
                    document_id="d1",
                    chunk_id=str(pt_a),
                    chunk_index=0,
                    embedded_at=now,
                ),
            ),
            ChunkPoint(
                id=pt_b,
                vector=[0.3] * 8,
                payload=ChunkPayload(
                    workspace_id=ws_b,
                    document_id="d2",
                    chunk_id=str(pt_b),
                    chunk_index=0,
                    embedded_at=now,
                ),
            ),
        ],
    )

    results_a = await repo.search(spec, workspace_id=ws_a, query_vector=[0.3] * 8, limit=5)
    results_b = await repo.search(spec, workspace_id=ws_b, query_vector=[0.3] * 8, limit=5)

    assert len(results_a) == 1
    assert len(results_b) == 1
    assert results_a[0].payload.get("workspace_id") == ws_a
    assert results_b[0].payload.get("workspace_id") == ws_b
