# Qdrant Module Plan — Review Critique

## Summary

The Qdrant integration plan is well-structured and follows sound architectural principles (async-first, idempotent, typed boundaries, SQL as source of truth). Most decisions align with the existing SQLite schema. Several integration gaps and terminology mismatches need resolution before implementation.

---

## Strengths

- **Clear separation of concerns** — Qdrant module handles only vector storage; no chunking/embedding logic
- **Idempotency** — `point_id = chunk_id` (UUID) aligns with SQL; upserts are safe
- **SQL as source of truth** — Vectors can be rebuilt via reindex; no orphan data in Qdrant
- **run_items integration** — Proposed `VECTOR_INDEX` stage and `target_type="chunk_embedding"` fit existing schema
- **EmbeddingSet / ChunkEmbedding** — Existing SQL models (`dims`, `distance`, `qdrant_collection`, `qdrant_point_id`) support the plan
- **Operational safety** — New-collection migration, retries for transient errors, integration tests

---

## Critical gaps

### 1. tenant_id vs workspace_id

The plan uses `tenant_id` in payloads and filters. The SQL schema uses `workspace_id` (workspace → source → source_version → document → chunk). There is no `tenant_id` column.

**Action:** Either use `workspace_id` in Qdrant payloads, or explicitly define `tenant_id = workspace_id` and document the mapping. The worker must join `chunk → document → source_version → source → workspace` to obtain workspace for each chunk.

### 2. Where do vectors come from?

Doc 07 states the worker should "fetch embedding vector from SQL," but vectors are not stored in SQL. The DB module stores only `qdrant_point_id` pointers.

**Action:** Clarify how the vector worker obtains embeddings:
- In-process: embedding and vector-index steps run together; vectors passed in memory
- Queue: embedding stage pushes `(chunk_id, vector, metadata)` to a queue; worker consumes and upserts

Update doc 07 to describe the actual data flow.

### 3. EmbeddingSet schema mismatch (Phase 0 checklist)

The checklist expects: `id, name, dim, distance, schema_version, is_active`.

Actual schema has: `id`, `workspace_id`, `name`, `model`, `dims`, `distance`, `qdrant_collection`, `created_at`. No `schema_version` or `is_active`.

**Action:** Align the checklist with the real schema. Decide whether to add `schema_version` or derive it from settings.

### 4. Collection naming conflict

The plan defines `build_collection_name(prefix, slug, schema_version)`, but `EmbeddingSet` already has `qdrant_collection`. Two possible sources of truth.

**Action:** Either treat `EmbeddingSet.qdrant_collection` as authoritative and set it with the same rule, or remove it and always compute the name. Clarify `embedding_set_slug` (name vs slug vs `qdrant_collection`).

---

## Minor issues

- **ChunkPayload.created_at** — Chunk has no `created_at`; use `embedded_at` from ChunkEmbedding
- **ChunkPayload.chunk_hash** — Indexed in doc 04 but not listed in doc 05’s ChunkPayload; add for document-bound deletes
- **requirements.txt** — Add and pin `qdrant-client`

---

## Pre-implementation checklist

1. Resolve tenant_id vs workspace_id
2. Define how the vector worker obtains embeddings; update doc 07
3. Align Phase 0 with real EmbeddingSet schema
4. Clarify collection naming (SQL field vs computed)
5. Add chunk_hash to ChunkPayload; use embedded_at for created_at
6. Add qdrant-client to requirements.txt
