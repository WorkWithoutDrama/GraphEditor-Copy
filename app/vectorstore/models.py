"""Typed models for Qdrant points and payloads."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChunkPayload(BaseModel):
    """Minimal payload stored with each vector point."""

    workspace_id: str = Field(..., description="Workspace isolation boundary")
    document_id: str = Field(..., description="Parent document")
    chunk_id: str = Field(..., description="Chunk UUID (redundant with point_id)")
    chunk_index: int = Field(..., description="Chunk index in document")
    embedded_at: datetime = Field(..., description="When embedding was computed")
    chunk_hash: str | None = Field(default=None, description="Chunk hash for dedupe/debug")


class ChunkPoint(BaseModel):
    """A point to upsert: id, vector, payload."""

    id: UUID = Field(..., description="Point ID (equals chunk_id)")
    vector: list[float] = Field(..., description="Embedding vector")
    payload: ChunkPayload = Field(..., description="Payload for filtering")


class ScoredChunk(BaseModel):
    """Search result: chunk_id, score, payload subset."""

    chunk_id: UUID = Field(..., description="Chunk UUID")
    score: float = Field(..., description="Similarity score")
    payload: dict = Field(default_factory=dict, description="Whitelisted payload subset")
