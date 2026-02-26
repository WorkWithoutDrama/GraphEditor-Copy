# 01 — DB module overview (scope, dependencies, structure)

## Responsibilities

The DB module must provide:

1. **Schema definition** (SQLAlchemy ORM models)
2. **Schema migration system** (Alembic)
3. **Connection/session management**
4. **Repositories** for CRUD and idempotent upserts
5. **DTO layer** (Pydantic models) for boundary-safe inputs/outputs
6. **Run/event tracking utilities** for pipeline observability

## Non-responsibilities

- Vector storage (Qdrant holds vectors)
- Heavy blob storage (raw files, huge JSON) — store URIs instead
- Business orchestration (the pipeline orchestrator calls DB services)

## Key design decisions

### Primary keys
Use `TEXT` IDs (UUID/ULID strings) for portability and distributed friendliness.
- SQLite: store as `TEXT`
- Postgres later: can switch to `UUID` easily

### JSON fields
Prefer `TEXT` containing JSON for maximum portability.
- Use Pydantic to validate/serialize
- Keep JSON small (metadata, stats)

### Idempotency keys
- `source_versions.content_sha256` — global dedupe (UNIQUE)
- `chunks.chunk_hash` ensures deterministic chunk insert
- `(chunk_id, embedding_set_id)` uniqueness for embedding pointer table

### Concurrency in SQLite
- Enable WAL mode
- Set busy timeout
- Keep transactions short
- Consider single-writer patterns for heavy ingestion bursts

## Dependency list (pin-worthy)

Use latest stable versions. Target Python 3.14.

- `SQLAlchemy>=2.0,<2.2`
- `alembic>=1.18`
- `pydantic>=2.0`
- `pydantic-settings>=2.0`
- `python-ulid` or `uuid` (choose one; UUID is fine)
- `pytest`
- `pytest-asyncio`
- `aiosqlite` (async-first; required for async SQLite)

## Proposed package structure

```
app/
  db/
    __init__.py
    config.py               # pydantic-settings model for DB config
    engine.py               # engine creation + PRAGMAs
    session.py              # session factory, context managers
    base.py                 # Base, mixins, conventions
    models/
      __init__.py           # imports for Alembic autoload
      workspace.py
      source.py
      document.py
      chunk.py
      embedding.py
      run.py
      query.py              # optional
    repositories/
      __init__.py
      workspace_repo.py
      source_repo.py
      document_repo.py
      chunk_repo.py
      embedding_repo.py
      run_repo.py
      event_repo.py
      query_repo.py         # optional
    services/
      __init__.py
      chunk_persist.py       # thin, deterministic services
      embedding_persist.py
      run_tracking.py
    migrations/              # alembic folder (versions/ etc.)
  tests/
    test_db_foundation.py
    test_core_lineage.py
    test_chunks_embeddings.py
    test_runs_events.py
    test_query_logging.py     # optional
```

## DB config model (pydantic-settings)

The agent should implement a config like:

- `db_url`: default `sqlite:///./data/app.db`
- `echo_sql`: bool
- `sqlite_pragmas`: allow override (advanced)
- `pool_pre_ping`: bool — **no effect on SQLite** (NullPool); used when migrating to Postgres. Add comment in config.

Keep config loading deterministic for CI and local dev.

## Session patterns (async-first)

Provide:
- `async_session_scope()` — primary (async-first)
- `session_scope()` — sync fallback if needed

Use defaults:
- `autoflush=True` — correctness; fewer subtle bugs
- `expire_on_commit=True`

**Critical:** Repositories must call `session.flush()` explicitly when they need DB-generated values (server defaults) or when subsequent queries depend on newly inserted rows.

Ensure:
- commit on success, rollback on error
- exceptions wrapped into domain-specific DB error classes if needed

## Migration discipline

- One migration per phase (at minimum)
- Use **Alembic default naming**: revision hash + message (e.g. `a1b2c3d4e5f6_001_create_core_lineage_tables.py`)
- Message examples:
  - `create_core_lineage_tables`
  - `create_chunk_embedding_tables`
  - `create_runs_events_tables`
  - `create_query_logs_tables` (optional)
- For SQLite ALTER: wrap in `op.batch_alter_table()` (see Phase F).
- Avoid destructive changes early; use add-backfill-swap-drop if needed.
