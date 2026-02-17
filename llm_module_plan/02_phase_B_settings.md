# Phase B — Settings & Secrets (Pydantic)

## B1. Create `LLMSettings` (Pydantic BaseSettings)

File: `app/llm/settings.py`

Use the same pattern as other app settings (e.g. `VectorStoreSettings`):
- `model_config = SettingsConfigDict(env_prefix="LLM_", env_file=".env", env_file_encoding="utf-8", extra="ignore")`

All fields below are overridable via env vars with the `LLM_` prefix (e.g. `LLM_DEFAULT_PROFILE`, `LLM_CONCURRENCY_LIMIT`, `LLM_OLLAMA_API_BASE`, `LLM_OLLAMA_MODEL`, `LLM_GEMINI_MODEL`, `LLM_PERSIST_RUNS`, `LLM_CACHE_ENABLED`). See B2 for Gemini API key naming.

### Required fields
- `default_profile: LLMProfile = AUTO`
- `concurrency_limit: int = 8`
- `default_timeout_s: float = 60.0`
- `max_retries: int = 2`
- `retry_backoff_base_s: float = 0.5`
- `retry_backoff_max_s: float = 8.0`
- `drop_unsupported_params: bool = True`  
  (LiteLLM can raise if a param isn’t supported; dropping makes multi-provider routing safer.)

### Ollama
- `ollama_enabled: bool = True`
- `ollama_api_base: str = "http://localhost:11434"`  
- `ollama_model: str = "ollama/<your-model>"` (e.g. `ollama/llama3`)
- `ollama_force_chat: bool = True` (use `ollama_chat` route if you standardize on it)

### Gemini (Google AI Studio)
- `gemini_enabled: bool = True`
- `gemini_api_key: SecretStr | None`
- `gemini_model: str = "gemini/gemini-2.0-flash"` (or other)
- `gemini_safety_settings: dict | None` (if you later expose it)

### Routing
- `router_policy: Literal["prefer_local","prefer_cloud","auto"] = "auto"`
- `fallback_order: list[LLMProvider] = [OLLAMA, GEMINI]`
- `force_cloud_for_tools: bool = False` (optional)
- `force_cloud_for_json: bool = False` (optional)

### Persistence
- `persist_runs: bool = True`
- `persist_prompt_text: bool = False` (store hashes by default; avoid sensitive data)
- `cache_enabled: bool = False`
- `cache_ttl_s: int = 86400`

---

## B2. Secrets loading and Gemini API key

- Never log API keys. Redaction helpers live in `app/llm/telemetry.py`.

**Gemini API key (choose one and document):**
- **Pattern 1 (compatibility):** Keep `GEMINI_API_KEY` as the env var; do not duplicate. Document this exception to the `LLM_` prefix.
- **Pattern 2 (namespaced, recommended):** Use `LLM_GEMINI_API_KEY`. Pass the key explicitly to LiteLLM via provider kwargs (`api_key=settings.gemini_api_key.get_secret_value()`) so the adapter never mutates `os.environ`. If LiteLLM requires an env var, set it **once at app bootstrap** (e.g. `bootstrap_llm_secrets(settings)`), not inside the adapter.

---

## B3. Settings validation rules

Implement `model_validator` checks:
- If `gemini_enabled=True` then `gemini_api_key` must be present.
- If any enabled provider has empty model string → error at startup.
- Validate `concurrency_limit >= 1`, `default_timeout_s > 0`, etc.

**Acceptance criteria (Phase B)**
- App fails fast on invalid configuration (clear error messages).
- Settings can be injected into services like DB/vector/docling modules already do.
