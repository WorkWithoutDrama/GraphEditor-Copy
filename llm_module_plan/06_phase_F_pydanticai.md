# Phase F — PydanticAI Integration (Structured Outputs)

You’re already using PydanticAI in the project; this phase makes LLM usage **schema-first**.

---

## F1. Decide integration strategy

Two viable approaches:

### Option 1 — Custom PydanticAI model adapter (recommended)
- Implement a `pydantic_ai.models.Model` adapter that delegates to `LLMService.chat()`.
- Pros: no extra infra; fully aligned with your router/persistence/guardrails.
- Cons: some adapter code to maintain.

### Option 2 — Use LiteLLM Proxy + OpenAI-compatible model
- Run LiteLLM proxy, then configure PydanticAI to use an OpenAI-compatible client at the proxy base URL.
- Pros: less custom code.
- Cons: extra service to deploy + more moving parts.

This plan implements **Option 1**, but keeps Option 2 as an extension.

---

## F2. Implement adapter: `PydanticAiLiteLLMModel`

File: `app/llm/pydanticai/model.py`

**Scope (v1):** The adapter supports **non-streaming completion only**. Streaming is deferred to a later phase once core routing and persistence are stable.

Responsibilities:
- Convert PydanticAI messages → `LLMRequest`
- Choose `profile` based on agent or dependency (e.g. LOCAL_FAST by default)
- Call `LLMService.chat()`
- Return response in the shape PydanticAI expects (text; tool calls if in scope — see below)
- For structured output: use PydanticAI’s normal schema extraction flow; add strict JSON mode via `LLMRequest.response_format` if needed

**Tool calls:** If a PydanticAI agent uses tool calls in v1: map tool specs to `LLMRequest.tools`, ensure `LLMService.chat()` passes them through to LiteLLM, and ensure the router routes tool-required requests to a supporting provider (e.g. Gemini). If tool calls are not in v1 scope, state explicitly: “v1 adapter ignores tool calls; add later.”

PydanticAI recommends controlling retries/fallbacks to avoid double-retry when using fallback models — that aligns with keeping retries/fallback in **our** router and provider retries minimal.

---

## F3. Example: “interest extraction” as structured output

Create `schemas.py`:
```python
from pydantic import BaseModel, Field

class Interest(BaseModel):
    name: str
    confidence: float = Field(ge=0, le=1)

class InterestExtractionResult(BaseModel):
    interests: list[Interest]
```

Example agent usage:
- Prompt: doc chunk summary + request JSON output
- Output parsed as `InterestExtractionResult`

---

## F4. Dependency injection pattern

Agents should receive `LLMService` (or a small façade) via dependencies, consistent with the rest of the app.

Example:
- `InterestExtractorService` depends on:
  - `LLMService`
  - `ChunkRepo` (read chunks)
  - `InterestRepo` (write results)

LLM module stays focused; orchestrators compose it.

---

**Acceptance criteria (Phase F)**
- At least one PydanticAI agent produces validated `BaseModel` output via `LLMService`.
- On validation failure, it raises `LLMResponseInvalid` and persists the failed run.
