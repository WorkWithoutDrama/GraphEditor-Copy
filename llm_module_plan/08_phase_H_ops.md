# Phase H — Ops & Telemetry

**Telemetry contract:** All observability is consolidated in `app/llm/telemetry.py`. It provides (1) **redaction helpers** (no secrets/PII in stored or logged previews), (2) **structured log emission** (standard fields per call), and (3) **metrics emission** (counters/histograms as below). `LLMService` and `LiteLLMClient` call these helpers; they do not embed ad hoc log or metric code.

---

## H1. Structured logging (match Docling module style)

Log fields on every call (via telemetry helpers):
- `llm_run_id`
- `workspace_id`
- `provider`, `model`, `profile`
- `stage`
- `latency_ms`
- `status`
- `error_code` (if any)

Never log:
- raw prompt text (unless explicitly enabled and redacted)
- API keys

---

## H2. Metrics (Prometheus-ready)

Emit counters/histograms (via telemetry module):
- `llm_requests_total{provider,model,profile,status}`
- `llm_latency_ms_bucket{provider,model}`
- `llm_tokens_total{provider,model,kind=in|out}`
- `llm_errors_total{provider,code}`

If you already have an observability module, register these in the same registry.

---

## H3. Cost / usage reporting

**v1:** Persist token counts (`input_tokens`, `output_tokens`, `total_tokens`) from the provider. `cost_usd` remains optional/NULL unless LiteLLM returns it reliably. **Later:** Add a post-processing step (e.g. daily aggregation job) to compute cost from a provider/model pricing table and token usage.

---

## H4. Runbook

### Common failures
- `LLMAuthError` (Gemini key missing/invalid)
- `LLMUnavailable` (Ollama not running / port closed)
- `LLMRateLimited` (Gemini quota)
- `LLMTimeout` (model overloaded)

### Standard actions
- switch `router_policy` to prefer alternative provider
- reduce concurrency
- increase timeout only if necessary
- inspect `llm_runs` table for correlated failures by stage/model

---

## H5. Future extensions (non-blocking)

- Add LiteLLM Router for multi-instance load balancing / fallbacks
- Add LiteLLM Proxy for centralized key management
- Add “prompt templates” registry per pipeline stage
- Add response caching via Redis (if SQL cache becomes bottleneck)

**Acceptance criteria (Phase H)**
- Redaction, structured logging, and metrics are implemented in `telemetry.py`; service and client call telemetry helpers only.
- You can answer: “which model failed, why, and how often?” from logs + `llm_runs`.
