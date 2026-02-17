# 06 — Phase F: Chunk Persistence (bulk insert/upsert, conflict handling)

## F0. Outcomes
- Efficiently persist N chunks without O(n) exception overhead.
- Preserve **chunk_index** + determinism (plan’s “ordinal” = chunk_index).
- Provide idempotent re-runs.

---

## F1. Batch insert design (and streaming for very large docs)

Create `ChunkRepo.bulk_upsert_chunks(chunks: list[ChunkCreate])` that:
- builds a single `INSERT ... VALUES ...` statement per batch
- uses `ON CONFLICT DO NOTHING` (or DO UPDATE if you allow updates)
- returns inserted count

**Batch sizing:** Bounded to avoid huge in-memory lists and massive SQL statements:
- `batch_rows` (e.g. 200)
- `batch_max_bytes` (e.g. 5 MB of text per batch)

For very large documents: generate chunks as an iterator and persist in these bounded batches.

Acceptance:
- Ingesting large docs remains fast and stable; no OOM from giant batches.

---

## F2. Conflict strategy

Option A (recommended): **do nothing on conflict**
- chunks are deterministic (chunk_hash includes chunker_version + chunk_index + text), so duplicates are safe
- if content changes, that implies settings changed → new chunk_hash → new row

Option B: **do update on conflict**
- only if you want same chunk_id to be “mutable”
- not recommended for reproducibility

Acceptance:
- No silent corruption of chunks across versions.

---

## F3. Indexes

Use existing / add indexes:
- `chunks(document_id, chunk_index)` (ordering)
- `chunks(document_id)` (batch retrieval)
- uniqueness on `(document_id, chunk_hash)` (existing)
- optionally `chunks(chunk_hash)` (analytics)

Acceptance:
- Embedding worker can fetch chunks fast by document_id.

---

## F4. Checkpoint

After chunk insert completes:
- update **extract_runs** `status=CHUNKED`
- store `chunk_count` (in extract_runs or in Document.stats_json)

Acceptance:
- A run in CHUNKED state has stable chunk set retrievable from SQL by document_id.

