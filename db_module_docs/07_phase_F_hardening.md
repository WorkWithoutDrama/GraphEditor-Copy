# 07 — Phase F: Hardening & ergonomics

## Goal
Make the DB module production-robust even on SQLite, and developer-friendly.

## Deliverables
- Improved PRAGMAs and connection behavior
- Better error handling and domain exceptions
- Tooling/CLI helpers (dev-only)
- Migration discipline docs
- CI-friendly tests

## Tasks (step-by-step)

### F1 — Concurrency hardening (SQLite)
- Ensure PRAGMAs are applied on every connection.
- Use WAL mode by default.
- Configure `busy_timeout`.
- Keep transactions short.
- Provide guidance:
  - avoid long-running sessions in web requests
  - do not hold sessions across awaits (async)

### F2 — Error mapping
Implement DB-specific errors:
- `DbError`
- `NotFoundError`
- `ConflictError` (uniqueness violation)
Wrap SQLAlchemy IntegrityError into ConflictError with a helpful message.

### F3 — Deterministic serialization for JSON TEXT columns
- Use `json.dumps(..., ensure_ascii=False, separators=(",", ":"), sort_keys=True)`
- This makes hashes and comparisons stable.

**Datetime handling:** Use UTC everywhere. Implement a custom JSON encoder (or `default` handler) for `datetime`/`date`:
- Serialize as ISO 8601 strings in UTC (e.g. `value.isoformat()` after `value.astimezone(timezone.utc)`).
- Deserialize from ISO strings back to timezone-aware UTC `datetime`.
- For ORM `DateTime` columns: use timezone-aware UTC in Python; store as timezone-naive UTC in DB. Consider a SQLAlchemy `TypeDecorator` (e.g. `UTCDateTime`) that converts on bind/result.

### F4 — Migration discipline
Document and enforce:
- Do not edit old migrations after merge.
- For destructive changes, use: add column → backfill → switch code → drop later.
- **SQLite ALTER:** SQLite has minimal ALTER support. For column changes, wrap in `op.batch_alter_table()`:
  ```python
  with op.batch_alter_table("table_name") as batch_op:
      batch_op.add_column(Column('foo', Integer))
      batch_op.drop_column('bar')
  ```
- In `env.py`, set `render_as_batch=True` in `context.configure()` for SQLite autogenerate.

### F5 — Tooling helpers
Add small scripts (or functions) for:
- printing current migration/head
- dumping table counts
- listing recent runs/events
- dev-only reset DB (dangerous; gate behind env var)

### F6 — Performance sanity checks
- verify critical indexes exist (unit test that inspects indexes)
- avoid unbounded text columns for logs; truncate or store URI

### F7 — Postgres migration readiness
Avoid SQLite-only constructs:
- do not use `INSERT OR REPLACE` semantics that differ from Postgres
- keep types portable (TEXT/INTEGER/REAL)
- store enums as TEXT
- avoid implicit rowid reliance

## Acceptance checks
- Concurrent ingestion with small parallelism does not frequently lock DB (smoke test)
- Conflict errors are readable and actionable
- JSON serialization stable across runs
- Migrations reproducible in CI from scratch
