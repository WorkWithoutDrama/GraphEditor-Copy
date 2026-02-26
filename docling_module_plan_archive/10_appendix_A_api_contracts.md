# 10 — Appendix A: API & Internal Contracts

## A1. Job envelope (required for all jobs)

Even with an abstract transport (Redis/SQS/Rabbit/in-memory), every job payload must include a **required envelope**:

**Required fields:**
- `type` (e.g. `docling.extract`, `embeddings.embed_document_chunks`)
- `job_id` (uuid)
- `attempt` (int)
- `created_at` (iso8601)
- `trace_id`
- `idempotency_key`
- `workspace_id`
- `source_version_id` (for docling.extract)

**Optional:** `priority`, `deadline_at`

**Idempotency key convention:**
- `idempotency_key = sha256(f"{workspace_id}:{source_version_id}:{type}:{extractor}:{extractor_version}")`

Workers can de-dupe on idempotency_key for at-least-once delivery safety.

---

## A2. External ingress (example API contract)

### POST /documents/ingest (or equivalent)

**Request:**
- `workspace_id` (required)
- `source_version_id` (required; raw file already stored under SourceVersion)
- `embedding_set_id` (required)

**Response:**
```json
{
  "source_version_id": "...",
  "extractor": "docling",
  "extractor_version": "2.73.1",
  "status": "QUEUED"
}
```

API layer: validate, ensure SourceVersion exists, create/update extract_runs (QUEUED), enqueue docling.extract with envelope, return.

---

## A3. Internal job messages

### docling.extract
Envelope (required) plus:
- `source_version_id`
- `extractor`, `extractor_version`
- `embedding_set_id` (for handoff after chunking)

### embeddings.embed_document_chunks
Envelope (required) plus:
- **workspace_id**
- **embedding_set_id**
- **document_id**
- **chunker_version**
- optional: chunk_ids (else worker derives from DB)

Example:
```json
{
  "type": "embeddings.embed_document_chunks",
  "job_id": "...",
  "attempt": 1,
  "created_at": "...",
  "trace_id": "...",
  "idempotency_key": "...",
  "workspace_id": "...",
  "embedding_set_id": "...",
  "document_id": "...",
  "chunker_version": "..."
}
```

---

## A4. Service interface (expanded)

```py
class DoclingService:
    async def enqueue_extract(
        self, workspace_id: str, source_version_id: str, embedding_set_id: str
    ) -> str:
        """Creates/updates extract_runs to QUEUED and publishes docling.extract job. Returns run id or status."""

    async def run_extract(self, job: DoclingExtractJob) -> None:
        """Worker entry: conversion → export → chunking → DB → embed enqueue."""

    async def rechunk(
        self,
        workspace_id: str,
        document_id: str,
        embedding_set_id: str,
        chunk_settings: dict,
    ) -> None:
        """Loads Docling JSON from Document.structure_json_uri and re-chunks to a new chunker_version; enqueues embeddings."""

    async def get_status(
        self,
        workspace_id: str,
        source_version_id: str,
        extractor: str,
        extractor_version: str,
    ) -> dict:
        """Reads extract_runs + Document/Chunk summary for UI/API status."""
```
