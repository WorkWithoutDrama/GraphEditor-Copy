# 02 — Phase A: Foundation (engine/session/base/Alembic)

## Goal
Create a working DB backbone: configuration, engine, session management, Base model conventions,
and Alembic fully wired to autogenerate migrations from ORM metadata.

## Deliverables
- `app/db/config.py` (pydantic-settings)
- `app/db/base.py` (Base + mixins)
- `app/db/engine.py` (engine creation + SQLite PRAGMAs)
- `app/db/session.py` (session factories + context managers)
- `alembic` initialized under `app/db/migrations/`
- working `alembic upgrade head` (even if empty)
- tests proving we can connect and execute a trivial query

## Tasks (step-by-step)

### A1 — Add dependencies
1. Add deps to project:
   - SQLAlchemy 2.x (>=2.0,<2.2)
   - Alembic (>=1.18)
   - Pydantic v2 + pydantic-settings
   - pytest
   - pytest-asyncio
   - aiosqlite (async-first)

### A2 — Implement DBConfig (pydantic-settings)
Implement:
- `DBConfig(db_url: str = "sqlite:///./data/app.db", echo_sql: bool = False, pool_pre_ping: bool = True)`
  - **Comment:** `pool_pre_ping` has no effect on SQLite (NullPool); used when migrating to Postgres.
- optional `sqlite_busy_timeout_ms: int = 5000`
- optional `sqlite_journal_mode: str = "WAL"`
- optional `sqlite_synchronous: str = "NORMAL"`
- optional `sqlite_foreign_keys: bool = True`

### A3 — Base + mixins
Implement:
- `Base = DeclarativeBase` (SQLAlchemy 2.0 style) or `declarative_base()`
- mixins:
  - `IdMixin`: `id: Mapped[str]` default uuid4 string
  - `TimestampMixin`: `created_at`, `updated_at` — use UTC; consider `UTCDateTime` TypeDecorator (see Phase F) or ensure `datetime.utcnow` / `func.datetime('now')` semantics are UTC.
- naming conventions for constraints/indexes (use metadata naming convention) to keep Alembic diffs stable

### A4 — Engine with SQLite PRAGMAs
Implement `create_engine_from_config(cfg: DBConfig)` (sync) and `create_async_engine_from_config(cfg: DBConfig)` (async; use `sqlite+aiosqlite` for SQLite).

For SQLite (Python 3.14):
- `connect_args={"autocommit": False}` — ensures proper SERIALIZABLE transaction semantics (legacy mode disabled).
- On connect, execute PRAGMAs via `@event.listens_for(engine, "connect")`:
  - `PRAGMA foreign_keys=ON;`
  - `PRAGMA journal_mode=WAL;`
  - `PRAGMA synchronous=NORMAL;`
  - `PRAGMA busy_timeout=5000;` (configurable)

Notes:
- Use SQLAlchemy event for PRAGMAs.
- Keep PRAGMAs configurable (via DBConfig).

### A5 — Session factory + context manager (async-first)
Implement:
- **Primary:** `AsyncSessionLocal` (async engine) and `async_session_scope()` — yields session, commit on success, rollback + re-raise on exception, close always.
- **Sync fallback:** `SessionLocal` and `session_scope()` if needed.

Session config:
- `autoflush=True` (default) — correctness; fewer subtle bugs.
- `expire_on_commit=True` (default).

**Critical:** Repositories must call `session.flush()` (or `await session.flush()`) explicitly when they need DB-generated values (server defaults) or when subsequent queries depend on newly inserted rows.

### A6 — Alembic init and wiring
1. Initialize alembic in `app/db/migrations/`
2. Configure `alembic.ini` (or programmatic config)
3. In `env.py`:
   - set `target_metadata = Base.metadata`
   - import `app.db.models` so all tables are registered
   - for SQLite, set `render_as_batch=True` in `context.configure()`

### A7 — Tests
Create tests:
- `test_db_can_connect_and_select_1`
- `test_session_scope_commits_and_rolls_back`

Use a temporary SQLite file per test (or `sqlite+pysqlite:///:memory:` with caution; file is more realistic for WAL).

## Acceptance checks
- `pytest` passes
- `alembic revision --autogenerate -m "init"` produces a revision (even empty)
- `alembic upgrade head` succeeds
- DB PRAGMAs are applied (verify by querying PRAGMA values in test)

## Pitfalls to avoid
- Forgetting to import models into Alembic env → missing tables in autogenerate
- Long-lived sessions → SQLite locked errors
- Using SQLite in-memory with multiple connections → tables disappear; prefer temp file for integration tests
