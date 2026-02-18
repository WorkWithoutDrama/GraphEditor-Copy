# Caching + Idempotency (Stage 1)

## What we are caching
We cache **chunk extraction results** so we do not call the LLM repeatedly for the same content and configuration.

### Cache key (signature)
Compute:
- `chunk_content_hash`: hash of normalized chunk text (e.g., strip whitespace, normalize newlines)
- plus stable extraction identity:
  - `prompt_version`
  - `extractor_version`
  - `model_id`
  - critical params (temperature, system prompt hash if you vary it)

Then:
- `signature_hash = sha256(chunk_content_hash + prompt_version + extractor_version + model_id + params_fingerprint)`

Store `signature_hash` in `chunk_extractions` with unique constraint `(chunk_id, signature_hash)`.

---

## Cache hit behavior
If `chunk_extractions` contains `(chunk_id, signature_hash)` with status `SUCCESS` or `CACHED`:
- skip LLM call
- return existing claim IDs (query claims by run_id+chunk_id OR via relation table)

Prefer to store a `chunk_extraction_id -> claim_ids` mapping implicitly via `claims.chunk_id` + `claims.run_id`.

---

## Concurrency-safe cache gate
To prevent two workers calling the LLM for the same chunk simultaneously:

1) Attempt insert into `chunk_extractions` for `(chunk_id, signature_hash)` with status `RUNNING`.
2) If uniqueness violation:
   - fetch the existing row
   - if status is SUCCESS/CACHED: reuse
   - if RUNNING: either wait/poll or skip (configurable)
3) On completion:
   - update status to SUCCESS/FAILED

---

## When to invalidate cache
Cache should change when you want results to change:

- Prompt changes → bump `prompt_version`
- Schema/extractor logic changes → bump `extractor_version`
- Model changes → new `model_id`

Do NOT add ad-hoc invalidation; use versions so runs are reproducible.

---

## Embedding cache (optional)
Embedding calls can also be cached:
- if claim text and embedding model are identical
- but for MVP, embedding cost is usually smaller than LLM extraction cost

At minimum:
- avoid re-embedding claims that already exist for this run.

---

## Determinism tips
- Set temperature low for extraction.
- Use explicit schema and “JSON only” constraints.
- Keep prompts stable; version them.
