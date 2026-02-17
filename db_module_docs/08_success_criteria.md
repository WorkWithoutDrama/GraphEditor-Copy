# 08 — Success criteria (Definition of Done)

This file lists objective criteria that determine whether the DB module is “done” and robust enough to support the pipeline.

## 1) Functional completeness

### Schema coverage
- [ ] Core lineage tables exist and are migrated via Alembic:
  - workspaces, sources, source_versions, documents
- [ ] Chunking tables exist:
  - chunks
- [ ] Embedding pointer tables exist:
  - embedding_sets, chunk_embeddings
- [ ] Observability tables exist:
  - runs, run_items, events
- [ ] (Optional) query logging tables exist:
  - queries, query_results

### Repository + service coverage
- [ ] Repositories implement required CRUD + idempotent create/get patterns
- [ ] Thin services exist to persist chunks and embedding references

## 2) Idempotency & integrity

- [ ] Ingesting the same content hash twice does not create duplicate SourceVersion records
- [ ] Creating the same Document extraction record twice (same version + extractor + extractor_version) is idempotent
- [ ] Persisting the same chunk payloads twice does not create duplicate Chunk rows
- [ ] Persisting embedding pointers twice does not create duplicates for (chunk_id, embedding_set_id)
- [ ] Foreign keys enforce correct deletion behavior (cascades) where intended
- [ ] Uniqueness constraints are present and tested

## 3) Migrations & reproducibility

- [ ] `alembic upgrade head` works on a fresh database
- [ ] `alembic downgrade -1` works for the latest migration (at least for non-destructive steps)
- [ ] Autogenerate is wired correctly: new models appear in migration diffs
- [ ] Constraint naming conventions prevent noisy diffs

## 4) SQLite operational robustness

- [ ] PRAGMAs are set on connect:
  - foreign_keys=ON, journal_mode=WAL, synchronous=NORMAL, busy_timeout configured
- [ ] The code uses short-lived sessions and transaction scopes
- [ ] Basic concurrent access smoke test passes (no frequent “database is locked” errors)

## 5) Test suite

Minimum tests required:
- [ ] Foundation: connection + session_scope commit/rollback + PRAGMA verification
- [ ] Core lineage: create workspace/source/version/document; dedupe tests
- [ ] Chunks/embeddings: idempotent chunk insertion + embedding pointer uniqueness
- [ ] Runs/events: run lifecycle + events append + failure recording
- [ ] (Optional) query logging: store query + results; uniqueness rank

## 6) Observability

- [ ] Each pipeline stage can write events without large overhead
- [ ] Failures are represented consistently:
  - run.status=failed
  - run_item.status=failed with an error_message
  - event level=error present with payload pointing to details

## 7) Developer ergonomics

- [ ] Clear module docs and file structure
- [ ] Simple entrypoints:
  - create engine/session
  - run migrations
  - basic admin utilities (dev-only)
- [ ] Lint/type hints in ORM + repos sufficient for agent-assisted maintenance

## 8) Future readiness (Postgres)

- [ ] No SQLite-only SQL patterns that block porting
- [ ] Types are portable (TEXT/INTEGER/REAL; JSON stored as TEXT)
- [ ] Enums stored as TEXT
- [ ] Primary keys are UUID/ULID strings

---

## Final “done” gate

The DB module is considered complete when:
- all non-optional criteria above are checked,
- CI runs migrations from scratch + runs tests successfully,
- and a sample end-to-end run (ingest → extract → chunk → embed) produces consistent DB records across repeated executions.
