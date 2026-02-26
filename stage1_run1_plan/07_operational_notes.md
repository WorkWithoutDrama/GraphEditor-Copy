# Operational Notes (Stage 1)

## Config defaults (recommended)
- temperature: low (0–0.2)
- max_tokens: enough for JSON but capped
- concurrency: start small (e.g., 4–8), tune per provider
- repair_attempts: 1 (maybe 2 if the model is noisy)

---

## Failure modes and handling
1) Provider/network error:
- retry with exponential backoff
- if still fails: mark chunk extraction FAILED, continue

2) Schema invalid:
- try repair once
- if still invalid: FAILED with stored raw output

3) DB errors:
- fail fast if cannot persist (don’t lose extracted data)
- consider wrapping chunk transaction: either persist everything for that chunk or nothing

4) Qdrant unavailable:
- extraction can still succeed
- mark embedding step failed but keep claims (store in run stats)
- allow a separate “embed_missing_claims” job later

---

## Observability
Log with correlation IDs:
- `run_id`, `chunk_id`, `llm_call_id`

Persist in SQL:
- request/response
- durations and token usage if possible

---

## Data growth
Claim ledger grows quickly. MVP tips:
- keep evidence snippets short (cap length)
- do not store full chunks again in evidence tables (reference chunk_id)

---

## Security / privacy
If docs can contain secrets:
- consider redaction rules before sending to external models
- store raw response carefully (access control later)

---

## Next stages (not implemented now)
- Stage 2: normalization/dedupe/conflict grouping using Qdrant retrieval
- Stage 3: compose canonical claims into AtomicActions + BusinessOperations with field wrappers
- Admin review UI: accept/reject claims and resolve conflicts
