# 06 — Phase E: Query logging (optional but recommended)

## Goal
Persist retrieval queries and their ranked results to support evaluation, analytics, and debugging.

Entities:
- Query
- QueryResult

This phase is optional. If you are time-boxing, skip now and add later (schema is additive).

## Deliverables
- ORM models
- Migration `004_create_query_logs_tables`
- Repository methods
- Tests

## Schema (recommended)

### queries
- `id` TEXT PK
- `workspace_id` FK → workspaces.id (ON DELETE CASCADE)
- `ts` DATETIME NOT NULL
- `query_text` TEXT NOT NULL
- `embedding_set_id` TEXT NULL    (which embedding config used)
- `top_k` INTEGER NOT NULL
- `filters_json` TEXT NULL
- `latency_ms` INTEGER NULL
- `meta_json` TEXT NULL
Indexes:
- `(workspace_id, ts)`

### query_results
- `id` TEXT PK
- `query_id` FK → queries.id (ON DELETE CASCADE)
- `rank` INTEGER NOT NULL
- `chunk_id` FK → chunks.id (ON DELETE CASCADE)
- `score` REAL NOT NULL
- `rerank_score` REAL NULL
Constraints:
- UNIQUE `(query_id, rank)`
Indexes:
- `(query_id)`
- `(chunk_id)`

## Tasks
1. Implement ORM in `app/db/models/query.py`
2. Create migration `004_create_query_logs_tables`
3. Implement QueryRepo:
   - `create_query(...)`
   - `add_results(query_id, results[])`
4. Add tests:
   - storing query and N results
   - uniqueness on rank

## Acceptance checks
- logging does not significantly slow retrieval (can be toggled)
- results stored are traceable to chunk IDs
- schema additive; no breaking changes
