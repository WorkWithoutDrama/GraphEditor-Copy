# 07 — Pipeline Integration with run_items (Idempotent stage execution)

This section aligns Qdrant writes with our earlier DB architecture decision:

- `events` is append-only history
- `run_items` is “current status” with UPSERT
- Uniqueness:
  `UNIQUE(run_id, stage, target_type, target_id)`

## Proposed stage name
`STAGE_VECTOR_INDEX` (or `VECTOR_INDEX`)

## Target identity
- `target_type = "chunk_embedding"` (recommended)
- `target_id = chunk_embedding_id` OR `(chunk_id, embedding_set_id)` canonicalized

Recommended: store `chunk_embedding_id` in SQL so each vector write has one stable identifier.

## Worker flow (exact)
1) **SQL stage** writes:
   - document/chunk rows (bulk upsert)
   - embedding rows (bulk upsert)
   - emits `run_items` for `VECTOR_INDEX` for each chunk_embedding row:
     - status = PENDING
     - metrics: vector_size, embedding_set_slug, etc.

2) **Vector index worker** (async):
   - Pull `run_items` where stage=VECTOR_INDEX and status=PENDING (batch)
   - Fetch needed data from SQL:
     - chunk_id (UUID) + embedding vector + workspace_id + document_id + chunk_index + embedded_at
   - Call Qdrant repo:
     - ensure_collection(embedding_set_slug)
     - upsert(batch_points)
   - Update run_items:
     - status = DONE
     - timestamps, counts
   - On failure:
     - status = FAILED
     - last_error, attempt_count++

## Why SQL-first
Prevents “Qdrant has vectors for chunks that SQL doesn’t know about”.
Also makes the pipeline restartable: Qdrant can be repopulated from SQL.

