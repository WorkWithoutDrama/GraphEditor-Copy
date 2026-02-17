# Phase C — LiteLLM Client Wrapper (Async + Guardrails)

## C1. Decide how we use LiteLLM

**SDK mode (recommended now):** import `litellm` and call `acompletion()` / `completion()` directly.  
**Proxy mode (optional later):** deploy LiteLLM proxy and call it via OpenAI-compatible client.

This plan implements SDK mode first, but keeps an internal abstraction so proxy can be swapped later.

**Dependency:** Pin LiteLLM to a known-good version in your dependency management (requirements.txt / uv / poetry). Document the minimum or locked version in the module (e.g. in Phase C5 or an `app/llm/README.md`) so upgrades are reviewable.

---

## C2. Implement `LiteLLMClient`

File: `app/llm/client_litellm.py`

### Responsibilities
- Normalize `LLMRequest` → LiteLLM call kwargs
- Apply:
  - **timeouts**
  - **concurrency limiting** (Semaphore)
  - **retries with backoff** for retryable failures
  - param dropping (multi-provider safety)
- Convert LiteLLM response → `LLMResponse`
- Convert exceptions → `LLMError` subclasses

### Key design choices
1. **Single async method**:
   - `async def acompletion(self, provider: LLMProvider, model: str, req: LLMRequest) -> LLMResponse`

2. **Semaphore per app instance**
   - `self._sem = asyncio.Semaphore(settings.concurrency_limit)`

3. **Retry rules**
   - Retry only on `retryable=True` errors (429, 5xx, timeouts)
   - Exponential backoff + jitter
   - Do not double-retry if provider SDK already retries (keep LiteLLM/provider retries minimal)

4. **Param dropping**
   - If `drop_unsupported_params=True`, set `drop_params=True` on the LiteLLM request so unsupported OpenAI params are dropped rather than raising.

---

## C3. Request normalization rules (avoid ambiguity)

- Always send `messages` in OpenAI format (`role`, `content`)
- Always include a `system` message if the pipeline expects it; do not “inject” silently inside provider adapters.
- If `req.response_format` indicates JSON schema, set the provider-appropriate params (and enforce in post-parse).

---

## C4. Response normalization rules

- Always return:
  - `provider`, `model`, `latency_ms`
  - `usage` if present
- Extract text:
  - prefer `choices[0].message.content` (chat)
  - fallback: `choices[0].text` (completion)
- Set `finish_reason` if available.

---

## C5. Exception mapping

Implement a single mapper and **document the concrete exception classes** you map (by name), so LiteLLM upgrades can be checked against this list:

- `litellm.exceptions.Timeout` → `LLMTimeout(retryable=True)`
- rate limit errors (e.g. 429 / LiteLLM rate-limit type) → `LLMRateLimited(retryable=True)`
- auth errors → `LLMAuthError(retryable=False)`
- invalid request → `LLMBadRequest(retryable=False)`
- unknown → `LLMUnavailable(retryable=True)` or `LLMError(code="UNKNOWN", retryable=False)` based on heuristic.

Store the **original exception class name** in `LLMError.details` (but do not leak secrets).

**Tests:** Add a test that asserts (1) these exception names are recognized and map to the correct `LLMError` subclass and `retryable` flag, and (2) unknown exceptions map to `LLMUnavailable` or `LLMError(UNKNOWN)`.

**Acceptance criteria (Phase C)**
- `LiteLLMClient` can be used by a router to call either provider with the same `LLMRequest`.
- A transient failure triggers retries with backoff and does not exceed max attempts.
- LiteLLM version is pinned; exception mapping list is documented and covered by tests.
