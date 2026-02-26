# Critical Review: LLM Module Implementation Plan

**Reviewed:** 2026-02-17  
**Scope:** `llm_module_plan/` (Index + Phases A–H)

---

## Executive Summary

The plan is **well-structured** and aligns with the project’s existing patterns (ports, settings, persistence, observability). It delivers a single typed async LLM interface with LiteLLM, Ollama, and Gemini, plus routing, guardrails, SQL persistence, and optional PydanticAI integration. Several details are underspecified or inconsistent with the written layout, and a few integration points with the rest of the app need to be made explicit. **Recommendation:** treat the plan as the main design spec and apply the clarifications and fixes below before implementation so the module fits cleanly into the current codebase and conventions.

---

## 1. Strengths

### 1.1 Architecture and boundaries

- **Single entrypoint rule** (“other modules never call LiteLLM or provider SDKs directly”) is clear and testable. The split between `LLMClientPort` (low-level) and `LLMService` (routing, persistence, policy) matches the docling-style separation of ports vs orchestration.
- **Folder layout** is coherent: `types`, `errors`, `ports`, `router`, `client_litellm`, `providers/`, `persistence/`, `pydanticai/`, `telemetry` keep the public surface small and make it obvious where to add new providers or persistence logic.
- **Phasing (A→H)** is logical: contracts → settings → LiteLLM wrapper → providers → persistence → PydanticAI → tests → ops. Dependencies between phases are respected.

### 1.2 Contracts and typing

- **Phase A** defines a rich but focused set of types: `LLMProvider`, `LLMProfile`, `LLMMessage`, `LLMRequest` (with `idempotency_key`, `metadata`, `timeout_s`), `LLMResponse`, `LLMUsage`, `LLMConstraints`. That is enough for router logic and persistence without leaking provider details.
- **Error taxonomy** (`LLMError` + concrete subclasses with `code`, `retryable`, `provider`) supports both runbook actions and SQL `error_code` storage. Mapping “original exception class name” into `details` without leaking secrets is a good balance.
- **Public API** is intentionally small: `chat()`, optional `chat_json()`, optional `stream_chat()`. Keeping streaming and structured output as optional/Phase F keeps the first delivery scope manageable.

### 1.3 Guardrails and operations

- **Concurrency (Semaphore), timeouts, retries with backoff** are specified in one place (LiteLLM client wrapper). The note about not double-retrying with provider SDK retries is important for predictable behavior.
- **Param dropping** (`drop_unsupported_params` → LiteLLM `drop_params=True`) is a practical way to keep multi-provider routing safe when Ollama and Gemini support different options.
- **Redaction policy** (Phase E4): store hashes by default, optional previews after redaction. This matches privacy-sensitive production use.
- **Runbook (Phase H4)** lists concrete failure types and standard actions (router_policy, concurrency, timeout, `llm_runs` inspection). That is directly actionable for ops.

### 1.4 Alignment with existing modules

- **Settings:** Pydantic `BaseSettings` with env prefix and validation mirrors `VectorStoreSettings` and the described docling/config style.
- **Persistence:** `llm_runs` with status, usage, latency, error_code, and repo methods (`create_started`, `mark_succeeded`, `mark_failed`, cache get/set) mirrors the docling “run FSM + stage logs” and SQL repo patterns.
- **Ports:** `LLMClientPort` and repository interfaces allow tests to mock the client and DB without touching LiteLLM or real APIs.
- **Dependency injection:** “Agents receive `LLMService` via dependencies” (Phase F4) is consistent with how docling services receive repo and store ports.

### 1.5 Documentation and acceptance criteria

- Each phase ends with **Acceptance criteria**, which gives a clear Definition of Done.
- Index **Definition of Done** is concrete: `chat()` with Ollama and Gemini, runs in SQL, concurrency/timeout/retry tested, router behavior, PydanticAI adapter for at least one use-case.

---

## 2. Gaps and Inconsistencies

### 2.1 Missing `service.py` in folder layout

**Index (folder layout):** Lists `router.py`, `client_litellm.py`, `ports.py`, etc., but **no `service.py`**.

**Phase A4:** Says public methods live in `app/llm/service.py` (or `router.py` + `service.py`).

**Impact:** Implementers may put everything in `router.py` or create `service.py` ad hoc. The plan does not state whether `LLMService` lives in `service.py` or `router.py`.

**Recommendation:** Add `service.py` to the folder layout and state explicitly: “`LLMService` in `service.py` orchestrates router, persistence, and policy; `router.py` holds routing logic and provider capability matrix.”

### 2.2 Persistence: UoW and DB session ownership

**Phase E2:** Repo methods `create_started`, `mark_succeeded`, `mark_failed`, `get_cached`, `set_cached` are defined; it says “commit boundaries controlled by caller UoW (align with SQL module conventions).”

**Gap:** The plan does not specify:
- Who creates the UoW/session (e.g. HTTP request scope, background job scope).
- Whether `LLMService` receives a repo that already has a session (like docling adapters) or creates its own.
- How `LLMService.chat()` gets `workspace_id` and optional `pipeline_run_id` for `llm_runs` (from `LLMRequest.metadata`? from a shared context?).

**Impact:** Without this, persistence may be implemented with a new session per call or with unclear transaction boundaries, and multi-tenant fields (`workspace_id`) may be missing or inconsistent.

**Recommendation:** Add a short “Persistence integration” subsection: (1) `LLMService` receives an `LLMRunRepoPort` (or equivalent) that is bound to a session/UoW provided by the caller. (2) `workspace_id` and `pipeline_run_id` are taken from `req.metadata` (e.g. `metadata["workspace_id"]`, `metadata["pipeline_run_id"]`) with a clear default if absent. (3) Repo methods do not commit; the caller commits after `chat()` returns.

### 2.3 Schema and migrations for `llm_runs`

**Phase E1:** Columns and indexes for `llm_runs` are listed in prose; there is no mention of Alembic or the existing DB migration flow.

**Current project:** Contains `alembic.ini` and likely `app/db/`-style models and migrations.

**Impact:** The plan does not say where `llm_runs` lives (same DB as documents/chunks? same migration tree?) or who owns the migration. This can lead to ad hoc tables or duplicate migration patterns.

**Recommendation:** State that `llm_runs` is added via the project’s existing Alembic workflow, and that the model lives in `app/llm/persistence/models.py` but is registered with the same metadata/base as the rest of the app (or explicitly describe a separate metadata if intentional). Optionally reference “match project standard” from Phase G4.

### 2.4 `workspace_id` and multi-tenancy

**Phase E1:** `workspace_id` is listed as a column “if your app is multi-tenant.”

**Gap:** The plan does not define how `workspace_id` is supplied (e.g. always from `LLMRequest.metadata`, or from a request-scoped context). Docling uses `workspace_id` in run tracking; the LLM plan does not tie `workspace_id` to the request contract.

**Impact:** Implementers may add the column but leave it null, or invent different ways to pass it, reducing consistency with docling and reporting.

**Recommendation:** Decide and document: either (1) `workspace_id` is required and comes from `req.metadata["workspace_id"]` (and validation fails if missing when persistence is enabled), or (2) the app is single-tenant and `workspace_id` is optional/null for now, with a short note in the plan.

### 2.5 Settings: env prefix and naming

**Phase B:** Fields like `ollama_api_base`, `gemini_api_key`, `default_profile` are defined but **no `env_prefix`** (e.g. `LLM_`) is specified.

**Current app:** e.g. `VectorStoreSettings` uses `env_prefix="QDRANT_"`.

**Impact:** Without a prefix, vars like `default_profile` or `concurrency_limit` might collide with other components. `GEMINI_API_KEY` is a common name; the plan already uses it. Clarifying prefix for all other LLM settings avoids collisions.

**Recommendation:** In Phase B1, add `model_config = SettingsConfigDict(env_prefix="LLM_", ...)` and document the resulting env vars (e.g. `LLM_DEFAULT_PROFILE`, `LLM_CONCURRENCY_LIMIT`, `LLM_OLLAMA_API_BASE`). Explicitly state that `GEMINI_API_KEY` remains as-is for compatibility (or rename to `LLM_GEMINI_API_KEY` and document the change).

### 2.6 Router: where capability matrix and profile mapping live

**Phase D3:** “In `app/llm/router.py`, define provider capabilities (supports_tools, supports_json_schema, max_context_tokens).”

**Gap:** The index does not define a separate “router” type; it only lists `router.py`. Phase A says “router selects provider based on profile + request constraints.” It is unclear whether:
- The router is a class (e.g. `LLMRouter`) that holds the capability matrix and is used by `LLMService`, or
- A set of pure functions in `router.py`.

**Impact:** Testability and DI are clearer if the router is an injectable object. The plan stays implementation-agnostic but leaves this open.

**Recommendation:** Specify that routing is implemented as a dedicated type (e.g. `LLMRouter` in `router.py`) with a method like `select_provider(req: LLMRequest, constraints: LLMConstraints) -> LLMProvider`, and that the capability matrix is either on the router or on a small `capabilities.py`/config used by the router. This makes Phase G1 “router selection” tests unambiguous.

### 2.7 Idempotency key and cache key semantics

**Phase A2:** `LLMRequest` has `idempotency_key: str | None`.  
**Phase E2:** Cache is keyed by `prompt_sha256`, `model`, `profile`, and TTL.

**Gap:** The relationship between `idempotency_key` and cache key is not defined. For example: if the caller sends `idempotency_key="run-123"`, should the cache lookup use (1) only `prompt_sha256 + model + profile`, or (2) `idempotency_key` when present and fallback to prompt hash otherwise? If (2), the repo contract should include “get by idempotency_key” for exact replay.

**Impact:** Without this, “idempotency” might mean “same run” while “cache” means “same prompt”; duplicate runs with the same idempotency key could still hit the backend if cache key is only prompt-based.

**Recommendation:** In Phase E2/E3, specify: when `cache_enabled` and `idempotency_key` is set, first try cache/get by `idempotency_key`; then by `(prompt_sha256, model, profile)`; and when storing, always store under both if idempotency_key is present. Alternatively, state explicitly that idempotency is for persistence deduplication only and cache is purely content-addressed (and document that as a design choice).

### 2.8 PydanticAI: streaming and tool calls

**Phase F2:** Adapter must “return response in the shape PydanticAI expects (text, tool calls, etc.)” and “for structured output use PydanticAI’s schema extraction flow.”

**Gap:** Phase A4 lists `stream_chat` as optional and Phase F mentions “PydanticAI supports streaming.” The plan does not say whether the first version of the PydanticAI adapter must support streaming or only sync-style completion. If the adapter only supports non-streaming, document that and add “streaming” as a later extension.

**Impact:** Scope creep or under-specification for PydanticAI integration.

**Recommendation:** In Phase F, state explicitly: “First version of `PydanticAiLiteLLMModel` supports only non-streaming completion; streaming can be added in a later phase.” If tool calls are in scope for “interest extraction” or similar, add a one-line note that the adapter maps `LLMRequest.tools` through to the underlying `chat()` and that PydanticAI tool-call parsing is supported for that path.

### 2.9 Gemini: setting env in adapter vs settings

**Phase D2:** “Ensure env var is set: `os.environ['GEMINI_API_KEY'] = settings.gemini_api_key.get_secret_value()`.”

**Concern:** Mutating `os.environ` in an adapter can have side effects (e.g. other code that reads `GEMINI_API_KEY` later, or multiple workers). LiteLLM often supports passing the API key in the call kwargs or via a dedicated config.

**Recommendation:** Prefer passing the key in the request/config to LiteLLM (e.g. `api_key=settings.gemini_api_key.get_secret_value()`) instead of setting `os.environ` in the adapter, unless LiteLLM’s Gemini integration requires the env var. If it does, document that and restrict the set to a single place (e.g. at app startup in a dedicated “secrets bootstrap”) rather than per request in the adapter.

### 2.10 Telemetry module name and placement

**Index:** Lists `telemetry.py` under `app/llm/`.  
**Phase B2:** “Add redaction helper in `app/llm/telemetry.py`.”  
**Phase H1–H2:** Structured logging and Prometheus metrics are described but not explicitly assigned to `telemetry.py`.

**Impact:** Redaction, logging, and metrics could end up split across `client_litellm`, `service`, and `telemetry` without a clear contract.

**Recommendation:** State that `telemetry.py` provides: (1) redaction helpers (no secrets in logs), (2) structured log fields for each call (as in H1), and (3) metric emission (H2) if the project has a common metrics registry. The LiteLLM client and service then call into `telemetry` rather than embedding log/metric logic.

---

## 3. Risks and Ambiguities

### 3.1 LiteLLM version and API stability

The plan assumes “SDK mode” with `litellm.acompletion()` and does not pin a LiteLLM version. LiteLLM’s API and exception hierarchy can change between versions.

**Recommendation:** Add to Phase C or to a “Dependencies” section: pin `litellm` in `requirements.txt` and document the minimum version. In Phase C5, list the concrete exception classes used for mapping (e.g. `litellm.exceptions.Timeout`, rate limit, auth) so that future upgrades can be checked against this list.

### 3.2 Cost and token counting

**Phase A2:** `LLMUsage` has optional `cost_usd`. **Phase E1:** `cost_usd` is optional on `llm_runs`. **Phase H3:** “Use LiteLLM’s pricing info if available (or store tokens only).”

The plan does not specify who computes cost (LiteLLM, a separate pricing table, or not at all in v1). If cost is optional and not implemented initially, that is fine but should be explicit.

**Recommendation:** State that v1 stores `input_tokens`, `output_tokens`, `total_tokens` from the provider response; `cost_usd` is optional and can be filled by a post-processing step or a small pricing table later. That keeps Phase E and H3 consistent.

### 3.3 Tool calls and JSON schema support

**Phase A2:** `LLMRequest` has `tools: list[dict] | None` and `response_format: dict | None`. **Phase D3:** Router uses `requires_tools` and `requires_json` for routing.

The plan does not specify how `tools` and `response_format` are passed through the LiteLLM client (e.g. which LiteLLM parameter names) or how partial support on Ollama is handled (e.g. “best effort” vs hard failure). This is acceptable as implementation detail but could cause rework if assumptions differ.

**Recommendation:** In Phase C3, add one sentence: “Map `req.tools` and `req.response_format` to the LiteLLM kwargs expected by each provider (e.g. OpenAI-style `tools` / `response_format`).” In Phase D3, clarify that when routing to Ollama with `requires_tools=True`, the behavior is “best effort” and may raise or fallback if the model does not support tools (and document the fallback behavior).

### 3.4 Test coverage and “minimal coverage threshold”

**Phase G4:** “Enforce minimal coverage threshold (match project standard).”

The project standard is not stated. Without a number or reference to an existing config (e.g. pytest-cov in `pytest.ini`), “minimal” is vague.

**Recommendation:** Either reference an existing pytest/cov config (e.g. “match `tests/` conftest or pytest.ini”) or add a concrete value (e.g. “≥ 80% for `app/llm/`”) and note that it can be adjusted to match the rest of the app.

---

## 4. Recommendations Summary

| Area | Action |
|------|--------|
| **Layout** | Add `service.py` to folder layout; state that `LLMService` lives there and uses `router.py` for routing. |
| **Persistence** | Document UoW/session ownership, and that `workspace_id` / `pipeline_run_id` come from `req.metadata`; repo does not commit. |
| **DB** | Align `llm_runs` with existing Alembic and model placement. |
| **Multi-tenant** | Define how `workspace_id` is supplied (e.g. required in `metadata` when persist is on). |
| **Settings** | Add `env_prefix="LLM_"` and document env vars; clarify `GEMINI_API_KEY` handling. |
| **Router** | Define `LLMRouter` (or equivalent) and where capability matrix lives. |
| **Cache vs idempotency** | Define how `idempotency_key` interacts with cache key and repo methods. |
| **PydanticAI** | State that v1 adapter is non-streaming; clarify tool-call path if in scope. |
| **Gemini** | Prefer passing API key in kwargs; if env is required, centralize in one place. |
| **Telemetry** | Assign redaction, structured logging, and metrics to `telemetry.py` and document the contract. |
| **LiteLLM** | Pin version; document exception classes used in Phase C5. |
| **Cost** | State that v1 focuses on token counts; `cost_usd` is optional and can be added later. |
| **Tests** | Reference or set a concrete coverage threshold for `app/llm/`. |

---

## 5. Conclusion

The LLM module plan is **suitable for implementation** with the above clarifications. Its strengths are a clear public API, strong alignment with existing ports/settings/persistence patterns, and sensible guardrails and ops guidance. Addressing the missing file in the layout, persistence/session/workspace contract, settings prefix, router and cache semantics, and the smaller points (telemetry, Gemini env, coverage) will reduce rework and keep the module consistent with the rest of the application. Applying the “integration addendum” style used in the docling critique will make the LLM plan ready for direct implementation and code review.
