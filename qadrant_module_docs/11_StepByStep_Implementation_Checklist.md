# 11 — Step-by-Step Implementation Checklist (do in this order)

This is the execution plan. Each step produces a concrete artifact and a test.

---

## Phase 0 — Lock inputs

1) Confirm `chunks.id` is UUID (or schedule migration).
2) Confirm you have (or will add) SQL `embedding_sets` table:
   - id, name, dim, distance, schema_version, is_active
3) Confirm you have workspace_id in your domain model (workspace-scoped multitenancy).

**Exit criteria:** You can name an embedding set and its vector dimension.

---

## Phase 1 — Module scaffolding

4) Create folder `app/vectorstore/` with files:
   - settings.py, client.py, models.py, filters.py, collections.py, repo.py, errors.py
5) Add `qdrant-client` dependency (pinned version) and a local docker compose for Qdrant.

**Exit criteria:** Module imports without side effects.

---

## Phase 2 — Settings + client

6) Implement `VectorStoreSettings` (Pydantic BaseSettings)
7) Implement `build_qdrant_client(settings) -> AsyncQdrantClient`
8) Add `health()` method to repo that checks connectivity (`get_collections` or similar).

**Exit criteria:** A standalone script can connect and report health.

---

## Phase 3 — Collection spec + ensure_collection

9) Implement `CollectionSpec` + `PayloadIndexSpec` models
10) Implement `build_collection_name(prefix, embedding_set_name, schema_version)`
11) Implement `ensure_collection(client, spec)` exactly as in file 04:
    - exists? create
    - validate size/distance
    - create payload indexes
    - raise MigrationRequired on mismatch

**Exit criteria:** Integration test passes: ensure_collection creates collection + indexes.

---

## Phase 4 — Typed models + filter compiler

12) Implement `ChunkPayload`, `ChunkPoint`, `VectorFilter`, `ScoredChunk`
13) Implement `compile_filter(VectorFilter)`:
    - workspace enforced
    - optional fields compile correctly
14) Unit test filter compilation (pure).

**Exit criteria:** Filter compiler tests pass.

---

## Phase 5 — Repository methods

15) Implement `QdrantVectorStoreRepo`:
    - ensure_ready()
    - upsert_points() with batching
    - search()
    - delete_by_filter()
    - delete_by_document()
    - count()
    - scroll_ids()

16) Add retry wrapper for transient errors (max 3).

**Exit criteria:** Integration tests pass: upsert/search/delete/workspace isolation.

---

## Phase 6 — Pipeline integration (run_items)

17) Add stage constants: VECTOR_INDEX
18) Implement worker function `vector_index_worker_tick()`:
    - fetch pending run_items
    - load embeddings from SQL (bulk)
    - map to ChunkPoint list
    - repo.upsert_points
    - mark run_items done/failed

19) Add end-to-end test in your pipeline test suite:
    - create doc/chunks/embeddings in SQL
    - enqueue run_items
    - run worker tick
    - query Qdrant and verify points exist

**Exit criteria:** Pipeline can index vectors end-to-end.

---

## Phase 7 — Migration tooling

20) Implement `reindex_collection(old, new, workspace_id, ...)`:
    - scroll old
    - upsert into new
    - count/verify
21) Add a CLI command (typer/click) to run reindex.

**Exit criteria:** You can migrate embedding_set schema_version safely.

---

## Phase 8 — Observability + ops hardening

22) Add structured logs + metrics around all Qdrant calls.
23) Add circuit breaker (optional but recommended for production).
24) Add dashboards/alerts (latency, error rate, worker backlog).

**Exit criteria:** You can detect issues before users do.

---

## Deliverables list (what you should have at the end)

- `VectorStoreSettings` + client factory
- `CollectionSpec` + deterministic ensure_collection
- `VectorFilter` typed compiler
- `QdrantVectorStoreRepo` async implementation
- Integration tests with docker Qdrant
- Worker integration with run_items
- Reindex CLI tool

