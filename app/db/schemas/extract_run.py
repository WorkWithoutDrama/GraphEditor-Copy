"""ExtractRun DTOs."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExtractRunDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    source_version_id: str
    extractor: str
    extractor_version: str
    status: str
    attempt: int
    trace_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    chunker_version: str | None = None
