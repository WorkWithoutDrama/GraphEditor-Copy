# Phase D — Providers: Ollama + Gemini (LiteLLM)

This phase adds **provider-specific configuration** and “known-good” smoke paths.

---

## D1. Ollama provider adapter

File: `app/llm/providers/ollama.py`

### How LiteLLM expects Ollama calls

LiteLLM’s docs show this minimal usage for Ollama: model prefix `ollama/` and an `api_base` pointing at the local Ollama server. citeturn1view0

Example (SDK):
```python
from litellm import completion
resp = completion(
  model="ollama/llama2",
  messages=[{"role": "user", "content": "Hello"}],
  api_base="http://localhost:11434",
)
```

### Adapter responsibilities
- Build provider kwargs:
  - `model = settings.ollama_model`
  - `api_base = settings.ollama_api_base`
- Optional: standardize on `ollama_chat` (if you decide to) by mapping model or provider route consistently.
- Enforce a smaller timeout by default if desired (local models can hang on heavy prompts).

### Operational notes
- Treat Ollama as “best-effort local”: safe defaults, fast fallback to cloud when required.

---

## D2. Gemini (Google AI Studio) provider adapter

File: `app/llm/providers/gemini.py`

### Model string format matters

LiteLLM’s Vertex documentation notes that **models without a prefix may default to Vertex AI**, which requires GCP auth.  
If you want “API key like OpenAI”, use the `gemini/` prefix + `GEMINI_API_KEY`. citeturn1view2

LiteLLM’s Gemini docs show setting `GEMINI_API_KEY` and calling `completion(model="gemini/<...>")`. citeturn1view1

### Adapter responsibilities
- **API key:** Prefer passing the key in provider kwargs: `api_key=settings.gemini_api_key.get_secret_value()`. Do not set `os.environ` inside the adapter. If LiteLLM requires an env var for Gemini, set it **once at app bootstrap** (e.g. `bootstrap_llm_secrets(settings)`), not per request.
- Build provider kwargs:
  - `model = settings.gemini_model` (e.g. `gemini/gemini-2.0-flash`)
- Optional: expose per-request safety settings if you need them later.

---

## D3. Router as injectable object and capability matrix

In `app/llm/router.py`, implement **`LLMRouter`** as a first-class injectable class (not a set of loose functions):

- **`LLMRouter`**:
  - `def select_provider(self, req: LLMRequest, constraints: LLMConstraints) -> LLMProvider`
  - Optionally: `async def execute(self, req: LLMRequest) -> LLMResponse` (convenience that runs selection + fallback loop)

**Capability matrix:** Keep in one place — either inside `LLMRouter` or as `PROVIDER_CAPABILITIES: dict[LLMProvider, ProviderCaps]` in `router.py`. `ProviderCaps` includes:
- `supports_tools: bool` (Gemini = yes; Ollama = limited/experimental)
- `supports_json: bool` (Gemini = good; Ollama = best effort)
- `max_context_tokens: int | None`
- Optionally: `preferred_for_profiles: set[LLMProfile]`

**Selection and fallback:**
- If `requires_tools=True` and `force_cloud_for_tools=True` → route to Gemini
- If `requires_json=True` and `force_cloud_for_json=True` → route to Gemini
- Otherwise prefer provider per `profile` and `settings.router_policy`
- **Deterministic fallback:** If the first provider fails with a **retryable** error and `constraints.allow_fallbacks` is true → try next provider (per `fallback_order`). Never fallback on non-retryable errors (bad request, auth).

---

## D4. Smoke tests (minimal)

Create two smoke tests:
- `test_ollama_smoke.py` (skipped if not enabled)
- `test_gemini_smoke.py` (skipped if no API key)

Each should:
- Send a simple prompt
- Assert non-empty response text
- Assert latency_ms is recorded
- Persist run (if enabled) and verify row exists

**Acceptance criteria (Phase D)**
- Both providers can be called through the same `LLMService.chat()` interface.
- Gemini uses `gemini/` prefix and API key handling follows Phase B (explicit `api_key=` or bootstrap, no per-request env mutation).
- `LLMRouter` is injectable and uses the capability matrix for deterministic selection and fallback.
