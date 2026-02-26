# Stage 1 Run-1 Plan: Critique and Clarifying Questions

This document provides a structured critique of the Stage 1 (Run-1) implementation plan and a list of clarifying questions. It is intended to tighten the plan before implementation.

---

## 1. Critique

### 1.1 Strengths

- **Clear scope and boundaries** — The plan explicitly states what Stage 1 is and is not (chunk-only, no cross-chunk normalization, no composition). This reduces scope creep.
- **Evidence-first and epistemic tags** — Requiring evidence per claim and tagging EXPLICIT/IMPLICIT/MODEL_INFERRED supports auditability and later review; the “if unsure, omit” rule is well aligned with conservative extraction.
- **Idempotency and cache key** — The signature (chunk_content_hash + prompt_version + extractor_version + model_id + params) is well specified and supports reproducible runs and cost control.
- **Concurrency-safe cache gate** — Using a unique `(chunk_id, signature_hash)` and insert-then-check avoids duplicate LLM calls under parallel workers.
- **Repair flow** — Two-step parse → repair prompt → fail with persisted raw output is practical and auditable.
- **Operational realism** — Failure modes (provider/network, schema, DB, Qdrant), retries, and “embed_missing_claims” as a follow-up job are thought through.
- **Testing strategy** — Unit tests (signature, schema, repair, DB), integration test with a small doc, and golden chunks are appropriate for MVP.

### 1.2 Gaps and Ambiguities

- **Schema vs existing codebase**  
  The plan introduces tables `runs`, `chunk_extractions`, `llm_calls`, `claims`, `claim_evidence`. The codebase already has:
  - `pipeline_runs` (workspace_id, document_id, status, llm_profile, prompt_name, …)
  - `chunk_extractions` (run_id, chunk_id, prompt_name, model, raw_text, parsed_json, …) with unique `(run_id, chunk_id, prompt_name)`
  - `chunk_runs` (run_id, chunk_id, status, …)

  The plan does not state whether to:
  - **Replace** these with the new schema (migrate and drop/repurpose old tables), or
  - **Add** new Stage-1-specific tables (e.g. `stage1_runs`, `stage1_chunk_extractions`) and leave the MVP orchestrator tables as-is for the “disposable glue.”

  **Recommendation:** Decide explicitly: either “Stage 1 uses new tables only” (and document migration from old pipeline_runs if needed) or “Stage 1 extends existing tables with new columns/constraints” and describe the migration.

- **Run identity and batch vs document**  
  Plan says `runs.doc_id` is nullable “if batch.” It does not define what a “batch” is (e.g. multiple docs in one run, or “all chunks from a filter”). For chunk selection (“from doc_id, or explicit chunk_ids”), it’s unclear whether a single run can span multiple documents or only one document + optional chunk subset. Clarifying this will affect `runs` design and the chunk-selection API.

- **`chunk_content_hash` normalization**  
  “Normalized chunk text (e.g., strip whitespace, normalize newlines)” is underspecified. Even small differences (e.g. Unicode normalization, strip vs no strip) change the hash and break cache hits. The plan should specify the exact normalization (e.g. NFKC, single newline, no leading/trailing space) and encode it in `extractor_version` or document it so it’s stable across versions.

- **Embedding model and collection**  
  Step 6 says “Call embedding model (whatever you use).” The codebase has an embeddings module (e.g. Ollama). The plan does not state:
  - Which embedding model is used for claims (same as chunk embeddings or a dedicated one).
  - Whether the Qdrant collection name is fixed per Stage 1 run (e.g. from config) or versioned (e.g. by extractor_version). This affects idempotency when the embedding model or schema changes.

- **`llm_calls` and linkage to cache**  
  On cache hit, no LLM call is made; the plan says “reuse existing claim IDs.” The `chunk_extractions` row has `llm_call_id` (nullable). For a CACHED row, `llm_call_id` will be null (or point to an older run’s call). The plan doesn’t state whether we need to be able to trace “this chunk extraction reused claims from run X” via a relation (e.g. `chunk_extractions.original_run_id` or `original_llm_call_id`). For audit, that might be desirable.

- **NOTE claim type**  
  NOTE is “optional” and “keep minimal.” The schema and validation rules don’t specify whether NOTE requires evidence or can be evidence-free like RULE_INFERRED, or what `value` shape it has. This can lead to inconsistent validation or prompt drift.

- **Cap at 50 claims per chunk**  
  Step 9 mentions “cap at 50 with warning.” It’s not specified whether we truncate (and if so, how we choose which to drop), reject the whole extraction, or only warn and persist all. Truncation could bias the ledger; rejection might be safer for MVP with a clear error path.

### 1.3 Risks

- **Run table and observability**  
  If `runs` is new and separate from `pipeline_runs`, existing dashboards or scripts that only know about `pipeline_runs` will not see Stage 1 runs unless a separate view or integration is added. Low risk for a single team, but worth a one-line note in the plan.

- **Qdrant failure and “embed later”**  
  Allowing extraction to succeed and “embed_missing_claims” later is good. The plan should state how we mark claims as “not yet embedded” (e.g. a flag, or absence in Qdrant) and how the embed job discovers them (e.g. by run_id or by “claims with no Qdrant point”).

- **Repair prompt and token budget**  
  Repair sends “raw output + schema” to the LLM. For large raw outputs, this can exceed context or be expensive. A limit (e.g. truncate raw to last N chars) or a note that repair is best-effort for “small” failures would reduce risk.

- **Determinism and golden tests**  
  Golden tests compare “stable fields only” or “deterministic model settings.” If the only available models are non-deterministic, golden tests may be flaky. The plan could recommend a small deterministic model or a single canonical run artifact (e.g. committed JSON) for regression.

### 1.4 Consistency and Small Nits

- **Naming**  
  Plan uses `run_id` in several places; the schema uses `run_id` (uuid) in `runs`. The existing code uses `pipeline_runs.id`. Keeping naming consistent (e.g. always `run_id` for the run’s PK) will avoid confusion.

- **`subject_type` / `subject_text`**  
  These are “optional; for later grouping.” It’s not stated whether the prompt asks the LLM to fill them or they are derived in code from `value_json`. If LLM-filled, the prompt/schema doc should describe them; if derived, the implementation plan should say where.

- **`config_json` and `stats_json`**  
  Storing these as JSON is flexible. For queryability (e.g. “all runs with model X”), consider documenting whether we will add application-level indexes or use JSON queries; for SQLite, JSON functions are available but not always indexed.

---

## 2. Clarifying Questions

### 2.1 Schema and existing code

1. Should Stage 1 use **new tables only** (e.g. `stage1_runs`, `stage1_chunk_extractions`, …) and leave `pipeline_runs` / current `chunk_extractions` untouched, or should we **migrate** the existing pipeline tables to the new schema and deprecate the old column semantics?
2. For the existing `chunk_extractions` unique constraint `(run_id, chunk_id, prompt_name)`: the plan’s cache key is `(chunk_id, signature_hash)`. Should `signature_hash` be the single “version” of the extraction (so one chunk can have multiple extractions for different signatures), and should we keep `run_id` on `chunk_extractions` to record “which run wrote this row”?

### 2.2 Run and batch semantics

3. Can one Stage 1 run process chunks from **multiple documents**, or is it always one run = one document (with optional chunk_ids filter)? If multiple docs are allowed, how is `doc_id` set (null, or first doc, or a batch_id)?
4. For “optional `--force` to reprocess”: should `--force` create a **new run** (same chunks, new run_id) with a bumped version/signature, or re-use the same run_id and invalidate/overwrite previous extractions for those chunks?

### 2.3 Caching and hashing

5. What is the **exact** normalization for `chunk_content_hash`? (e.g. UTF-8, NFKC, strip(), single `\n` for newlines, no other changes?)
6. Should `extractor_version` be a **code/schema version** (e.g. from app or schema module) or a manually bumped string in config? Same for `prompt_version`: from file hash, or from a literal in config?

### 2.4 Claims and evidence

7. For **NOTE** claims: required evidence (snippet) or optional? And what is the canonical `value` shape (e.g. `{ "text": "..." }`)?
8. When the plan says “cap at 50 claims per chunk”: should we **reject** the extraction (FAILED), **truncate** (and if so, by what rule?), or **persist all and only log a warning**?
9. Should **RULE_INFERRED** claims ever be produced by Stage 1 in v1, or is that explicitly out of scope (so we only allow EXPLICIT, IMPLICIT, MODEL_INFERRED)?

### 2.5 Embeddings and Qdrant

10. Which **embedding model** should be used for claims (same as existing chunk embeddings, or a dedicated one)? Should it be fixed in config or selectable per run?
11. How do we identify claims that were **not embedded** (e.g. after Qdrant failure) so a later “embed_missing_claims” job can find them? (e.g. a `claims.embedded_at` column, or “point exists in Qdrant” check?)

### 2.6 LLM and repair

12. For the **repair prompt**, is there a maximum length for the “raw output” we send (to avoid context overflow and cost)? Should we truncate and mention “output truncated” in the repair prompt?
13. Should **token usage** (prompt_tokens, completion_tokens) be stored in `llm_calls` for every call (including repair)? The plan mentions “if available”; confirming that we always try to capture and persist when the client provides it would help.

### 2.7 Operations and CLI

14. For the CLI, should `stage1_extract` support **only doc-id** and **only chunk-ids** (no “all chunks in workspace”), or also a “run on all chunks that have no successful extraction for current signature” mode?
15. Should the run’s **config_json** store the full `Stage1Config` (including concurrency, repair_attempts, etc.) for full reproducibility, or only the fields that affect the signature (prompt_version, model_id, temperature, …)?

---

## 3. Summary

The plan is strong on scope, evidence, idempotency, and operations. The main gaps are: (1) how the new schema relates to existing `pipeline_runs` and `chunk_extractions`, (2) exact cache-key normalization and run/batch semantics, (3) embedding model and “missing embedding” tracking, (4) behavior for NOTE and for the 50-claim cap, and (5) a few repair/observability details. Resolving the questions in §2 will make the plan ready for implementation with minimal backtracking.
