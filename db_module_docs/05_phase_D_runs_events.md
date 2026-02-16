# 05 — Phase D: Runs + Events (pipeline observability)

## Goal
Track pipeline execution in DB so failures are diagnosable and reruns are safe.
This is essential for robust ingestion in production-like environments.

Entities:
- Run
- RunItem
- Event

## Deliverables
- ORM models
- Migration `003_create_runs_events_tables`
- Run tracking repository/service utilities
- Tests: run lifecycle, event append, failure recording

## Schema (recommended)

### runs
- `id` TEXT PK
- `workspace_id` FK → workspaces.id (ON DELETE CASCADE)
- `run_type` TEXT NOT NULL         (ingest/rechunk/reembed/eval/etc.)
- `status` TEXT NOT NULL           (queued/running/succeeded/failed/canceled)
- `trigger` TEXT NOT NULL          (manual/api/schedule)
- `started_at` DATETIME NOT NULL
- `finished_at` DATETIME NULL
- `meta_json` TEXT NULL            (parameters snapshot)

Indexes:
- `(workspace_id, started_at)`
- `status`

### run_items
**Identity:** Current status per (stage + target). Events hold history; run_items is latest state only.

- `id` TEXT PK
- `run_id` FK → runs.id (ON DELETE CASCADE)
- `stage` TEXT NOT NULL          (ingest/extract/chunk/embed)
- `target_type` TEXT NOT NULL    (enum: `source_version` | `document` | `chunk`)
- `target_id` TEXT NOT NULL
- `status` TEXT NOT NULL         (queued/running/succeeded/failed/skipped)
- `error_message` TEXT NULL
- `metrics_json` TEXT NULL
- `created_at`, `updated_at`

Constraints:
- UNIQUE `(run_id, stage, target_type, target_id)`

Indexes:
- `(run_id, stage, status)`

**Validation layer:** Before insert/upsert, validate that `target_id` exists in the table for `target_type` (source_versions/documents/chunks). Document this decision (no FKs for flexibility; validation enforces integrity).

### events
- `id` TEXT PK
- `run_id` FK → runs.id (ON DELETE CASCADE)
- `ts` DATETIME NOT NULL
- `level` TEXT NOT NULL          (info/warn/error)
- `event_type` TEXT NOT NULL     (DOC_INGESTED, CHUNKED, QDRANT_UPSERTED, etc.)
- `payload_json` TEXT NULL
Indexes:
- `(run_id, ts)`
- `(event_type)`

## Tasks (step-by-step)

### D1 — Implement ORM models
Create `app/db/models/run.py` containing Run, RunItem, Event.

### D2 — Migration
Create `003_create_runs_events_tables`.
Verify indexes for common queries:
- recent runs for workspace
- events for a run ordered by ts
- failed items for a run

### D3 — Repositories/utilities
RunRepo
- `start_run(workspace_id, run_type, trigger, meta)`
- `finish_run(run_id)`
- `fail_run(run_id, error_message=None)`

RunItemRepo
- `upsert_item(run_id, stage, target_type, target_id, status, error_message=None, metrics=None)`
  - **Validation layer:** Validate `target_id` exists in the table for `target_type` before upsert.
  - **Upsert:** On conflict `(run_id, stage, target_type, target_id)`, UPDATE `status`, `error_message`, `metrics`, `updated_at`.
  - (SQLite) Use `INSERT ... ON CONFLICT (...) DO UPDATE SET ...`.
  - Keep events append-only for detailed history; run_items is only latest state.

EventRepo
- `append_event(run_id, level, event_type, payload=None)`
- `list_events(run_id, limit=...)`

Implementation notes:
- Run start should be one transaction.
- Event append should be fast; keep payload small.
- For errors, record:
  - run.status=failed
  - run_item.status=failed with error_message
  - event with level=error + payload

### D4 — Tests
- Start run → append events → finish run sets `finished_at`
- Fail run records failure and allows reading event trail
- `run_items` upsert: same (run_id, stage, target_type, target_id) updates existing row (no duplicates)

## Acceptance checks
- Every pipeline stage can log events safely
- Failure state is clearly represented in DB
- Querying recent runs and their last event is efficient

## Pitfalls to avoid
- Storing huge stacktraces unbounded in DB; truncate or store URI to logs
- Writing events inside long transactions; keep event inserts isolated and fast
- Skipping validation layer for target_type/target_id — orphaned refs would break lineage
