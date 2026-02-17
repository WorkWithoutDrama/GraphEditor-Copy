# 02 — Decisions and Naming (locked defaults)

This file deliberately **locks defaults** to avoid ambiguity. Alternatives are listed only as *explicit extensions*.

---

## D1. Point ID type (LOCKED)

**Point ID = `chunk_id` (UUID).**

### Why
- Qdrant point IDs support `UUID` and `uint64`.
- Using the SQL chunk primary key directly makes upserts/deletes naturally idempotent.

### Consequence
- SQL `chunks.id` MUST be UUID (or convertible to UUID).
- If you currently use BIGINT IDs, migrate chunks to UUID (recommended), or choose D1b (extension).

### Extension D1b (only if you already have BIGINT)
Point ID = `chunk_id_uint64` (BIGINT). Keep a strict rule: chunk IDs must be non-negative, <= 2^64-1.

---

## D2. Collection strategy (LOCKED)

**One collection per embedding set.**

Naming:
- `collection_name = "chunks__{embedding_set_name}__v{schema_version}"`

Example:
- `chunks__e5_large_v1__v1` (you can simplify; keep it deterministic)

### Why
- Avoids mixing incompatible vector dimensions/metrics.
- Migration (reindex) becomes simpler.
- You can tune collection params per embedding set independently.

### Extension D2b (only if you truly need multiple vectors per point)
Use **Named Vectors** and keep a single collection. This adds complexity to search/upsert routing and migration.
We defer this until there is a real requirement.

---

## D3. Payload schema (LOCKED)

We store the **minimum join keys + filter keys**:

Required payload fields:
- `workspace_id: str` (keyword)
- `document_id: UUID/str` (keyword)
- `chunk_index: int` (integer)
- `chunk_hash: str` (keyword)
- `created_at: datetime` (datetime)

Optional (only if needed):
- `source: str` (keyword)
- `tags: list[str]` (keyword list)

### Not stored in Qdrant
- Full chunk text (canonical in SQL)
- Large raw document metadata blobs

---

## D4. Multitenancy isolation approach (LOCKED)

**Payload-based isolation** using `workspace_id` + filter in every query and delete.

Rule:
- Every search MUST include `workspace_id` filter (enforced by repo, not by callers).

---

## D5. Indexing stage integration (LOCKED)

Vector indexing is tracked as a run stage:
- `stage = "VECTOR_INDEX"`
- `target_type = "chunk"`
- `target_id = chunk_id`

We use `run_items` upsert on `(run_id, stage, target_type, target_id)` to make the stage restartable.

---

## D6. Distance + size (LOCKED)

For each embedding set, lock:
- `vector_size = embedding_set.dim`
- `distance = "Cosine"` (default)

If you use dot-product or euclidean, change it **per embedding set** and bump schema_version.

---

## D7. Write consistency (LOCKED)

**SQL-first, Qdrant-second** with an outbox-like job:

1) Bulk write chunks + embeddings to SQL  
2) Enqueue vector indexing jobs (run_items or dedicated outbox)  
3) Worker performs Qdrant upsert in batches  
4) Mark success/failure on run_items

This avoids “half-written” situations and makes retries safe.

