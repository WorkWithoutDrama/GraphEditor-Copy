# Stage 1 Step-by-Step Implementation Plan

This plan assumes you already have:
- chunks stored in SQL
- working LiteLLM client abstraction
- Qdrant client abstraction
- Pydantic settings + project structure

## Step 0 — Create a clean Stage 1 module boundary
Create a module/package, e.g.:
- `app/runs/stage1_extract/`

Expose one public entry:
- `run_stage1_extract(doc_id: str | None, chunk_ids: list[str] | None, config: Stage1Config) -> RunResult`

Avoid coupling Stage 1 to the temporary glue orchestrator. Stage 1 should be callable from it, not embedded inside it.

---

## Step 1 — Define config + signatures
Create `Stage1Config` (Pydantic):
- `prompt_version`
- `extractor_version` (code/schema version)
- `model_id` (provider/model)
- `temperature`, `max_tokens`
- `concurrency` (max parallel chunk calls)
- `repair_attempts`
- `embed_claims: bool`
- `qdrant_collection: str`

Define `signature_hash = hash(chunk_content_hash + prompt_version + extractor_version + model_id + core_params)`.

---

## Step 2 — Implement chunk selection
Query chunks to process:
- from doc_id, or explicit chunk_ids
- filter out chunks already cached:
  - join `chunk_extractions` on `(chunk_id, signature_hash)` status in {SUCCESS,CACHED}
- optionally allow `--force` to reprocess (creates a new signature by bumping extractor_version or add `force_run_id`)

---

## Step 3 — Implement LLM call wrapper (auditable)
For each chunk:
1) Build prompt messages (chunk-only)
2) Call `llm_client.complete(messages, params)`
3) Store to `llm_calls` (request_json + raw response)
4) Parse JSON and validate Pydantic
5) If validation fails:
   - run repair prompt (store 2nd call as another llm_call record)
6) Return validated `Stage1ExtractionResult`

**Important:** store `prompt_version` and `model_id` in both `chunk_extractions` and `llm_calls`.

---

## Step 4 — Persist chunk extraction record (cache gate)
Before calling LLM, attempt to insert a `chunk_extractions` row with `(chunk_id, signature_hash)`:
- If insert fails due to uniqueness:
  - another worker already processed it
  - fetch existing record and reuse it
This supports concurrency and prevents duplicated LLM calls.

Set status transitions:
- `RUNNING` (optional) → `SUCCESS` / `FAILED` / `CACHED`

---

## Step 5 — Persist claims + evidence
Transform validated output into DB rows:

- create claim row for each claim:
  - store `claim_type`, `value_json`, `epistemic_tag`, `confidence`, `rule_id`
- create evidence rows (1..n) per claim:
  - store snippet and offsets if present

**Do not attempt global dedupe here.** Stage 1 is append-only.

---

## Step 6 — Embed and upsert to Qdrant
For each persisted claim, generate `embedding_text`, e.g.:
- `"{type} | {normalized_subject/action} | {normalized_value}"`

Call embedding model (whatever you use) and upsert to Qdrant:
- point_id: claim_id
- vector: embedding
- payload:
  - doc_id, chunk_id, run_id
  - claim_type, epistemic_tag, review_status
  - prompt_version, extractor_version, model_id

Batch upserts for performance.

---

## Step 7 — Run stats + finalization
Accumulate per-run counters:
- chunks_total
- chunks_cached
- chunks_success
- chunks_failed
- claims_total
- token usage totals (if available)

Persist in `runs.stats_json`, set status:
- SUCCESS if all chunks processed or cached
- PARTIAL if some failed
- FAILED if catastrophic (e.g., DB down)

---

## Step 8 — CLI entrypoint (for MVP testing)
Add CLI:
- `stage1_extract --doc-id <id> --model <...> --prompt-version chunk_claims_extract_v1`

Return:
- run_id
- counts
- where to inspect claims (SQL) and embeddings (Qdrant)

---

## Step 9 — Safety constraints (hard checks)
- Reject outputs that contain non-JSON or violate schema after repair
- Reject claims missing evidence unless RULE_INFERRED
- Enforce maximum evidence snippet length
- Enforce maximum number of claims per chunk (avoid blow-ups; e.g., cap at 50 with warning)
