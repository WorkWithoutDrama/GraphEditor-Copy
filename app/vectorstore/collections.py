"""Collection creation, validation, and naming."""
from __future__ import annotations

from typing import Protocol

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qdrant_http

from app.vectorstore.errors import VectorSchemaMismatchError
from app.vectorstore.settings import VectorStoreSettings


class EmbeddingSetSpec(Protocol):
    """Protocol for embedding set data (from SQL EmbeddingSet or similar)."""

    id: str
    workspace_id: str
    qdrant_collection: str
    dims: int
    distance: str


def compute_collection_name(
    workspace_id: str,
    embedding_set_id: str,
    schema_version: int,
) -> str:
    """Compute deterministic collection name when qdrant_collection is empty.

    Pattern: ws_{workspace_id}__emb_{embedding_set_id}__v{schema_version}
    """
    return f"ws_{workspace_id}__emb_{embedding_set_id}__v{schema_version}"


def _qdrant_distance(s: str) -> qdrant_http.Distance:
    """Map string distance to Qdrant enum."""
    m = {
        "Cosine": qdrant_http.Distance.COSINE,
        "cosine": qdrant_http.Distance.COSINE,
        "Dot": qdrant_http.Distance.DOT,
        "dot": qdrant_http.Distance.DOT,
        "Euclid": qdrant_http.Distance.EUCLID,
        "euclid": qdrant_http.Distance.EUCLID,
    }
    return m.get(s, qdrant_http.Distance.COSINE)


async def ensure_collection(
    client: AsyncQdrantClient,
    embedding_set: EmbeddingSetSpec,
    settings: VectorStoreSettings | None = None,
) -> None:
    """Ensure collection exists with correct schema. Create if missing. Validate if exists.

    Raises VectorSchemaMismatchError if existing collection has wrong vector_size or distance.
    """
    s = settings or VectorStoreSettings()
    collection_name = embedding_set.qdrant_collection
    vector_size = embedding_set.dims
    distance = _qdrant_distance(embedding_set.distance)

    try:
        info = await client.get_collection(collection_name)
    except Exception:
        # Collection does not exist
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=qdrant_http.VectorParams(size=vector_size, distance=distance),
            hnsw_config=qdrant_http.HnswConfigDiff(
                m=16,
                ef_construct=128,
            ),
        )
        # Create payload indexes
        await _ensure_payload_indexes(client, collection_name)
        return

    # Validate existing collection
    vectors_config = info.config.params.vectors
    if isinstance(vectors_config, qdrant_http.VectorParams):
        if vectors_config.size != vector_size or vectors_config.distance != distance:
            raise VectorSchemaMismatchError(
                f"Collection {collection_name} has size={vectors_config.size} distance={vectors_config.distance}, "
                f"expected size={vector_size} distance={distance}. Migration (new collection + reindex) required."
            )
    await _ensure_payload_indexes(client, collection_name)


async def _ensure_payload_indexes(client: AsyncQdrantClient, collection_name: str) -> None:
    """Create payload indexes if they don't exist."""
    indexes = [
        ("workspace_id", qdrant_http.PayloadSchemaType.KEYWORD),
        ("document_id", qdrant_http.PayloadSchemaType.KEYWORD),
        ("chunk_index", qdrant_http.PayloadSchemaType.INTEGER),
        ("embedded_at", qdrant_http.PayloadSchemaType.DATETIME),
    ]
    for field, schema_type in indexes:
        try:
            await client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=qdrant_http.PayloadSchemaType(schema_type),
            )
        except Exception:
            # Index may already exist
            pass
