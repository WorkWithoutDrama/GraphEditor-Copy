# Critical Review: Docling Module Implementation Plan

**Reviewed:** 2026-02-16  
**Scope:** `docling_module_plan_archive/` (Phases A–I + Appendices A–C)

---

## Executive Summary

The plan is **structurally sound** and shows strong awareness of idempotency, determinism, and async/worker boundaries. It is suitable as a reference for building a docling-based ingestion pipeline. However, it is written largely **in isolation** from the existing codebase: it assumes schema and session defaults that differ from the current app, omits integration with existing document/chunk/vector abstractions, and leaves several design choices underspecified. **Recommendation:** treat the plan as a design spec and produce an explicit **integration addendum** that maps it onto the current DB/vector modules and resolves the conflicts below before implementation.

---

## 1. Strengths

### 1.1 Architecture and boundaries
- **Clean separation** of Docling (converter/chunking/artifacts) from service/repo/adapters is well defined. The rule “service MUST NOT import SQLAlchemy; repo MUST NOT import Docling” is testable and avoids big-ball-of-mud.
- **Port interfaces** (DocumentRepoPort, ArtifactRepoPort, ChunkRepoPort, FileStorePort, JobPublisherPort) are narrow and enable testing without real DB/queue.
- **Phasing** (A→I) is logical: foundation → storage → conversion → artifacts → chunking → persistence → handoff → tests → rollout.

### 1.2 Idempotency and determinism
- **Deterministic IDs** (document_id, source_sha256, artifact_id, chunk_id) and uniqueness constraints are clearly specified. Re-ingest and re-chunk behavior is predictable.
- **Status FSM** (RECEIVED → STORED → PARSED → ARTIFACTS_STORED → CHUNKED → EMBED_ENQUEUED → COMPLETED / FAILED) with checkpointing supports safe retries.
- **Bulk upsert + ON CONFLICT** is correctly preferred over per-row try/insert/catch.

### 1.3 Operational and safety concerns
- **Hard max-tokens enforcement** (Phase E3) explicitly addresses Docling’s historical non-strict behavior—practical and necessary for embedding limits.
- **Performance guardrails** (Phase H4): caps on file size, pages, chars, chunks, plus timeouts and circuit-breakers, are appropriate for production.
- **Re-chunk from docling_json** (Phase I2) and version fields (parser_version, chunker_version) support tuning without re-upload.

### 1.4 Documentation
- Error taxonomy (Appendix B), API contracts (Appendix A), and config reference (Appendix C) give implementers concrete targets.
- “Acceptance” bullets per section are useful as completion criteria.

---

## 2. Gaps and Inconsistencies

### 2.1 Session and transaction guidance vs current app
**Plan (Phase A5):** Recommends `autoflush=False`, `expire_on_commit=False`, explicit `session.flush()` when needed, and returning DTOs (not ORM objects).

**Current app (`app/db/session.py`):** Uses `autoflush=True`, `expire_on_commit=True` for both sync and async session makers.

**Impact:** Adopting the plan’s repo patterns in the current app without changing session defaults will either (a) keep current behavior and risk implicit flushes / detached-object issues in orchestration, or (b) require changing global session config and potentially affecting all DB usage. The plan does not say whether the docling module should use a **separate** session factory with different flags or whether the whole app should migrate.

**Recommendation:** Decide explicitly: either a docling-specific session factory with the recommended flags, or an app-wide migration with a short note in the plan.

### 2.2 Schema alignment with existing DB models
**Plan assumes:**
- `documents` keyed by `source_sha256` (or `tenant_id, source_sha256`) with status, error_code, byte_size, mime_type, page_count, etc.
- Separate `artifacts` table (artifact_id, document_id, kind, content_hash, storage_uri, content).
- `chunks` with chunk_id (deterministic), ordinal, text, text_for_embedding, token_count, content_hash, section_path, etc.
- Optional `ingest_jobs` or equivalent for job tracking.

**Current app:**
- **Document** (`app/db/models/document.py`): Unique on `(source_version_id, extractor, extractor_version)`. Fields: structure_json_uri, plain_text_uri, language, stats_json. **No** status FSM, **no** source_sha256, **no** byte_size/mime_type.
- **Chunk** (`app/db/models/chunk.py`): Unique on `(document_id, chunk_hash)`. Has chunk_index, text, text_uri, start_char, end_char, page_start, page_end, meta_json. **No** chunk_id as primary key, **no** text_for_embedding, **no** token_count, **no** ordinal (chunk_index is similar but naming differs).
- **No** `artifacts` table; **no** `ingest_jobs` table; documents are tied to **source_versions**, not raw file hashes.

**Impact:** The plan describes a **different** document lifecycle (file → hash → status pipeline) and schema. Implementing it “as written” would require either:
- New tables (e.g. `ingest_documents`, `artifacts`) and mapping to existing `documents`/`chunks` at handoff, or
- Migrating existing `documents`/`chunks` to the plan’s shape (breaking change for current usage).

The plan does not mention `source_version_id`, `SourceVersion`, or the existing document/chunk schema. This is the **largest single gap**.

**Recommendation:** Add an “Integration with existing schema” section that either (1) defines new tables and a clear mapping (e.g. “one ingest_document → one Document after CHUNKED”) or (2) specifies how to extend current tables (new columns, new tables for artifacts only) and how status is stored (e.g. on Document or on a new ingest_state table).

### 2.3 Vector store and workspace/embedding-set model
**Plan (Phase G2, Phase I3):** Uses `chunk_id` as Qdrant point ID; discusses collections per `chunker_version` vs single collection with version in payload.

**Current app (`app/vectorstore/collections.py`, etc.):** Collection naming is `ws_{workspace_id}__emb_{embedding_set_id}__v{schema_version}`. The vector module is workspace- and embedding-set-centric; there is no mention of document_id or chunker_version in the collection naming.

**Impact:** Handoff “embeddings.embed_document_chunks” with document_id and chunk_ids is compatible, but “which Qdrant collection?” is not specified. In the current model, it likely depends on workspace and embedding set, which the plan does not mention. So either the docling plan assumes a single global collection, or the handoff contract must include workspace_id and embedding_set_id (or equivalent).

**Recommendation:** Extend the handoff contract (Appendix A, Phase G) with workspace/embedding-set (or equivalent) so the embeddings worker knows which collection to upsert into. Align Phase I3 (Qdrant coexistence) with existing collection naming and schema versioning.

### 2.4 Tenant / multi-tenancy
Plan mentions `(tenant_id, source_sha256)` as an optional uniqueness key but does not define tenant_id, how it is supplied at ingest, or how it propagates to chunks and vector writes. If the product is single-tenant, this is fine but should be stated; if multi-tenant, the plan is incomplete.

### 2.5 Queue and job transport
**Plan:** Uses abstract `JobPublisherPort` and topics `docling.parse`, `embeddings.embed_document_chunks`. No concrete transport (Redis, SQS, in-memory, etc.) or message envelope (e.g. idempotency key, trace id) is specified.

**Impact:** Implementers must invent or copy from elsewhere. For observability and retries, at least a minimal envelope (e.g. job_id, document_id, created_at) would help.

**Recommendation:** Add a short “Job envelope” subsection (e.g. in Appendix A) with required fields and one example (e.g. Redis JSON or SQS body).

### 2.6 Re-chunk and “reconstruct from docling_json”
**Phase I2** says: “Re-chunk from docling_json: load JSON → reconstruct document (or use supported import) → run chunker … If reconstruction isn’t supported: re-run Docling parse.”

Whether Docling supports **reconstructing** a DoclingDocument from its own JSON export (without re-parsing the raw file) is implementation-dependent. The plan does not cite or assume a specific Docling API for “import from our JSON.” If unsupported, every re-chunk would require re-parse, which contradicts “Tuning chunk settings does not require re-upload.”

**Recommendation:** Verify Docling’s import/load-from-JSON story; if missing, either document “re-chunk requires re-parse” or add a note that a small adapter (JSON → internal doc model) may be needed.

### 2.7 FileStore path and raw artifact ownership
**Phase B3** stores raw file at e.g. `/data/raw/{sha256[:2]}/{sha256}` and says “Record artifacts(kind=raw).storage_uri”. Phase B is “inputs & raw storage” and creates the Document row; Phase D is “artifact export” and creates docling_json, docling_md, etc. So “artifacts(kind=raw)” is written in Phase B, but the plan’s ArtifactRepoPort and bulk_upsert_artifacts are introduced in Phase A and used in Phase D. Whether the **raw** artifact is upserted in Phase B (separately) or in a single artifact batch in Phase D is unclear. If both phases write artifacts, ordering and idempotency are fine, but the narrative could be clearer.

**Recommendation:** State explicitly: “Phase B creates the document and the raw artifact row (kind=raw); Phase D adds docling_json (and optional) artifacts in the same artifacts table.”

### 2.8 Ordinal vs chunk_index
Plan uses **ordinal** (0..n-1) and “(document_id, ordinal) UNIQUE”; existing Chunk model uses **chunk_index**. Semantically the same; naming should be aligned in the integration addendum to avoid two names for the same concept (e.g. stick to chunk_index in DB, map to “ordinal” in DTOs if desired).

---

## 3. Technical Risks

### 3.1 Process pool and async worker
Phase C3 recommends a process pool for CPU-heavy parsing and says “never run Docling conversion on the main API event loop.” It does not specify how the **worker** is started (separate process, same process with thread/process pool, or a dedicated worker process consuming from a queue). If the same process runs both API and worker logic, process-pool usage must be clearly scoped (e.g. only in worker code path) to avoid deadlocks or heavy work on the API process.

### 3.2 Tokenizer and embedding model coupling
Phase E2 says token counts must align with the embedding provider (OpenAI vs HF, etc.). The plan does not specify where the embedding model (and thus tokenizer) is configured—docling module vs embeddings module. If the embeddings module owns the model, the docling module must either receive a tokenizer from the embeddings module or rely on a shared config. Otherwise you risk docling using one tokenizer and the embedding API using another, leading to “input too long” or wasted capacity.

### 3.3 Large batch and memory
Phase F1 suggests 200–1000 chunks per batch. For very large documents (e.g. 10k chunks), building a single INSERT with 1000 rows of long text can be memory-heavy. The plan could add a short note on streaming or batching in smaller chunks when chunk text size is large.

---

## 4. Minor Omissions

- **Authentication/authorization:** No mention of who can call POST /documents/ingest or run backfill (Phase I4). Acceptable if delegated to API layer, but could be one sentence.
- **Rate limiting:** Not mentioned; may be desired at ingest API or job consumption level.
- **Appendix A service interface:** Only two methods are shown (`ingest_from_source_uri`, `run_parse_and_chunk`). A method for “re-chunk only” (Phase I2) and possibly “get status” would round out the contract.
- **Docling version pinning:** Plan references “DocumentConverter” and “HybridChunker” but does not pin a minimum Docling version or list known incompatibilities. A single line (e.g. “Tested with docling>=2.x”) would help.

---

## 5. Recommendations Summary

| Priority | Action |
|----------|--------|
| **High** | Add an **integration addendum** that maps the plan’s schema (documents, artifacts, chunks, status) to the **existing** DB models and session usage (or defines new tables and migration path). |
| **High** | Resolve **session defaults**: docling-specific session vs app-wide change, and document the choice. |
| **High** | Extend **handoff contract** (and Phase G) with **workspace_id / embedding_set_id** (or equivalent) so the embeddings worker knows which vector collection to use. |
| **Medium** | Clarify **raw artifact** write: Phase B creates document + raw artifact row; Phase D adds other artifacts. |
| **Medium** | Verify Docling **“reconstruct from JSON”** support and document re-chunk strategy accordingly. |
| **Medium** | Add minimal **job envelope** (e.g. job_id, document_id, created_at) to Appendix A. |
| **Low** | Align **ordinal** vs **chunk_index** naming in integration doc. |
| **Low** | Add a sentence on **tenant_id** (or state single-tenant). |
| **Low** | Pin or recommend **Docling version** and mention tokenizer ownership (docling vs embeddings module). |

---

## 6. Conclusion

The Docling module plan is **well thought out** for a self-contained pipeline: clear phases, good idempotency and determinism, and sensible operational guardrails. Its main weakness is **lack of alignment with the current codebase**: different document/chunk model, different session defaults, and no treatment of workspace/embedding-set in the vector handoff. Addressing the high-priority items above in an **integration addendum** will make the plan directly implementable and avoid surprises during development.
