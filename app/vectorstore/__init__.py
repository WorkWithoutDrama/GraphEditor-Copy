"""Vector store (Qdrant) module — async-first, workspace-enforced."""

from app.vectorstore.client import build_qdrant_client
from app.vectorstore.collections import EmbeddingSetSpec, compute_collection_name, ensure_collection
from app.vectorstore.errors import VectorSchemaMismatchError, VectorStoreError, VectorStoreConnectionError
from app.vectorstore.filters import VectorFilter, compile_filter
from app.vectorstore.models import ChunkPayload, ChunkPoint, ScoredChunk
from app.vectorstore.repo import QdrantVectorStoreRepo
from app.vectorstore.settings import VectorStoreSettings
from app.vectorstore.stages import EMBED, EMBED_AND_INDEX, VECTOR_INDEX

__all__ = [
    "build_qdrant_client",
    "EmbeddingSetSpec",
    "compute_collection_name",
    "ensure_collection",
    "VectorSchemaMismatchError",
    "VectorStoreError",
    "VectorStoreConnectionError",
    "VectorFilter",
    "compile_filter",
    "ChunkPayload",
    "ChunkPoint",
    "ScoredChunk",
    "QdrantVectorStoreRepo",
    "VectorStoreSettings",
    "get_vectorstore_repo",
    "EMBED",
    "EMBED_AND_INDEX",
    "VECTOR_INDEX",
]


_repo: QdrantVectorStoreRepo | None = None


def get_vectorstore_repo(
    settings: VectorStoreSettings | None = None,
) -> QdrantVectorStoreRepo:
    """Get or create the shared QdrantVectorStoreRepo (one per process)."""
    global _repo
    if _repo is None:
        s = settings or VectorStoreSettings()
        client = build_qdrant_client(s)
        _repo = QdrantVectorStoreRepo(client, s)
    return _repo
