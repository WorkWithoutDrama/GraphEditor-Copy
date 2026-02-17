# 11 — Step-by-step Implementation Checklist (linear execution)

## Phase A — Foundations
A1) Create `app/vectorstore/` package and file skeleton.  
A2) Implement `VectorStoreSettings` (Pydantic) and wire into app settings loader.  
A3) Implement `AsyncQdrantClient` factory with timeouts.  
A4) Add typed errors (`VectorStoreError`, `VectorSchemaMismatchError`, `VectorTenantMissingError`).  

## Phase B — Schema and ensure_collection
B1) Decide `embedding_set_slug` source (SQL table or config).  
B2) Implement `collection_name(embedding_set_slug)`.  
B3) Implement `ensure_collection()`:
- exists? create if missing
- validate if exists
- create payload field indexes

B4) Add a small CLI or admin function to run `ensure_collection()` for all embedding sets.

## Phase C — Repo core operations
C1) Implement `upsert(points)` with batching.  
C2) Implement `search(query_vector, filter, limit)` returning `ScoredChunk`.  
C3) Implement `delete_by_document()` via filter.  
C4) Implement `scroll_ids()` for reindex tooling.

## Phase D — Pipeline integration (run_items)
D1) Add stage constant `VECTOR_INDEX`.  
D2) SQL pipeline stage emits `run_items` PENDING for each chunk_embedding target.  
D3) Worker:
- pulls run_items batch
- loads vectors + payload from SQL
- calls qdrant repo upsert
- UPSERT run_items status DONE/FAILED

D4) Ensure worker is restart-safe:
- re-run PENDING or FAILED (with attempt limit)

## Phase E — Migrations
E1) Add schema_version into settings.  
E2) Implement `reindex(old, new)` helper (prefer SQL as source).  
E3) Add admin command: “migrate embedding_set X from vN to vN+1”.

## Phase F — Tests
F1) Add docker-compose Qdrant for tests.  
F2) Write integration tests listed in section 10.  
F3) Run tests in CI pipeline (optional at start).

## Phase G — Hardening
G1) Add retry/backoff wrapper and classify errors.  
G2) Add logs/metrics around each Qdrant call.  
G3) Load-test batch sizes and tune.

