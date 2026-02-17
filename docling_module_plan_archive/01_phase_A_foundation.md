# 01 — Phase A: Foundation (module boundaries, settings, idempotency)

## A0. Outcomes
By the end of this phase you have:
- a new `docling` module package in the codebase,
- a stable, testable **service/repo/adapters** split,
- deterministic **IDs + status FSM** for safe retries (FSM in **extract_runs**; see 13_integration_addendum.md),
- configuration via Pydantic settings,
- **DB alignment:** existing **documents** and **chunks**; new **extract_runs** table for operational state (no separate artifacts table).

---

## A1. Create module skeleton

### Target package layout
```
app/modules/docling/
  __init__.py
  settings.py
  schemas.py
  errors.py
  ids.py
  service.py
  converter.py
  chunking.py
  artifacts.py
  ports.py
  repo.py
  adapters/
    filestore.py        # for derived outputs (docling JSON, plain text); raw file owned by SourceVersion
    jobs.py             # queue publisher/consumer (pluggable)
    clock.py            # for testable timestamps
  tests/
```

### Architectural rule
- `service.py` MUST NOT import SQLAlchemy models directly.
- `repo.py` MUST NOT import Docling.
- Docling code lives only in `converter.py`, `chunking.py`, `artifacts.py`.

Acceptance:
- Import graph stays clean (no “everything imports everything”).

---

## A2. Settings (Pydantic) & defaults

Create `DoclingSettings` with explicit defaults you can tune later:

- **Input limits**
  - `max_file_size_bytes` (e.g. 20 MB)
  - `max_num_pages` (e.g. 200)
  - `allowed_formats` (PDF/DOCX/PPTX/HTML/MD/IMAGE, etc.) — passed to DocumentConverter.

- **Execution**
  - `parse_concurrency`: semaphore for parallel conversions
  - `use_process_pool`: bool (recommended if parsing is CPU-heavy)
  - `process_pool_workers`: int

- **Artifacts**
  - `store_docling_json`: true
  - `store_docling_md`: optional
  - `artifact_text_inline_max_chars`: threshold for storing text directly in SQL vs file store

- **Chunking**
  - `chunker`: `hybrid` (default) or `hierarchical`
  - `target_tokens`: e.g. 800
  - `max_tokens`: e.g. 1000
  - `overlap_tokens`: e.g. 80
  - `enforce_max_tokens_hard`: true (see Phase E; HybridChunker has historical non-strict enforcement notes)

- **Idempotency**
  - `dedupe_strategy`: `sha256` (recommended)
  - `rehydrate_from_artifact_json`: true (re-chunk without re-parse)

Acceptance:
- Settings are “all-in-one” and produce identical behavior between API and worker processes.

---

## A3. Domain status machine (FSM)

Store status in **extract_runs** (not on Document). Table unique on `(workspace_id, source_version_id, extractor, extractor_version)`.

Status values: `QUEUED` → `RUNNING` → `PARSED` → `ARTIFACTS_STORED` → `CHUNKED` → `EMBED_ENQUEUED` → `COMPLETED`; failure at any stage: `FAILED`.

extract_runs fields (minimal): `status`, `attempt`, `trace_id`, `error_code`, `error_message`, `created_at`, `updated_at`, `started_at`, `finished_at`.

Rules:
- state transitions are monotonic
- each stage update is persisted with timestamps and error details
- retries resume from the last successful state (checkpointing)

Acceptance:
- A retry cannot accidentally “skip” a stage or create duplicates.

---

## A4. Deterministic IDs & uniqueness constraints (aligned with existing schema)

### Document
- **Idempotency:** `(source_version_id, extractor="docling", extractor_version)` → existing Document row (get_or_create).
- `document_id` = Document.id (DB primary key).

### Chunk (use chunk_index; collision-safe hash)
- **ordinal** in plan = DB field **chunk_index** (0..n-1). Use `chunk_index` in all DB-facing code.
- **chunk_hash** (required for uniqueness): `chunk_hash = sha256(f"{chunker_version}:{chunk_index}:{text_for_embedding}")` — prevents collisions when repeated boilerplate appears in one doc.

### Uniqueness constraints (SQL)
- Document: existing `(source_version_id, extractor, extractor_version)` UNIQUE.
- extract_runs: `(workspace_id, source_version_id, extractor, extractor_version)` UNIQUE.
- Chunk: existing `(document_id, chunk_hash)` UNIQUE; index `(document_id, chunk_index)` for ordering.

Acceptance:
- Re-runs with same settings never duplicate documents or chunks.

---

## A5. Session & transaction guidance (keep current app defaults)

The app uses `autoflush=True` and `expire_on_commit=True`. Keep these; adapt repo patterns instead.

**Repo rules (R1–R4):**
- **R1** Repos return DTOs or primitives (ids, counts) only — never live ORM objects.
- **R2** For “check then write” flows, use `with session.no_autoflush:` where needed to avoid implicit flushes.
- **R3** Prefer SQLAlchemy Core bulk inserts with conflict handling over ORM per-row inserts.
- **R4** Call `session.flush()` explicitly when you need generated PKs before commit.

Acceptance:
- No “Instance <...> is not bound to a Session” surprises; global DB behavior stays consistent.

---

## A6. Port interfaces (what Docling module depends on)

Define narrow ports so you can test without real DB/queue:

- `DocumentRepoPort`
  - `get_or_create_document(source_version_id, extractor, extractor_version, ...)` → Document DTO / id
  - `update_document(document_id, ...)` (e.g. structure_json_uri, plain_text_uri, language, stats_json)
- `ExtractRunsPort`
  - `get_or_create_run(workspace_id, source_version_id, extractor, extractor_version)` → run id
  - `update_run_status(run_id, status, error_code?, error_message?, ...)`
- `ChunkRepoPort`
  - `bulk_upsert_chunks(chunks: list[ChunkCreate])` → inserted count
  - `mark_chunks_indexed(...)` (optional; embeddings worker may set)
- `FileStorePort` (for **derived** outputs only; raw file owned by SourceVersion)
  - `put_bytes(key, bytes) -> uri`
  - `open_stream(uri) -> file-like`
- `JobPublisherPort`
  - `publish(topic, payload)` (payload includes required envelope; see Appendix A)
- `TokenizerSpec` (or config): resolved from `embedding_set_id`; Docling uses only for chunk token counts / max-token enforcement (embeddings module owns the model).

Acceptance:
- Docling service can be unit-tested with fakes/mocks.

