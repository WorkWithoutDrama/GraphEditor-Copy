# 07 — Phase G: Handoff to Embeddings + Vector DB (enqueue, idempotent upserts)

## G0. Outcomes
- Docling module **does not compute embeddings**.
- It triggers your existing embeddings/vector pipeline with a stable contract that includes **workspace_id** and **embedding_set_id**.
- Vector collection naming is **owned by the vector/embeddings module** (e.g. `ws_{workspace_id}__emb_{embedding_set_id}__v{schema_version}`).

---

## G1. Handoff contract (required fields)

Publish an internal job/event:

**Topic:** `embeddings.embed_document_chunks`

**Payload (required):**
- `job_id`, `created_at`, `trace_id`
- **workspace_id** (tenant; required for collection resolution)
- **embedding_set_id** (required; embeddings worker selects collection from workspace_id + embedding_set_id + schema_version)
- **document_id**
- **chunker_version** (so worker can filter chunks by meta_json.chunker_version if needed)

Optional: `chunk_ids` (worker can derive by querying chunks where document_id=... and optionally chunker_version).

Embeddings worker:
- selects Qdrant collection from `(workspace_id, embedding_set_id, schema_version)`
- loads chunks by document_id (and optionally filters by chunker_version in meta_json)

Acceptance:
- Embeddings worker can run without Docling internals; collection is unambiguous.

---

## G2. Vector point ID strategy

**Docling module does not impose Qdrant point ID.** The vector/embeddings module continues to use its current stable scheme (e.g. derived from chunk_hash + document_id). Payload metadata for points can include document_id, chunk_index, chunk_hash, section_path, etc.

Acceptance:
- Qdrant collection remains consistent after retries; no duplicate points from Docling handoff.

---

## G3. Chunk indexed flag and Docling checkpoint

In SQL (if your schema has it): chunks.indexed, optionally indexed_at, embedding_model. Embeddings worker sets indexed=true after successful vector upsert.

Docling module:
- sets **extract_runs** `status=EMBED_ENQUEUED` after publishing the embed job.

Acceptance:
- You can monitor progress and resume partial failures.

---

## G4. Failure policy between modules

If embedding fails:
- do NOT revert Docling stage statuses
- keep run at CHUNKED or EMBED_ENQUEUED; record embedding job failure separately
- allow embedding worker to retry safely

Acceptance:
- Parsing/chunking results stay reusable even if embeddings are temporarily down.
