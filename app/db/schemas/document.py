"""Document DTOs and Create schema."""
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    source_version_id: str
    extractor: str
    extractor_version: str
    language: str | None
    structure_json_uri: str
    plain_text_uri: str | None
    stats: dict[str, Any] | None = Field(default=None, alias="stats_json")

    @field_validator("stats", mode="before")
    @classmethod
    def parse_stats(cls, v: Any) -> dict[str, Any] | None:
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            return json.loads(v) if v.strip() else None
        return None


class DocumentCreate(BaseModel):
    source_version_id: str
    extractor: str
    extractor_version: str
    structure_json_uri: str
    language: str | None = None
    plain_text_uri: str | None = None
    stats: dict[str, Any] | None = None
