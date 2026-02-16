# LLM Module — Implementation Plan (LiteLLM + Ollama + Gemini)

**Goal:** add a production-ready `llm` module that provides a **single, typed, async** interface for all LLM calls in the app, with:
- Provider implementations: **local Ollama** + **Google Gemini (AI Studio)** via LiteLLM
- Routing profiles (e.g., “local-fast”, “cloud-quality”)
- Guardrails: timeouts, retries, concurrency limits, request normalization
- Observability + persistence to SQL (runs, usage, error codes) aligned with existing DB conventions
- Optional structured outputs via **PydanticAI** integration

This plan matches the project patterns established for:
- Docling ingest pipeline (FSM/run tracking, structured logs, stages)
- SQL module (repo ports + unit-of-work boundaries)
- Vector/Qdrant module (LLM module does **not** touch vector DB directly; it’s consumed by orchestrators)

---

## Folder layout (proposed)

```
app/
  llm/
    __init__.py
    settings.py
    types.py
    errors.py
    ports.py
    service.py          # orchestration entrypoint (LLMService)
    router.py           # LLMRouter + capability matrix + fallbacks
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
      test_router.py
      test_mapping.py
      test_ollama_smoke.py
      test_gemini_smoke.py
```

**Ownership rules:**
- `service.py` contains **`LLMService`** and is the **only** class other modules import/use.
- `router.py` contains **`LLMRouter`** (injectable) + capability matrix + deterministic selection/fallback.
- `client_litellm.py` contains **`LiteLLMClient`** (timeout/retry/semaphore + normalization).
- `providers/*` only translate settings → provider kwargs and define provider capabilities; they do not do routing.

> Keep the public surface small: everything outside `app/llm/` calls **only** `LLMService` (or `LLMClientPort`) + `LLMProfiles`.

---

## Phases (read in order)

1. **Phase A — Contracts & public API** → `01_phase_A_contracts.md`  
2. **Phase B — Settings & secrets** → `02_phase_B_settings.md`  
3. **Phase C — LiteLLM client wrapper** → `03_phase_C_litellm_wrapper.md`  
4. **Phase D — Providers: Ollama + Gemini** → `04_phase_D_providers.md`  
5. **Phase E — SQL persistence for runs + optional cache** → `05_phase_E_persistence.md`  
6. **Phase F — PydanticAI integration** → `06_phase_F_pydanticai.md`  
7. **Phase G — Tests & quality gates** → `07_phase_G_tests.md`  
8. **Phase H — Ops/telemetry playbook** → `08_phase_H_ops.md`

---

## Definition of Done

- ✅ `LLMService` exists in `service.py` and is the only public entrypoint.
- ✅ `LLMService.chat()` works with local `ollama/*` and `gemini/*` (API key strategy documented in Phase B).
- ✅ Repos are session-bound via caller UoW; service never creates or commits sessions.
- ✅ `llm_runs` table created via Alembic migration in the existing tree; models use same SQLAlchemy Base/metadata.
- ✅ `workspace_id` contract enforced when persistence is enabled (from request context or `req.metadata`).
- ✅ Settings use `LLM_` env prefix (Gemini key strategy documented in Phase B).
- ✅ `LLMRouter` is an injectable object with capability matrix + deterministic fallback.
- ✅ Idempotency + cache semantics implemented as specified in Phase E.
- ✅ Concurrency limit + timeout + retry/backoff implemented and tested.
- ✅ PydanticAI adapter (non-streaming v1) produces structured output for at least one pipeline use-case.
- ✅ LiteLLM version pinned; exception mapping documented and tested.
- ✅ Token usage persisted; `cost_usd` optional (v1 token-only is OK).
- ✅ Coverage gate for `app/llm/` defined and met (see Phase G).
