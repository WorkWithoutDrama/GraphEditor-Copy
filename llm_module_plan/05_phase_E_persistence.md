# Phase E — SQL Persistence: LLM Runs + Optional Cache

This phase mirrors your existing pattern:
- Docling has `extract_runs` FSM + stage logs
- LLM module gets `llm_runs` (auditability, debugging, cost tracking)

**UoW/session ownership:** `LLMService` does **not** create sessions and does **not** commit. It receives repo ports already bound to the caller’s UoW/session. The caller (e.g. HTTP request handler or background job) opens a UoW, provides `LLMRunRepo` (or equivalent) using that session, calls `await llm_service.chat(...)`, and commits or rolls back at the request/job boundary.

---

## E1. Add DB model: `llm_runs`

File: `app/llm/persistence/models.py` (SQLAlchemy)

- Use the **same SQLAlchemy Base/metadata** as the rest of the application. Do not introduce a separate metadata.
- Add the table via an **Alembic migration** in the existing migration tree.

Suggested columns:
- `id` (UUID / BIGINT)
- `created_at`, `updated_at` (UTC)
- `workspace_id` (required when persistence is enabled; see E3 for source)
- `pipeline_run_id` (optional; correlate to ingest/extract runs)
- `stage` (e.g., `INTEREST_EXTRACTION`, `SUMMARY`, `RERANK`; from `req.metadata["stage"]` when provided)
- `provider` (enum)
- `model`
- `profile`
- `status` (enum: `STARTED`, `SUCCEEDED`, `FAILED`)
- `idempotency_key` (unique nullable)
- Request fingerprints:
  - `prompt_sha256` (always)
  - `prompt_preview` (optional; only if `persist_prompt_text=True`, and **redacted**)
- Output:
  - `response_sha256`
  - `response_preview` (optional)
- Usage:
  - `input_tokens`, `output_tokens`, `total_tokens`
  - `cost_usd` (optional; **v1:** leave NULL; persist token counts only; cost can be filled later by aggregation or pricing table)
- Timing:
  - `latency_ms`
- Error:
  - `error_code`
  - `error_message` (short)
  - `error_details_json` (redacted)

Indexes:
- `(workspace_id, created_at)`
- `(pipeline_run_id)`
- `idempotency_key` unique (SQLite: UNIQUE allows multiple NULLs; use unique index)
- `prompt_sha256` (if enabling cache lookups)

For SQLite/portability: use TEXT with JSON serialization for JSON columns if that matches the rest of the app, or SQLAlchemy JSON type if the project uses it.

---

## E2. Repository (ports + adapters)

File: `app/llm/persistence/repo.py`

**Contract:** Repo is bound to the caller’s session; repo methods do **not** commit. Caller commits once per UoW.

Methods:
- `create_started(run: LLMRunStarted) -> run_id`
- `mark_succeeded(run_id, response: LLMResponse, previews...)`
- `mark_failed(run_id, err: LLMError)`
- `get_cached(prompt_sha256, model/profile, ttl_s) -> Optional[LLMResponse]`
- `set_cached(prompt_sha256, model/profile, response, ttl_s)`
- `get_by_idempotency_key(key: str) -> Optional[StoredLLMResult]` (for idempotent replay)
- `save_result_for_idempotency_key(key: str, result: ...)` (store response for replay)

---

## E2b. Where `workspace_id` and correlation IDs come from

When `persist_runs=True`, require by contract:
- **`workspace_id`:** from (1) a request-scoped context object, or (2) `req.metadata["workspace_id"]`. If missing, raise a clear configuration/contract error (fail fast). If `persist_runs=False`, `workspace_id` may be absent.
- **Optional but recommended:** `pipeline_run_id` = `req.metadata["pipeline_run_id"]`, `stage` = `req.metadata["stage"]`.

---

## E3. Service flow with persistence

In `LLMService.chat()`:

1. **Idempotency (when `req.idempotency_key` is set):** Check repo `get_by_idempotency_key(key)`. If a **SUCCEEDED** run exists → return the stored response. If a run exists with **STARTED** for the same key → in v1 return a clear “in-progress” error (no wait/poll).
2. **Cache (when enabled):** Compute `prompt_sha256` over a stable canonical form (messages + model/profile + temperature/max_output_tokens/tools/response_format). Cache key = `(prompt_sha256, model, profile)` with TTL. Check cache; on hit return and record SUCCEEDED_FROM_CACHE (or annotate status). When storing, if idempotency_key is present, store/lookup under both idempotency_key and content key.
3. Build `run_id` and call repo `create_started` (no commit).
4. Call router → provider.
5. On success: repo `mark_succeeded`; set cache if enabled (no commit).
6. On error: map to `LLMError`, repo `mark_failed`, re-raise. Caller commits or rolls back.

---

## E4. Redaction policy

Default behavior:
- Store **hashes only** (`prompt_sha256`, `response_sha256`)
- Store previews only if explicitly enabled and after redaction:
  - remove API keys, tokens, emails, long numbers
  - truncate to N chars

---

**Acceptance criteria (Phase E)**
- Every LLM call produces exactly one `llm_runs` row with consistent status transitions.
- Repos are session-bound; service never commits.
- `workspace_id` is enforced when persistence is enabled.
- Idempotency key replay and cache semantics (including canonical cache key and dual store when idempotency_key is set) are implemented as above.
- Cache (if enabled) reduces repeated identical calls without leaking sensitive text.
- `llm_runs` is added via Alembic in the existing migration tree; models use the same Base/metadata.
