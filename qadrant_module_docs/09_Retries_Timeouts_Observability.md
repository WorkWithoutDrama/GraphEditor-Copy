# 09 — Retries, Timeouts, Observability

## Retry policy
- Retry only transient categories:
  - timeouts
  - connection errors
  - 429 / 5xx
- Do NOT retry schema mismatch or validation errors.

Suggested:
- max_attempts = settings.retries (default 3)
- exponential backoff:
  - delay = base * 2**(attempt-1) + jitter

## Timeouts
- Set client timeout to a sane value (10–30s)
- For large upserts, consider increasing or splitting batches.

## Metrics/logging
Emit structured logs:
- collection name
- embedding_set_slug
- batch size
- latency
- success/failure
- qdrant error type

Connect to your existing observability stack (whatever we choose later).

