"""DTOs and job envelope for docling module."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --- Job envelope (Appendix A) ---


class JobEnvelope(BaseModel):
    """Required envelope for all jobs."""

    type: str = Field(..., description="e.g. docling.extract, embeddings.embed_document_chunks")
    job_id: str = Field(..., description="UUID")
    attempt: int = Field(default=1)
    created_at: str = Field(..., description="ISO8601")
    trace_id: str = Field(..., description="Distributed trace id")
    idempotency_key: str = Field(..., description="Dedupe key for at-least-once")
    workspace_id: str = Field(...)
    source_version_id: str | None = Field(default=None, description="For docling.extract")


class DoclingExtractPayload(JobEnvelope):
    """Payload for docling.extract job."""

    type: str = Field(default="docling.extract")
    source_version_id: str = Field(...)
    extractor: str = Field(default="docling")
    extractor_version: str = Field(...)
    embedding_set_id: str = Field(..., description="For handoff after chunking")


class EmbedDocumentChunksPayload(JobEnvelope):
    """Payload for embeddings.embed_document_chunks handoff."""

    type: str = Field(default="embeddings.embed_document_chunks")
    embedding_set_id: str = Field(...)
    document_id: str = Field(...)
    chunker_version: str = Field(...)
    chunk_ids: list[str] | None = Field(default=None, description="Optional; else worker derives from DB")


# --- Document/Chunk DTOs used by docling (no SQLAlchemy) ---


class DocumentDTO(BaseModel):
    """Document identity and URIs (from DocumentRepoPort)."""

    id: str
    source_version_id: str
    extractor: str
    extractor_version: str
    language: str | None = None
    structure_json_uri: str
    plain_text_uri: str | None = None
    stats: dict[str, Any] | None = None


class ChunkCreate(BaseModel):
    """Single chunk for bulk_upsert_chunks."""

    chunk_index: int
    chunk_hash: str
    text: str | None = None
    text_uri: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    meta_json: str | None = None


class ExtractRunDTO(BaseModel):
    """Extract run status (from ExtractRunsPort)."""

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


# --- API response ---


class IngestResponse(BaseModel):
    """Response for POST ingest."""

    source_version_id: str
    extractor: str = "docling"
    extractor_version: str
    status: str = "QUEUED"
