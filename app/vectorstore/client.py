"""Qdrant async client factory."""
from qdrant_client import AsyncQdrantClient

from app.vectorstore.settings import VectorStoreSettings


def build_qdrant_client(settings: VectorStoreSettings | None = None) -> AsyncQdrantClient:
    """Create AsyncQdrantClient. Use one shared client per process."""
    s = settings or VectorStoreSettings()
    return AsyncQdrantClient(
        url=s.url,
        api_key=s.api_key,
        prefer_grpc=s.prefer_grpc,
        timeout=s.timeout_s,
    )
