# MVP Orchestrator Module Plan (Glue Layer) — *Not Final Architecture*

> **Purpose:** Implement the smallest possible **orchestrator** that stitches together already-built modules:
> **SQL DB** + **Vector DB (Qdrant)** + **Docling (parse/chunk)** + **LLM client (LiteLLM/Ollama/Gemini)**  
> to run a **test pipeline**: `file -> chunks -> LLM per chunk -> persist -> inspect DB`.
>
> **Explicitly not final:** This orchestrator is a **single-process MVP runner**. It is designed to be easy to replace later
> with a more robust workflow engine / queue-based processing without rewriting your DB schema or extraction payloads.

---

## 0) Goals & Non‑Goals

### Goals (MVP)
- One command/function runs the full ingestion pipeline end-to-end.
- Stores enough artifacts in SQL + Qdrant to prove feasibility:
  - Document metadata
  - Chunk records
  - Per-chunk processing status
  - LLM extraction results (raw + parsed JSON)
  - Embeddings in Qdrant with payload linking back to SQL IDs
- **Idempotent** reruns: re-ingesting same file does not duplicate chunks/results unless forced.
- **Resumable** run: if it crashes mid-way, re-run continues remaining chunks.

### Non‑Goals (Later)
- Distributed processing / queues / workers
- Graph building / entity resolution across chunks
- Full observability stack (traces/metrics), advanced retries/backoff orchestration
- UI/API layer (beyond a minimal CLI harness)
- Perfect prompt management / eval harness (only a minimal prompt pack)

---

## 1) High-Level Design

### Orchestrator responsibilities
- **Coordinate** module calls in a stable order.
- **Own execution state** (`pipeline_run`, `chunk_run`) so the pipeline can resume.
- **Handle errors** at the boundaries (per chunk) and persist them for debugging.
- **Enforce idempotency rules** (upserts + unique keys).

### Orchestrator must NOT
- Implement parsing/chunking logic (Docling module owns it)
- Implement DB details (SQL module owns sessions + repositories)
- Implement vector store details (Qdrant module owns upsert/query)
- Implement LLM provider details (LLM module owns routing, retries, schemas)

---

## 2) Proposed Module Layout

```
app/
  orchestrator/
    __init__.py
    settings.py          # MVPOrchestratorSettings (pydantic)
    contracts.py         # minimal Protocols / interfaces the orchestrator depends on
    models.py            # DTOs used by orchestrator only (not DB ORM models)
    orchestrator.py      # Orchestrator class + run entrypoints
    cli.py               # minimal CLI harness (optional but recommended)
    errors.py            # orchestrator-specific exceptions (thin)
    README.md            # quick usage / examples
```

> Keep this module **thin**. It should be easily deletable later.

---

## 3) Minimal Contracts (Interfaces)

> The orchestrator should depend on **interfaces**, not concrete implementations.  
> This keeps the orchestrator testable and lets you swap implementations later.

### SQL DB module (expected existing building blocks)
- `UnitOfWork` (async context manager)
  - `.documents` repo
  - `.chunks` repo
  - `.pipeline_runs` repo
  - `.chunk_runs` repo
  - `.extractions` repo
  - `.commit()`, `.rollback()`

### Vector DB module (Qdrant)
- `VectorStore`
  - `upsert_points(points: list[VectorPoint]) -> None`

### Docling module
- `DocumentReader`
  - `read(file_path: Path) -> DoclingDocument`
- `Chunker`
  - `chunk(doc: DoclingDocument) -> list[ChunkDTO]`

### LLM module (LiteLLM router)
- `LLMClient`
  - `extract(prompt_name: str, input: ChunkInput, schema: type[BaseModel]) -> LLMResult`
  - `LLMResult` includes `raw_text`, `parsed` (validated model), `usage`, `model`, `latency_ms`

### Embeddings (if separate)
- `EmbeddingClient`
  - `embed(texts: list[str]) -> list[list[float]]`

> If your LLM module already exposes embeddings, keep a single router interface.

---

## 4) Data Model Needed for MVP (SQL)

> If these tables already exist, map this plan onto your existing schema.  
> If not, add the minimal versions.

### `documents`
- `id` (pk)
- `workspace_id`
- `source_name` (file name)
- `file_sha256` (**unique with workspace_id**)
- `mime`, `size_bytes`
- timestamps

### `chunks`
- `id` (pk)
- `document_id` (fk)
- `chunk_index` (int)
- `chunk_sha256` (optional but recommended)
- `text` (or stored externally; MVP can store in SQL)
- `meta_json` (page, headings, offsets, etc.)
- **unique** `(document_id, chunk_index)` (or `(document_id, chunk_sha256)`)

### `pipeline_runs`
- `id` (pk)
- `workspace_id`, `document_id`
- `status` (RUNNING/DONE/FAILED)
- `llm_profile`, `embed_profile`, `prompt_name`
- `started_at`, `finished_at`
- `error_summary` (nullable)

### `chunk_runs`
- `id` (pk)
- `run_id`, `chunk_id`
- `status` (PENDING/DONE/ERROR)
- `attempts` (int), `latency_ms`
- `error_type`, `error_message` (nullable)
- **unique** `(run_id, chunk_id)`

### `chunk_extractions`
- `id` (pk)
- `chunk_id` (fk), `run_id` (fk)
- `prompt_name`, `model`
- `raw_text` (text)
- `parsed_json` (json)  ← validated output
- `usage_json` (json)   ← tokens/cost if available
- `validation_error` (nullable)
- **unique** `(run_id, chunk_id, prompt_name)` for idempotency

---

## 5) Orchestrator Settings (Pydantic)

`MVPOrchestratorSettings` (examples):
- `max_concurrency: int = 4`
- `llm_profile: str`
- `embed_profile: str`
- `prompt_name: str = "chunk_extract_v1"`
- `max_chunk_attempts: int = 2`
- `stop_on_first_error: bool = False`
- `force_reprocess: bool = False`
- `store_chunk_text_in_sql: bool = True` (MVP convenience)
- `vector_payload_fields: list[str]` (defaults: ids + chunk_index)

---

## 6) End-to-End Flow (MVP)

### 6.1 Entry Point
**Function signature (suggested):**
- `run_file_ingestion(workspace_id: str, file_path: Path, *, settings: MVPOrchestratorSettings) -> str(run_id)`

### 6.2 Steps
1) **Create/Resume pipeline_run**
   - If `force_reprocess=False`, attempt to find existing `document_id` by `(workspace_id, file_sha256)`
   - Create a new `pipeline_run` row with status RUNNING

2) **Docling read + chunk**
   - `doc = reader.read(file_path)`
   - `chunks = chunker.chunk(doc)`
   - Normalize chunk DTOs: `chunk_index`, `text`, `meta_json`

3) **Persist document + chunks (idempotent)**
   - `documents.upsert_by_sha(workspace_id, file_sha256, ...) -> document_id`
   - `chunks.bulk_upsert(document_id, chunks)` using efficient upsert (`on_conflict_do_nothing` where supported)

4) **Create chunk_runs (idempotent)**
   - For each chunk_id in SQL, ensure there is a `(run_id, chunk_id)` in `chunk_runs` with status PENDING
   - Again: bulk insert with conflict-do-nothing

5) **Process chunks loop (async with concurrency limit)**
   - Query pending chunks for the run: `chunk_runs.status == PENDING`
   - For each pending chunk, run `process_one_chunk(run_id, chunk_id)` under a semaphore

6) **Finalize pipeline_run**
   - If all chunks DONE => mark pipeline_run DONE
   - If some ERROR and not stopping => DONE_WITH_ERRORS (or DONE but errors count)
   - If fatal => FAILED with summary

---

## 7) Per-Chunk Processing Contract

### `process_one_chunk(run_id, chunk_id)`
1) Load chunk text + metadata
2) Mark chunk_run as RUNNING (optional; or keep PENDING until DONE/ERROR)
3) Call LLM extraction:
   - input: chunk text + minimal metadata
   - schema: `ChunkExtractionV1` (Pydantic)
   - capture `raw_text`, `parsed_json`, `validation_error`, `usage`, `latency_ms`, `model`
4) Persist extraction row (idempotent upsert by unique key)
5) Embeddings:
   - embed chunk text (or `summary` if that’s your design)
   - upsert to Qdrant with payload: `{workspace_id, document_id, chunk_id, chunk_index, run_id}`
6) Mark chunk_run DONE
7) On exception:
   - increment attempts
   - store `error_type`, `error_message`
   - mark ERROR (or keep PENDING if retryable and attempts < max)

---

## 8) Idempotency & Resumability Rules (MVP)

### Idempotency keys
- Document: `(workspace_id, file_sha256)`
- Chunk: `(document_id, chunk_index)` (or `(document_id, chunk_sha256)`)
- Chunk run: `(run_id, chunk_id)`
- Extraction: `(run_id, chunk_id, prompt_name)`

### Resume behavior
- If pipeline restarts:
  - It reuses existing document + chunk rows
  - It re-creates missing chunk_runs
  - It only processes `PENDING` chunks (and optionally retries ERROR based on settings)

### Force behavior
- `force_reprocess=True`:
  - either create a new run_id and process all chunks again (recommended)
  - or reset statuses for this run (less clean)

---

## 9) Minimal Logging (MVP)

Use structured logs (even plain `logging` with extras is fine):
- Always include: `run_id`, `document_id`, `chunk_id`, `chunk_index`
- Log stage boundaries:
  - `docling.read.start/end`
  - `chunk.persist.start/end`
  - `llm.extract.start/end`
  - `vector.upsert.start/end`
- Log errors with exception class + message, and persist the same into SQL.

---

## 10) Minimal CLI Harness (Recommended for PoC)

### Commands
- `python -m app.orchestrator.cli ingest --workspace ws1 path/to/file.pdf`
  - prints: run_id, document_id, total chunks, done/error counts
- `python -m app.orchestrator.cli inspect --run <run_id> [--limit 5]`
  - prints a short report + sample extraction JSON

> This is the fastest way to demonstrate “it works” without building any API/UI.

---

## 11) Testing Plan (MVP)

### Unit tests (fast)
- Orchestrator flow with mocked contracts:
  - chunk list returned by chunker
  - llm returns deterministic extraction
  - vector store captures upsert payloads

### Integration test (valuable)
- Use temporary SQLite DB (your SQL module)
- Use a local Qdrant (or test container) OR a fake vector store implementation
- Use a stub LLM client that returns canned JSON
- Ingest a small fixture file (e.g., 1–2 pages PDF)
- Assert:
  - 1 document row
  - N chunk rows
  - N chunk_run rows DONE
  - N extraction rows with parsed_json
  - N vectors upserted with correct payload

---

## 12) Definition of Done (MVP)

- [ ] `ingest` runs end-to-end for at least 1 real file
- [ ] SQL contains: document, chunks, run, chunk_runs, extractions
- [ ] Qdrant contains vectors keyed by chunk_id with correct payload
- [ ] Rerun without `force` does not duplicate work and finishes quickly
- [ ] `inspect run_id` shows sample extraction outputs

---

## 13) Implementation Steps (Concrete Task List)

1) **Create module skeleton** `app/orchestrator/*`
2) **Add settings model** `MVPOrchestratorSettings`
3) **Define contracts** (Protocols) in `contracts.py`
4) **Implement Orchestrator class**
   - `run_file_ingestion()`
   - `process_one_chunk()`
   - concurrency/semaphore handling
5) **Wire to existing modules**
   - inject real implementations in a simple factory function
6) **Add minimal CLI**
   - `ingest`
   - `inspect`
7) **Add tests**
   - unit test with mocks
   - one integration test

---

## 14) Planned Replacements (Post‑MVP)

When moving beyond MVP:
- Replace orchestrator loop with queue/worker model
- Add distributed locks / leasing for chunk_runs
- Add prompt registry + eval harness
- Add entity resolution & graph building stage
- Add real observability (OpenTelemetry, metrics, dashboards)
- Add API endpoints and background processing

---

## Appendix A — Suggested Pseudocode

```python
async def run_file_ingestion(workspace_id, file_path, settings):
    sha = compute_sha256(file_path)

    async with uow_factory() as uow:
        doc_id = await uow.documents.upsert_by_sha(workspace_id, sha, source_name=file_path.name, ...)
        run_id = await uow.pipeline_runs.create(workspace_id, doc_id, settings)
        await uow.commit()

    doc = await doc_reader.read(file_path)
    chunks = await chunker.chunk(doc)

    async with uow_factory() as uow:
        await uow.chunks.bulk_upsert(doc_id, chunks)
        chunk_ids = await uow.chunks.list_ids_by_document(doc_id)
        await uow.chunk_runs.bulk_ensure(run_id, chunk_ids)
        await uow.commit()

    pending = await list_pending_chunks(run_id)

    sem = asyncio.Semaphore(settings.max_concurrency)

    async def runner(chunk_id):
        async with sem:
            await process_one_chunk(run_id, chunk_id, settings)

    await asyncio.gather(*(runner(cid) for cid in pending))

    async with uow_factory() as uow:
        await uow.pipeline_runs.finalize(run_id)
        await uow.commit()

    return run_id
```

