"""Source and SourceVersion DTOs and Create schemas."""
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    title: str | None
    source_type: str
    external_ref: str | None


class SourceCreate(BaseModel):
    workspace_id: str
    title: str | None = None
    source_type: str
    external_ref: str | None = None


class SourceVersionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    source_id: str
    content_sha256: str
    mime_type: str | None
    size_bytes: int | None
    storage_uri: str
    ingested_at: datetime
    ingest_meta: dict[str, Any] | None = Field(default=None, alias="ingest_meta_json")

    @field_validator("ingest_meta", mode="before")
    @classmethod
    def parse_ingest_meta(cls, v: Any) -> dict[str, Any] | None:
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            return json.loads(v) if v.strip() else None
        return None


class SourceVersionCreate(BaseModel):
    source_id: str
    content_sha256: str
    storage_uri: str
    mime_type: str | None = None
    size_bytes: int | None = None
    ingested_at: datetime
    ingest_meta: dict[str, Any] | None = None
