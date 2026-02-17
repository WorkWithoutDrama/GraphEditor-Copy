"""Typed filter abstraction for Qdrant queries."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field
from qdrant_client import models as qdrant_models


class VectorFilter(BaseModel):
    """Typed filter AST for Qdrant. Compiles to Qdrant filter objects."""

    workspace_id: str = Field(..., description="Mandatory workspace isolation")
    document_id: str | None = Field(default=None, description="Optional document scope")
    created_after: datetime | None = Field(default=None, description="Optional time lower bound")
    created_before: datetime | None = Field(default=None, description="Optional time upper bound")
    tags: list[str] | None = Field(default=None, description="Optional tag filter")


def compile_filter(vf: VectorFilter) -> qdrant_models.Filter:
    """Compile VectorFilter to Qdrant Filter."""
    must: list[qdrant_models.FieldCondition] = [
        qdrant_models.FieldCondition(
            key="workspace_id",
            match=qdrant_models.MatchValue(value=vf.workspace_id),
        )
    ]
    if vf.document_id is not None:
        must.append(
            qdrant_models.FieldCondition(
                key="document_id",
                match=qdrant_models.MatchValue(value=vf.document_id),
            )
        )
    if vf.created_after is not None:
        must.append(
            qdrant_models.FieldCondition(
                key="embedded_at",
                range=qdrant_models.DatetimeRange(gte=vf.created_after),
            )
        )
    if vf.created_before is not None:
        must.append(
            qdrant_models.FieldCondition(
                key="embedded_at",
                range=qdrant_models.DatetimeRange(lte=vf.created_before),
            )
        )
    if vf.tags:
        must.append(
            qdrant_models.FieldCondition(
                key="tags",
                match=qdrant_models.MatchAny(any=vf.tags),
            )
        )
    return qdrant_models.Filter(must=must)
