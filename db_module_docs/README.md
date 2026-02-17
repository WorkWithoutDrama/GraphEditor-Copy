# DB Module Implementation Pack (SQLite + SQLAlchemy + Alembic)

Generated: 2026-02-16 (timezone reference: Europe/Madrid)

This archive is written for an **AI coding agent** to implement a robust database module for our document-ingestion / extraction / chunking / embedding pipeline.

## File map

- `00_app_overview.md` — high-level application context and where the DB module fits
- `01_db_module_overview.md` — DB module scope, responsibilities, dependencies, package structure
- `02_phase_A_foundation.md` — engine/session, config, base models, Alembic wiring
- `03_phase_B_core_lineage.md` — workspaces/sources/versions/documents schema + repos + tests
- `04_phase_C_chunks_embeddings.md` — chunks + embedding pointers + idempotency
- `05_phase_D_runs_events.md` — runs, run_items, events (observability)
- `06_phase_E_query_logging_optional.md` — optional query logs and results
- `07_phase_F_hardening.md` — WAL/PRAGMAs, concurrency, migrations discipline, tooling
- `08_success_criteria.md` — acceptance criteria / definition of done

## Working agreement for the agent

1. Implement incrementally by phases. Each phase must pass its own acceptance checks before moving on.
2. Keep SQLite compatibility **and** avoid decisions that block an easy future migration to Postgres.
3. Prefer **small, testable** repositories and services, short transactions, clear error types.
4. Avoid storing large blobs in SQLite. Store references (URIs) and small metadata in DB.
5. Alembic migrations are the source of truth for schema changes; never “auto-sync” schema at runtime.
