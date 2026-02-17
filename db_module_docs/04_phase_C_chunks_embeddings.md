# 04 — Phase C: Chunks + Embedding pointers (Qdrant references)

## Goal
Persist deterministic chunks and link them to embedding sets + Qdrant point IDs.
Ensure idempotency so re-chunking and re-embedding do not create duplicates.

Entities:
- Chunk
- EmbeddingSet (definition/config)
- ChunkEmbedding (pointer into Qdrant)

## Deliverables
- ORM models
- Migration `002_create_chunk_embedding_tables`
- Repositories with bulk insert + idempotent upserts
- Thin services for persisting chunks and embedding pointers
- Tests for idempotency

## Schema (recommended)

### chunks
- `id` TEXT PK
- `document_id` FK → documents.id (ON DELETE CASCADE)
- `chunk_index` INTEGER NOT NULL
- `chunk_hash` TEXT NOT NULL      (sha256(normalized_text + chunking_params_signature))
- `text` TEXT NULL                (optional; prefer URI for large content)
- `text_uri` TEXT NULL            (if storing externally)
- `start_char` INTEGER NULL
- `end_char` INTEGER NULL
- `page_start` INTEGER NULL
- `page_end` INTEGER NULL
- `meta_json` TEXT NULL           (section path, headings, etc.)
Constraints:
- UNIQUE `(document_id, chunk_hash)`
- (optional) UNIQUE `(document_id, chunk_index)` if chunk_index stable
Indexes:
- `(document_id)`
- `chunk_hash`

### embedding_sets
- `id` TEXT PK
- `workspace_id` FK → workspaces.id (ON DELETE CASCADE)
- `name` TEXT NOT NULL
- `model` TEXT NOT NULL
- `dims` INTEGER NOT NULL
- `distance` TEXT NOT NULL     (cosine/dot/l2)
- `qdrant_collection` TEXT NOT NULL
- `created_at`
Constraints:
- UNIQUE `(workspace_id, name)`
Indexes:
- `(workspace_id)`

### chunk_embeddings
- `id` TEXT PK
- `chunk_id` FK → chunks.id (ON DELETE CASCADE)
- `embedding_set_id` FK → embedding_sets.id (ON DELETE CASCADE)
- `qdrant_point_id` TEXT NOT NULL
- `embedded_at` DATETIME NOT NULL
Constraints:
- UNIQUE `(chunk_id, embedding_set_id)`
Indexes:
- `(embedding_set_id)`
- `(chunk_id)`

## Chunking strategy (token-aware + fallback)

- **Primary:** Token-aware chunking — split by token boundaries (e.g., sentence/paragraph-aware); chunks typically short.
- **Fallback:** If chunk text exceeds N bytes (e.g., 64KB) or token limit, store via `text_uri` instead of `text` column.

## Chunk hash (important!)

Define a stable chunk hash computation:
- Normalize text (e.g., trim, collapse whitespace) **or** keep exact text but be consistent.
- Include chunking parameters in the hash signature, e.g.:
  - chunk_size, overlap, splitter version, rules version
Example:
`chunk_hash = sha256(f"{splitter_version}|{chunk_size}|{overlap}|{normalized_text}")`

This ensures:
- same inputs → same chunk_hash
- changing chunk strategy produces new chunks (no collisions)

## Tasks (step-by-step)

### C1 — Implement ORM models
Create:
- `app/db/models/chunk.py` (Chunk)
- `app/db/models/embedding.py` (EmbeddingSet, ChunkEmbedding)

### C2 — Migration
Create `002_create_chunk_embedding_tables` and verify FKs + uniqueness.

### C3 — Repositories
ChunkRepo
- `bulk_create_or_get(document_id, chunks[])`
  - Input includes chunk_hash, chunk_index, text/text_uri, offsets, meta
  - Use dialect-specific bulk insert with `on_conflict_do_nothing` — **never resolve conflicts row-by-row**

EmbeddingSetRepo
- `create_or_get(workspace_id, name, model, dims, distance, qdrant_collection)`

ChunkEmbeddingRepo
- `upsert_pointers(embedding_set_id, items=[(chunk_id, qdrant_point_id)])`
  - Same pattern: bulk insert with `on_conflict_do_nothing`, then bulk SELECT for IDs if needed

**Bulk insert pattern (chunks):**
1. `from sqlalchemy.dialects.sqlite import insert as sqlite_insert` (or `pg_insert` for Postgres)
2. `insert_stmt.on_conflict_do_nothing(index_elements=["document_id", "chunk_hash"])`
3. Execute bulk insert (silently ignores existing rows)
4. Single SELECT: `SELECT id, chunk_hash FROM chunks WHERE document_id=:doc AND chunk_hash IN (:hashes)`
5. Build `{chunk_hash -> id}` mapping from that query

**Bulk insert pattern (chunk_embeddings):**
1. Unique key: `(chunk_id, embedding_set_id)`
2. Bulk insert with `on_conflict_do_nothing(index_elements=["chunk_id", "embedding_set_id"])`
3. Bulk SELECT for all `(chunk_id, embedding_set_id)` pairs attempted, if IDs needed

### C4 — Thin services
ChunkPersistService
- `persist_chunks(document_id, chunk_payloads, chunking_signature)`
- returns chunk IDs mapped to chunk_hash

EmbeddingPersistService
- `persist_qdrant_refs(embedding_set_id, mapping chunk_id → qdrant_point_id)`

### C5 — Tests
- Re-running `persist_chunks` with same payloads returns same rows (no duplicates)
- Re-running embedding pointer persistence updates or keeps stable without duplication
- Uniqueness constraints enforced

## Acceptance checks
- Chunk insert idempotency verified
- Embedding pointer uniqueness verified
- Can select all chunks for a document quickly (index present)

## Pitfalls to avoid
- Storing huge chunk text in DB without limits (use text_uri if needed)
- Non-deterministic chunk_hash computation (e.g. including timestamps)
- Mixing multiple embedding models without embedding_sets table → becomes untraceable
