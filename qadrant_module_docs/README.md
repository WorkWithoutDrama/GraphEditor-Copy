# Qdrant (Vector Store) Module — Implementation Archive (Async-first)

**Date:** 2026-02-16  
**Context:** This archive is aligned with our app architecture:  
`Ingestion → Docling normalization → Chunking → Embedding/Ranking → Storage`, executed as an **async pipeline** with **idempotent stage tracking via `run_items`**.

This module defines a clean boundary around Qdrant (vector DB): client, collection schema, indexes, typed repo API, migration plan, and integration with our `run_items` worker stage.

## Reading order
1. `01_Context_and_Goals.md`
2. `02_Locked_Decisions.md`
3. `03_Settings_and_Client.md`
4. `04_Collections_and_Indexes.md`
5. `05_Typed_Models_and_Filters.md`
6. `06_Repository_API_and_Behavior.md`
7. `07_Pipeline_Integration_RunItems.md`
8. `08_Migrations_and_Reindex.md`
9. `09_Retries_Timeouts_Observability.md`
10. `10_Testing_Integration.md`
11. `11_StepByStep_Checklist.md`

## What you implement in code
Suggested folder layout:

```
app/
  vectorstore/
    settings.py
    client.py
    models.py
    filters.py
    collections.py
    repo.py
    migrations.py
    errors.py
tests/
  integration/
    test_qdrant_repo.py
```

## Non-goals
- No chunking logic
- No embedding generation
- No ranking logic beyond returning Qdrant scores
- No SQL writes (only consumes IDs produced by SQL stage)

