# LLM Module Plan — Critique Addressed (Single Spec Addendum)

**Date:** 2026-02-17  
**Input critique:** `CRITIQUE.md` fileciteturn0file0  
**Scope:** Applies to `llm_module_plan/` Phases A–H.

This document **patches and clarifies** the original LLM module implementation plan so it fits the current project conventions (ports/UoW/migrations/settings prefixes) and removes underspecified parts.

---

## 0) Executive changes (what you should implement)

1. **Add `service.py`** to the module and make it the only public orchestrator entrypoint (router + persistence + policy).
2. **Define UoW/session ownership** explicitly: `LLMService` uses repos bound to the caller’s UoW; it never creates/commits sessions.
3. **Add Alembic migration** for `llm_runs` in the existing migration tree; register LLM models under the same SQLAlchemy Base/metadata.
4. **Make `workspace_id` contract explicit** (from request-scoped context or `LLMRequest.metadata`) and validate when persistence is enabled.
5. **Settings get `env_prefix="LLM_"`** (except Gemini key if you keep `GEMINI_API_KEY` for compatibility).
6. **Make router a first-class injectable object** (`LLMRouter`) with a capability matrix and deterministic selection/fallback.
7. **Define idempotency vs cache semantics** (and implement repo lookups for idempotency key if caching/dedup are enabled).
8. **PydanticAI adapter v1 is non-streaming**; streaming becomes a later extension.
9. **Gemini key handling is centralized** (prefer passing `api_key=`; if env is required, set once at app bootstrap, not per request).
10. **Telemetry contract** consolidated into `telemetry.py` (redaction + structured logs + metrics).
11. **Pin LiteLLM version** and document the exception classes used in error mapping.
12. **Cost tracking** is token-only in v1; `cost_usd` is optional and filled later.
13. **Tests include a concrete coverage gate** for `app/llm/`.

Everything below gives the precise spec edits needed.

---

## 1) Folder layout correction: add `service.py`

### Updated module layout

```text
app/
  llm/
    __init__.py
    settings.py
    types.py
    errors.py
    ports.py
    service.py          # ✅ NEW: orchestration entrypoint
    router.py           # routing policy + capability matrix + fallbacks
    client_litellm.py   # LiteLLM wrapper (timeouts/retries/semaphore)
    providers/
      __init__.py
      ollama.py
      gemini.py
    persistence/
      __init__.py
      models.py
      repo.py
    pydanticai/
      __init__.py
      model.py
    telemetry.py
    tests/
      ...
```

### Ownership rules (explicit)
- `service.py` contains **`LLMService`** and is the **only** class other modules import/use.
- `router.py` contains **`LLMRouter`** (injectable) + capability matrix + deterministic selection/fallback.
- `client_litellm.py` contains **`LiteLLMClient`** (infrastructure adapter: timeout/retry/sem + normalization).
- `providers/*` only translate settings → provider call kwargs and define provider capabilities; they do not do routing.

---

## 2) Persistence integration: UoW/session ownership + required metadata

### 2.1 Session/UoW ownership (must match existing DB conventions)

**Decision:** `LLMService` does **not** create sessions and does **not** commit.  
It receives repo ports that are already bound to the active UoW/session.

**Pattern (consistent with existing modules):**
- HTTP request handler / background job opens a UoW:
  - Provides `LLMRunRepo` (and other repos) using that session.
  - Calls `await llm_service.chat(...)`
  - Commits/rollbacks at the end of the request/job boundary.

### 2.2 Where `workspace_id` and correlation IDs come from

**Decision:** When `persist_runs=True`, the following fields are required **by contract**:

- `workspace_id`: supplied by either:
  1) a request-scoped context object (preferred), or  
  2) `req.metadata["workspace_id"]`

Additionally recommended (optional but strongly encouraged):
- `pipeline_run_id`: `req.metadata["pipeline_run_id"]`
- `stage`: `req.metadata["stage"]` (string enum used across pipelines)

### 2.3 Validation behavior
- If `persist_runs=True` and `workspace_id` is missing → raise a **configuration/contract error** at runtime with a clear message (fail fast), OR enforce at construction-time of the service if you have a typed context object.
- If `persist_runs=False`, `workspace_id` may be absent.

### 2.4 Transaction boundaries in `LLMService.chat()`
- `create_started(...)` is called inside the active session but does not commit.
- `mark_succeeded/mark_failed(...)` update the same row inside the same session; no commit.
- The caller commits once per outer unit-of-work.

---

## 3) DB schema + migrations: align with existing Alembic workflow

### 3.1 Single DB, same metadata/base
- `app/llm/persistence/models.py` must use the **same SQLAlchemy Base/metadata** as the rest of the application.
- Do **not** introduce a new metadata unless the project already does so for other modules.

### 3.2 Alembic migration is mandatory
Add a migration in the **existing** Alembic tree that:
- creates `llm_runs`
- adds indexes and any constraints

### 3.3 Practical schema notes (SQLite + portability)
- Unique nullable `idempotency_key`:
  - If you need “unique when not null” behavior on SQLite, implement it carefully:
    - SQLite allows multiple NULLs under a UNIQUE constraint, so a simple UNIQUE index is acceptable.
- JSON column types:
  - Prefer TEXT with JSON serialization if you already do that elsewhere, or use SQLAlchemy JSON type if the project has it.
- Index choices:
  - `(workspace_id, created_at)`
  - `(pipeline_run_id)`
  - `idempotency_key` unique index
  - `prompt_sha256` if caching is enabled

---

## 4) Multi-tenancy: decide and document now

Pick one and encode it in validation + docs:

### Option A (recommended): multi-tenant-ready now
- `workspace_id` is required whenever persistence is enabled.
- `LLMRequest.metadata` reserves keys: `workspace_id`, `pipeline_run_id`, `stage`.

### Option B: single-tenant for now
- `workspace_id` column exists but nullable
- persistence does not enforce it
- add TODO: enforce once multi-tenant is introduced

**This addendum assumes Option A** because your other pipelines already benefit from correlated run tracking.

---

## 5) Settings: add env prefix and document environment variables

### 5.1 Add `env_prefix="LLM_"` (Pydantic settings)
In `LLMSettings`, add:
- `model_config = SettingsConfigDict(env_prefix="LLM_", ...)`

### 5.2 Env var mapping examples
- `LLM_DEFAULT_PROFILE`
- `LLM_CONCURRENCY_LIMIT`
- `LLM_DEFAULT_TIMEOUT_S`
- `LLM_OLLAMA_API_BASE`
- `LLM_OLLAMA_MODEL`
- `LLM_GEMINI_MODEL`
- `LLM_PERSIST_RUNS`
- `LLM_CACHE_ENABLED`

### 5.3 Gemini key naming
Two acceptable patterns — choose and freeze:

**Pattern 1 (compatibility):** keep `GEMINI_API_KEY` as the real secret input, do not duplicate it.  
**Pattern 2 (namespaced):** use `LLM_GEMINI_API_KEY` and configure LiteLLM with `api_key=` explicitly.

This addendum recommends **Pattern 2** for avoiding collisions, but if you already standardize on `GEMINI_API_KEY`, keep it and just document the exception.

---

## 6) Router spec: make it a class (`LLMRouter`) with explicit capability matrix

### 6.1 Router as an injectable object
In `router.py` implement:

- `class LLMRouter:`
  - `def select_provider(self, req: LLMRequest, constraints: LLMConstraints) -> LLMProvider`
  - `async def execute(self, req: LLMRequest) -> LLMResponse` (optional convenience that handles fallback loop)

### 6.2 Capability matrix location
Keep capability definitions in one place:
- either inside `LLMRouter` constructor, or
- in `router.py` as `PROVIDER_CAPABILITIES: dict[LLMProvider, ProviderCaps]`

`ProviderCaps` includes:
- `supports_tools: bool`
- `supports_json: bool`
- `max_context_tokens: int | None`
- `preferred_for_profiles: set[LLMProfile]` (optional)

### 6.3 Deterministic fallback policy
Document and implement:
- prefer provider per `profile` and `settings.router_policy`
- if first provider fails with **retryable** error and fallbacks allowed → try next provider once (or per list)
- never fallback on non-retryable errors (bad request/auth)

---

## 7) Idempotency key vs cache semantics (define exact behavior)

### 7.1 Definitions
- **Idempotency:** “I want the same *logical call* not to be executed twice.”  
- **Cache:** “If inputs are identical, reuse result.”

### 7.2 Required semantics (recommended)
If `req.idempotency_key` is present:
1. Check `llm_runs` for an existing **SUCCEEDED** run with that idempotency_key:
   - if found → return the stored response (or cached response payload)
2. If not found:
   - proceed with normal execution and store run using that idempotency_key
3. If a run exists with `STARTED` for the same key:
   - either (a) return “in-progress” error, or (b) wait/poll — **choose one** (v1: return a clear error)

If cache is enabled (content-addressed):
- Compute `prompt_sha256` over a stable canonical form of:
  - messages (roles + content)
  - model/profile
  - temperature/max_output_tokens/tools/response_format (anything that changes output)
- Cache key = `(prompt_sha256, model, profile)` with TTL.
- When idempotency_key is present, store/lookup under both:
  - `idempotency_key` (exact replay)
  - `prompt_sha256` (content cache)

### 7.3 Repo port updates
Add repo methods explicitly:
- `get_by_idempotency_key(key) -> Optional[StoredLLMResult]`
- `save_result_for_idempotency_key(key, result)`

---

## 8) PydanticAI integration scope: v1 is non-streaming

### 8.1 Explicit scope
- `PydanticAiLiteLLMModel` supports **non-streaming completion only** in v1.
- Streaming (`stream_chat`) is deferred to a later phase once core routing+persistence is stable.

### 8.2 Tool calls (if used)
If a PydanticAI agent uses tool calls:
- Ensure adapter maps tool specifications to `LLMRequest.tools`
- Ensure `LLMService.chat()` passes `tools` through to LiteLLM
- Ensure router routes tool-call-required requests to the provider that supports it (Gemini by default)

If tool calls are not in v1 scope, state: “v1 adapter ignores tool calls; add later.”

---

## 9) Gemini API key handling: no per-request env mutation

### 9.1 Preferred approach: pass key explicitly
In provider kwargs for Gemini, prefer:
- `api_key=settings.gemini_api_key.get_secret_value()`

### 9.2 If LiteLLM requires env var
If you must use env vars for LiteLLM Gemini:
- set it once in an **app bootstrap** step (startup hook), not inside the adapter:
  - `bootstrap_llm_secrets(settings)` sets env var exactly once
- adapter never mutates process env.

This avoids side effects across workers and makes behavior deterministic.

---

## 10) Telemetry contract: consolidate in `telemetry.py`

### 10.1 `telemetry.py` responsibilities (explicit)
1. **Redaction helpers**
   - redact secrets and PII from any stored/logged preview
2. **Structured log emission**
   - standard set of fields (llm_run_id, workspace_id, provider, model, profile, stage, status, latency_ms, error_code)
3. **Metrics emission**
   - counters/histograms as described in Phase H2

### 10.2 Usage rule
- `LLMService` and `LiteLLMClient` call telemetry helpers; they do not embed ad hoc log/metric code.

---

## 11) LiteLLM version pin + exception mapping stability

### 11.1 Pin version
- Pin LiteLLM to a known-good version in your dependency management (requirements/uv/poetry).
- Document the minimum/locked version in `app/llm/README.md` or in the phase docs.

### 11.2 Exception mapping list
In Phase C5, list concrete exception classes you map (by name) and add a test that asserts:
- “these exception names are recognized”
- “unknown exceptions map to LLMUnavailable or LLMError(UNKNOWN)”

This makes upgrades safer and reviewable.

---

## 12) Cost and token counting: explicit v1 behavior

### 12.1 v1 scope
- Persist token counts (`input_tokens`, `output_tokens`, `total_tokens`) when provided by the backend.
- `cost_usd` remains **NULL** in v1 unless LiteLLM returns it reliably in the response.

### 12.2 Later extension
- Add a post-processing step (daily aggregation job) to compute cost from:
  - provider/model pricing table
  - token usage

---

## 13) Tests: define concrete coverage gate

### 13.1 Coverage gate
Set a concrete number for `app/llm/` (example):
- **≥ 80% line coverage** for `app/llm/` in CI

If the repo already has a standard threshold, reference that file/config instead (pytest.ini/pyproject).

### 13.2 Router + idempotency tests must exist
Minimum required tests:
- Router selection + fallback on retryable error
- Idempotency key “replay” path
- Cache key canonicalization and TTL behavior (if cache enabled)

---

## 14) Updated “Definition of Done” (revised)

- ✅ `LLMService` exists in `service.py` and is the only public entrypoint
- ✅ Repos are session-bound via caller UoW; service never commits
- ✅ `llm_runs` table created via Alembic migration in existing tree
- ✅ `workspace_id` contract enforced when persistence enabled
- ✅ Settings use `LLM_` env prefix (Gemini key strategy documented)
- ✅ `LLMRouter` is an injectable object with capability matrix + deterministic fallback
- ✅ Idempotency + cache semantics are implemented as specified
- ✅ PydanticAI adapter works (non-streaming) for one structured-output use-case
- ✅ LiteLLM version pinned; exception mapping tested
- ✅ Token usage persisted; cost optional (v1 token-only is OK)
- ✅ Coverage gate for `app/llm/` is defined and met

---

## Appendix: Critique reference

This addendum addresses all points raised in `CRITIQUE.md`. fileciteturn0file0
