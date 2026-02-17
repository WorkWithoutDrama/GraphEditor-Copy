"""DTOs and schemas used by orchestrator (not DB ORM models)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChunkExtractionV1(BaseModel):
    """Structured extraction output from LLM per chunk. Used for response_format JSON."""

    summary: str = Field(default="", description="Brief summary of the chunk")
    key_points: list[str] = Field(default_factory=list, description="Key points or takeaways")
    entities: list[str] = Field(default_factory=list, description="Notable entities (people, orgs, concepts)")
