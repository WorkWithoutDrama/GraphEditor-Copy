# Phase A — Contracts & Public API

## A1. Decide the single entrypoint (what other modules call)

- **Ports** in `app/llm/ports.py`: `LLMClientPort` (low-level, provider-agnostic) and any repo ports.
- **Orchestrator** in `app/llm/service.py`: `LLMService` (routing + persistence + policy) — this is the only class other modules use.

**Rule:** other modules never call LiteLLM or provider SDKs directly.

---

## A2. Define typed request/response models (Pydantic v2)

In `app/llm/types.py` define:

### Core types
- `LLMProvider`: Enum = `{OLLAMA, GEMINI}`
- `LLMModel`: validated string (alias-friendly)
- `LLMProfile`: Enum = `{LOCAL_FAST, CLOUD_QUALITY, AUTO}` (extendable)
- `LLMMessage`: `{role: Literal["system","user","assistant","tool"], content: str}`
- `LLMRequest`:
  - `messages: list[LLMMessage]`
  - `profile: LLMProfile`
  - `temperature: float | None`
  - `max_output_tokens: int | None`
  - `tools: list[dict] | None` (OpenAI-compatible tool spec)
  - `response_format: dict | None` (for JSON schema / structured output)
  - `metadata: dict[str, str]` (reserve keys: `workspace_id`, `pipeline_run_id`, `stage`; plus document_id, run_id, etc.)
  - `idempotency_key: str | None` (important for persistence + cache)
  - `timeout_s: float | None`

### Result types
- `LLMUsage`: `input_tokens`, `output_tokens`, `total_tokens`, `cost_usd?`
- `LLMResponse`:
  - `text: str`
  - `raw: dict` (provider response, **optional** / redacted)
  - `usage: LLMUsage | None`
  - `provider: LLMProvider`
  - `model: str`
  - `latency_ms: int`
  - `finish_reason: str | None`

### Constraints objects (router-friendly)
- `LLMConstraints`: `max_input_tokens?`, `max_context_tokens?`, `requires_tools?`, `requires_json?`, `allow_fallbacks: bool`

---

## A3. Error taxonomy (align with DB + FSM patterns)

In `app/llm/errors.py`:

- Base: `LLMError(code: str, retryable: bool, provider: LLMProvider | None)`
- Concrete:
  - `LLMTimeout`
  - `LLMRateLimited`
  - `LLMBadRequest`
  - `LLMAuthError`
  - `LLMUnavailable`
  - `LLMResponseInvalid` (e.g., JSON schema mismatch)

Map everything to stable `code` values so that SQL runs table can record them and pipelines can make decisions.

---

## A4. Public methods (keep small)

In `app/llm/service.py` (only):

- `async chat(req: LLMRequest) -> LLMResponse`
- `async chat_json(req: LLMRequest, schema: type[pydantic.BaseModel]) -> schema` (optional, or implemented via PydanticAI)
- `async stream_chat(req: LLMRequest) -> AsyncIterator[str]` (optional; deferred to later phase)

**Acceptance criteria (Phase A)**
- The public API compiles, is fully typed, and has docstrings describing invariants and exceptions.
- `LLMRequest.model_dump()` is stable and can be hashed for idempotency.
