# 13 — Integration Addendum (alignment with existing codebase)

Date: **2026-02-16**  
Applies to: Phases A–I + Appendices. Resolves schema/session/handoff gaps from CRITIQUE.md.

---

## 1. Decisions

### 1.1 No new ingest_documents / artifacts schema
The plan maps **directly** onto existing models:
- **Document** — unique on `(source_version_id, extractor, extractor_version)`. Docling uses `extractor="docling"`, `extractor_version` = Docling runtime version. Stores `structure_json_uri`, `plain_text_uri`, `language`, `stats_json`.
- **Chunk** — unique on `(document_id, chunk_hash)`. Stores `chunk_index`, `text` and/or `text_uri`, `page_start`/`page_end`, `meta_json`.

No separate `artifacts` table; derived outputs live in `Document.*_uri` and optional refs in `stats_json`.

### 1.2 Operational state: `extract_runs` table
Status FSM lives in a separate table (Document has no status/error fields):
- **extract_runs** unique on `(workspace_id, source_version_id, extractor, extractor_version)`
- Fields: `status` (QUEUED|RUNNING|PARSED|ARTIFACTS_STORED|CHUNKED|EMBED_ENQUEUED|COMPLETED|FAILED), `attempt`, `trace_id`, `error_code`, `error_message`, `created_at`, `updated_at`, `started_at`, `finished_at`

### 1.3 Multi-tenancy = workspace_id
Tenant boundary is `workspace_id`. Required in job envelopes and embed handoff. Single-tenant: use `workspace_id="default"`.

### 1.4 Vector collection naming
Owned by vector/embeddings module. Docling hands off `workspace_id` and `embedding_set_id` so the embeddings worker can resolve collection (e.g. `ws_{workspace_id}__emb_{embedding_set_id}__v{schema_version}`).

### 1.5 Tokenizer ownership
Tokenizer is owned by embeddings. Docling receives a `TokenizerSpec` (resolved from `embedding_set_id` via config or port) and uses it only for chunk sizing / max-token enforcement.

### 1.6 Raw file ownership
Raw file is owned by **SourceVersion** (already persisted). Docling reads from SourceVersion’s URI/stream and writes only **derived** outputs (docling JSON, plain text, optional markdown) to file store and records URIs on Document.

---

## 2. Schema mapping (plan → current DB)

| Plan concept        | Current DB |
|--------------------|------------|
| document idempotency | `(source_version_id, "docling", extractor_version)` → Document |
| status FSM         | extract_runs.status |
| docling JSON       | Document.structure_json_uri |
| plain text         | Document.plain_text_uri |
| conversion metadata | Document.stats_json (parser, chunking, conversion, optional artifact refs) |
| ordinal            | Chunk.chunk_index |
| chunk hash         | `chunk_hash = sha256(f"{chunker_version}:{chunk_index}:{text_for_embedding}")` |
| chunk metadata     | Chunk.meta_json (chunker_version, section_path, captions, source_artifact, token_count) |
| embedding-ready text | Chunk.text (or text_uri for large chunks) |

---

## 3. Session defaults (no global change)
Keep app’s `autoflush=True`, `expire_on_commit=True`. Repo rules:
- **R1** Repos return DTOs/primitives only, never ORM objects.
- **R2** For “check then write”, use `session.no_autoflush` where needed.
- **R3** Prefer Core bulk inserts with conflict handling.
- **R4** Call `session.flush()` when PKs are needed before commit.

---

## 4. Re-chunk from stored JSON
Use **DoclingDocument.load_from_json(path)** when `structure_json_uri` exists. Re-chunk without re-parse. If JSON missing/unreadable, fallback to reconvert from source.

---

## 5. Acceptance checklist (integration)
- [ ] extract_runs table exists and is used for status/error tracking.
- [ ] Docling worker produces a Document row for `(source_version_id, "docling", docling_version)`.
- [ ] Document.structure_json_uri is always written on success.
- [ ] Chunks use deterministic chunk_index and collision-safe chunk_hash.
- [ ] Embed job includes workspace_id, embedding_set_id, document_id, chunker_version.
- [ ] Re-chunk uses DoclingDocument.load_from_json when structure_json_uri is available.
- [ ] No Docling conversion on API event loop; worker only.
