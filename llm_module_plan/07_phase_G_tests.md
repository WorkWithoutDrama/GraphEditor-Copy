# Phase G — Tests & Quality Gates

## G1. Unit tests (no network)

### Router selection
- `test_router_selects_local_by_default`
- `test_router_forces_cloud_when_requires_json_and_flag_set`
- `test_router_fallbacks_on_retryable_error`

### Mapping & normalization
- request normalization produces stable hashes / idempotency key behavior
- response extraction picks correct text field
- exception mapping produces correct `LLMError.code` and `retryable` flag

### Persistence logic
- `LLMService.chat()` creates run STARTED and transitions to SUCCEEDED/FAILED
- Cache hit path (if enabled) returns response and records appropriate status

Mock strategy:
- Patch `LiteLLMClient.acompletion()` to return deterministic responses.
- Patch time to validate latency calculations.

---

## G2. Integration tests (optional, gated)

- Ollama smoke test (requires local service):
  - marked `@pytest.mark.integration`
  - skip if `OLLAMA_ENABLED=false`
- Gemini smoke test:
  - skip if `GEMINI_API_KEY` missing

---

## G3. Contract tests (multi-provider)

Create a small “contract prompt set” and validate:
- plain text response works
- tool call path (if you support it) works on Gemini
- JSON output path works (PydanticAI schema)

---

## G4. CI gates

- ruff, mypy strict, pytest
- enforce no secrets in logs
- **Coverage gate:** Set a concrete threshold for `app/llm/` (e.g. **≥ 80% line coverage**). If the project already has a standard in pytest.ini or pyproject.toml, reference that instead.

**Required tests (minimum):**
- Router selection and fallback on retryable error
- Idempotency key “replay” path (return stored result when idempotency_key matches)
- Cache key canonicalization and TTL behavior (when cache enabled)

**Acceptance criteria (Phase G)**
- Unit tests cover routing + mapping + persistence
- Router, idempotency, and cache tests exist as above
- Integration tests can be run manually or in a nightly job
- Coverage gate for `app/llm/` is defined and met
