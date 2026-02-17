"""Minimal Protocols the orchestrator depends on (not concrete implementations)."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EmbeddingClientPort(Protocol):
    """Embed texts and return vectors."""

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


@runtime_checkable
class VectorStorePort(Protocol):
    """Upsert points to vector store."""

    async def upsert_points(
        self,
        embedding_set: Any,
        points: list[Any],
    ) -> None:
        ...

    async def ensure_collection(self, embedding_set: Any) -> None:
        ...
