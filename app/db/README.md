# DB module

SQLAlchemy 2.x + Alembic + SQLite (Postgres-ready). System of record for workspaces, sources, versions, documents, chunks, embedding pointers, runs/events, and optional query logs.

## Quick start

- **Config:** `DBConfig` (pydantic-settings, env prefix `DB_`).
- **Sessions:** `init_db(cfg)` then `async_session_scope()` or `session_scope()`.
- **Migrations:** `alembic upgrade head` (from project root). `render_as_batch=True` for SQLite.

## Migration discipline

- Do not edit migrations after they are merged.
- For destructive changes: add column → backfill → switch code → drop in a later migration.
- SQLite ALTER: use `op.batch_alter_table("table_name")` in migrations.
- One migration per logical change; names like `create_core_lineage_tables`, `create_chunk_embedding_tables`.

## Dev tools

```bash
python -m app.db.dev_tools --counts       # table row counts
python -m app.db.dev_tools --runs 5        # recent runs
```

## Exceptions

- `DbError`, `NotFoundError`, `ConflictError` in `app.db.exceptions`.
- Use `app.db.utils.json_serialize` for stable JSON in TEXT columns (UTC datetimes, sort_keys).
