# 09 — Error Handling, Retries, Observability

---

## 9.1 Error taxonomy (typed exceptions)

Define explicit exceptions in `vectorstore/errors.py`:

- `VectorStoreError` (base)
- `VectorStoreUnavailable` (network/timeouts)
- `CollectionSchemaMismatch` (size/distance mismatch)
- `MigrationRequired` (expected when schema version differs)
- `BadFilterError` (missing workspace_id, invalid ranges)
- `UpsertFailed` (after retries exhausted)

## 9.2 Retry policy (locked defaults)

Retry ONLY for transient categories:
- timeouts
- connection resets
- 502/503/504
- rate limiting / overload signals

No retry for:
- schema mismatch
- bad request (validation errors)

Defaults:
- max_retries = 3
- backoff = base * (2^attempt) + jitter

## 9.3 Circuit breaker (recommended)

If Qdrant is down, do not hammer it:
- after N consecutive failures, open breaker for T seconds
- fail fast (VectorStoreUnavailable)
- let worker retry later

## 9.4 Metrics + logging (minimum)

Emit:
- `qdrant_upsert_batch_seconds`
- `qdrant_search_seconds`
- `qdrant_delete_seconds`
- counts: points_upserted, points_deleted, search_results
- failures by exception type

Log context:
- collection_name
- embedding_set_name
- workspace_id (safe)
- batch_size

## 9.5 Timeouts

- Keep request timeouts short (10s) and rely on retries for blips.
- For large reindex jobs, allow a longer timeout or smaller batches.

