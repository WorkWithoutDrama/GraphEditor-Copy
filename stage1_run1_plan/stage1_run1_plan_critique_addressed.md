# Stage 1 (Run‑1) Plan — Critique Addressed + Decisions (Single Source)

This document addresses the critique + clarifying questions raised in **“Stage 1 Run‑1 Plan: Critique and Clarifying Questions”**. fileciteturn0file0  
It updates the Stage‑1 plan with explicit decisions, schema alignment guidance, and tightened implementation rules.

---

## 0) Executive decisions (what we lock now)

### D0.1 — Stage 1 schema strategy vs existing tables
We will **reuse and evolve existing “pipeline” tables where sensible** and **add Stage‑1 ledger tables**, with **no requirement to preserve old semantics** (the MVP glue is disposable).

Concretely:
- `pipeline_runs` becomes the canonical **Run** record (we may rename in code; physical rename optional).
- Existing `chunk_extractions` becomes the **global cache table** keyed by `(chunk_id, signature_hash)` (not per run).
- Existing `chunk_runs` becomes the **run↔chunk usage/status** table (per run execution outcomes).
- We add new Stage‑1 tables for the **Claim Ledger** (`claims`, `claim_evidence`) and **LLM call audit** (`llm_calls`) if not already present; if an existing audit table exists, extend it instead of duplicating.

This gives:
- cross-run caching (global cache)  
- per-run observability (chunk_runs)  
- clean ledger tables (claims/evidence)  
- no need to keep legacy constraints.

### D0.2 — Run scope
**One Stage‑1 run processes exactly one document** (`document_id` required), optionally restricted to a subset of its chunks.
- Multi-document “batch runs” are **out of scope for Stage‑1 MVP**.
- A later “batch runner” can create **multiple runs**, one per document.

### D0.3 — Epistemic tags allowed in Stage 1 v1
Stage 1 v1 allows only:
- `EXPLICIT`
- `IMPLICIT`
- `MODEL_INFERRED` (rare; must include rationale + low confidence)

`RULE_INFERRED` is **explicitly not emitted by the LLM in Stage 1 v1**. Defaults like `NONEXISTENT` are applied later (Stage 3 or deterministic post-processing), not by Stage 1.

### D0.4 — “50 claims per chunk” behavior
- **No truncation. No silent dropping.**
- We set a **soft warning threshold** (default 50) and a **hard safety limit** (default 200):
  - If claims > 50: persist all, add a warning, mark chunk_run as `SUCCESS_WITH_WARNINGS`.
  - If claims > 200: mark extraction `FAILED_TOO_MANY_CLAIMS`, persist raw output, do **not** persist partial claims.

### D0.5 — Execution semantics in Stage 1
Stage 1 does **not** model operation-level atomicity/workflow semantics.
It only extracts atomic claims. (BusinessOperation and “execution semantics note” belong to Stage 3.)

---

## 1) Addressing “Gaps and Ambiguities” (critique §1.2)

### 1.1 Schema vs existing codebase
**Decision:** extend/repurpose existing tables + add ledger tables (D0.1).

**Implementation notes**
- If current `chunk_extractions` is keyed by `(run_id, chunk_id, prompt_name)`, we will:
  - add `signature_hash` column
  - change unique constraint to **`(chunk_id, signature_hash)`**
  - keep `run_id` as “first_run_id” or drop it from the cache table (see schema below).
- If you already have `pipeline_runs`, keep it and add:
  - `run_kind` (e.g., `STAGE1_EXTRACT`)
  - `config_json`, `stats_json` (or equivalent columns)
- If you already have `llm_calls`-like storage inside `chunk_extractions`, keep it there **or** split it out; the key requirement is: **raw request/response must be stored and linkable to a run + chunk + signature**.

### 1.2 Run identity and batch vs document
**Decision:** one run = one document (D0.2).

Operationally:
- `stage1_extract --doc-id X` creates a new run record each invocation (even if it results in “all cached”).
- The run record captures configuration and counts.

### 1.3 `chunk_content_hash` normalization (make it exact)
**Decision (locked algorithm):**

Given chunk text `t` (Python `str`):
1) Unicode normalize: `unicodedata.normalize("NFKC", t)`
2) Normalize newlines: replace `\r\n` and `\r` with `\n`
3) Strip trailing whitespace per line: for each line, `rstrip()`  
4) Strip leading/trailing whitespace of the entire string: `strip()`
5) Collapse runs of >2 blank lines to exactly 2 blank lines (optional but recommended; if applied, it is part of the algorithm and must not change without bumping extractor_version)

Hash:
- encode as UTF‑8 bytes
- `sha256(bytes).hexdigest()`

**Versioning rule:** any change to this normalization **requires bumping `extractor_version`**.

### 1.4 Embedding model and Qdrant collection
**Decision:**
- Claims embeddings are produced by a configurable **embedding profile**:
  - default: same embedding model already used for chunk embeddings (unless you have a better dedicated one).
- Qdrant collection for claims is **stable by name** (e.g., `claims_v1`) and **versioned by payload fields**, not by creating a new collection per run.

Add to payload:
- `embedding_model_id`
- `schema_version` / `extractor_version`
- `prompt_version`

This keeps retrieval consistent and allows filtering later.

### 1.5 `llm_calls` linkage to cache on cache hits
**Decision:**
- The global cache table (`chunk_extractions`) stores:
  - the `llm_call_id` that produced it (if any)
  - the `produced_run_id` (first run that produced it)
- Each run records **usage** via `chunk_runs` with:
  - `cache_status = CACHED|FRESH`
  - a pointer to `chunk_extraction_id`

So audit is always possible:
- “this run reused extraction #E created by run #R and LLM call #C”.

### 1.6 NOTE claim type
**Decision (v1 minimal):**
- Keep NOTE **disabled by default** in Stage 1 v1 to avoid schema drift.
- If enabled later, define it strictly:
  - `type: NOTE`
  - `value: { "text": "<short note>" }`
  - **evidence required** (NOTE is not a rule-inferred loophole)

### 1.7 Claim cap behavior (50 claims)
Addressed by D0.4 (warn at 50, hard-fail at 200; no truncation).

---

## 2) Risk mitigations (critique §1.3)

### 2.1 “Run table and observability”
Because we keep `pipeline_runs` as the canonical run table, existing scripts/dashboards remain usable.
We add `run_kind=STAGE1_EXTRACT` and ensure run status transitions are consistent.

Optional: create a SQL VIEW `stage1_runs` filtering `run_kind`, for convenience.

### 2.2 Qdrant failure and “embed later”
**Decision:** add explicit SQL tracking so we can find “not embedded” claims without querying Qdrant.

Implementation options (pick one; both are simple):
- **Option A (simplest):** `claims.embedded_at` nullable + `claims.embedding_model_id` + `claims.embedding_status`
- **Option B:** `claim_embeddings` table (claim_id, model_id, status, embedded_at, error)

Recommended for MVP: **Option A**.

The “embed_missing_claims” job queries:
- `WHERE embedding_status != 'EMBEDDED' AND run_id = <run>` (or by doc_id)

### 2.3 Repair prompt token budget
**Decision (locked):**
- Store full raw response in DB always.
- For repair calls, include at most **12,000 characters** of the raw output (configurable), preferring:
  - the first 2,000 chars (to keep header/context)
  - + the last 10,000 chars (where JSON often ends)
- In the repair prompt, explicitly state that the raw output was truncated.

### 2.4 Golden tests determinism
**Decision:**
- Golden tests compare **schema-normalized** outputs, not raw text.
- Prefer a deterministic local model (temperature=0) for CI, if available.
- If not deterministic: use “assert subset” tests (types present, evidence present, no invalid tags) rather than exact JSON equality.

---

## 3) Consistency nits resolved (critique §1.4)

### 3.1 Naming
We standardize on:
- `run_id` as PK identifier conceptually
- if the physical DB table uses `pipeline_runs.id`, map it in ORM as `run_id` (alias)

### 3.2 `subject_type` / `subject_text`
**Decision:** Stage 1 does **not** ask LLM to fill these.
- Derive lightweight subject hints in code if useful (e.g., for action claims store `target_object` and `name`).
- Canonical subject IDs are created in Stage 2.

### 3.3 `config_json` and `stats_json` queryability
We store full config for reproducibility, and also store common fields in dedicated columns where useful:
- `model_id`, `prompt_version`, `extractor_version` columns on run (or chunk_run)
This avoids relying on JSON queries in SQLite.

---

## 4) Clarifying questions — answered (critique §2)

### 2.1 Schema and existing code
**Q1. New tables vs migrate?**  
**Answer:** extend/repurpose existing run/extraction tables + add claim ledger tables; no legacy guarantees (D0.1).

**Q2. Existing unique constraint (run_id, chunk_id, prompt_name) vs (chunk_id, signature_hash)?**  
**Answer:** caching must be cross-run, so the cache uniqueness is **(chunk_id, signature_hash)**.  
Per-run execution status is stored in `chunk_runs` (run_id, chunk_id, …) with a link to the cache row.

### 2.2 Run and batch semantics
**Q3. One run multi-doc?**  
**Answer:** MVP Stage‑1: **one run = one document** (D0.2).

**Q4. `--force` behavior?**  
**Answer:** `--force` creates a new run and **bypasses cache** by adding `force_nonce=<run_id>` into the signature fingerprint.  
This keeps auditability and avoids overwriting.

### 2.3 Caching and hashing
**Q5. Exact normalization?**  
**Answer:** locked in §1.3.

**Q6. extractor_version/prompt_version source?**  
**Answer:**
- `prompt_version`: explicit semantic version string you control (e.g. `chunk_claims_extract_v1`). Also store `prompt_hash = sha256(prompt_text)` for audit.
- `extractor_version`: code/schema version constant (e.g., from package `__version__` or a `STAGE1_EXTRACTOR_VERSION` constant). Bump when schema/normalization/prompt contract changes.

### 2.4 Claims and evidence
**Q7. NOTE evidence? value shape?**  
**Answer:** NOTE disabled by default. If enabled: `value={text: ...}` and evidence required (§1.6).

**Q8. Cap at 50: reject/truncate/warn?**  
**Answer:** warn >50, fail >200, never truncate (D0.4).

**Q9. RULE_INFERRED in Stage 1?**  
**Answer:** not in v1 (D0.3).

### 2.5 Embeddings and Qdrant
**Q10. Which embedding model? fixed or selectable?**  
**Answer:** selectable by run config with a default embedding profile; record `embedding_model_id` in claims embedding metadata (§1.4).

**Q11. How to detect not embedded?**  
**Answer:** SQL tracking (`embedding_status`, `embedded_at`, `embedding_model_id`) so jobs can query missing embeddings (§2.2).

### 2.6 LLM and repair
**Q12. Repair raw output max length?**  
**Answer:** yes, cap at 12k chars with head+tail strategy (§2.3).

**Q13. Store token usage?**  
**Answer:** yes—always attempt to capture and persist for every LLM call (including repair). If provider doesn’t supply, store nulls.

### 2.7 Operations and CLI
**Q14. CLI modes?**  
**Answer:** support:
- `--doc-id` (default mode)
- `--chunk-ids` (subset)
- `--pending` (process only chunks without successful cache for current signature)
Out-of-scope: “all workspace documents” in one run; make a batch driver that creates per-doc runs.

**Q15. config_json: full config or signature-only?**  
**Answer:** store full `Stage1Config` for reproducibility; additionally store signature-driving fields in columns for easier querying.

---

## 5) Updated schema blueprint (aligned with existing tables)

> Names here are conceptual. If your DB already has these tables, prefer migrations that add/repurpose columns.

### 5.1 `pipeline_runs` (canonical run)
Add columns:
- `run_kind` (STAGE1_EXTRACT)
- `prompt_version`, `extractor_version`, `model_id`
- `config_json`, `stats_json`
- timestamps + status

### 5.2 `chunk_extractions` (global cache)
Purpose: one row per (chunk_id, signature_hash), reusable across runs.

Columns:
- `chunk_extraction_id` PK
- `chunk_id`
- `signature_hash`  (unique with chunk_id)
- `chunk_content_hash`
- `prompt_version`, `extractor_version`, `model_id`
- `params_fingerprint` (optional)
- `status` (SUCCESS|FAILED)
- `produced_run_id` (first run that created it)
- `llm_call_id` (the producing call)
- `error_type`, `error_message`
- timestamps

Unique:
- **(chunk_id, signature_hash)**

### 5.3 `chunk_runs` (per-run usage + status)
Purpose: record what happened in *this* run for *this* chunk.

Columns:
- `run_id`, `chunk_id` (unique together)
- `chunk_extraction_id` (nullable until done)
- `status` (CACHED|SUCCESS|SUCCESS_WITH_WARNINGS|FAILED)
- `attempts`, timing, error message
- timestamps

### 5.4 `llm_calls`
Either new table or extend existing.
Must include:
- run_id, chunk_id, signature_hash
- request_json, response_text, parsed_json (optional)
- tokens, latency, status, error

### 5.5 `claims` + `claim_evidence`
Add as in the original plan, plus embedding tracking:
- `embedding_status` (PENDING|EMBEDDED|FAILED)
- `embedded_at` nullable
- `embedding_model_id` nullable

---

## 6) Updated Stage 1 implementation notes (delta from original plan)

### 6.1 Cache gate with existing tables
Flow per chunk:
1) Compute signature_hash
2) Look up `chunk_extractions` by `(chunk_id, signature_hash)`:
   - if SUCCESS → mark `chunk_runs.status=CACHED` + link extraction_id, do not call LLM
   - if FAILED → decide per config whether to retry (usually yes, with attempts cap)
3) If missing:
   - insert a new cache row in `chunk_extractions` with status “pending/running” (or insert failed row after call; choose your concurrency strategy)
   - call LLM, validate, persist claims/evidence
   - update cache row to SUCCESS and link llm_call_id + produced_run_id
   - mark chunk_run SUCCESS

### 6.2 Prompt contract hard rules (enforced by validator)
- JSON only
- no RULE_INFERRED
- each claim has evidence (non-empty) unless NOTE disabled (and even NOTE requires evidence when enabled)
- `MODEL_INFERRED` requires `confidence <= 0.5` and a `rationale` field in value (add this in schema if you allow MODEL_INFERRED)

### 6.3 Embedding step safety
If Qdrant fails:
- keep claims (embedding_status remains PENDING/FAILED)
- record in run stats
- allow `embed_missing_claims --run-id` job

---

## 7) What remains intentionally out of scope for Stage 1
- Any cross-chunk dedupe/aliasing
- Any conflict resolution
- Any BusinessOperation composition
- Any default-state injection (e.g., NONEXISTENT) by the LLM

Stage 1 output should be conservative, auditable claims only.

---

## 8) Action items to apply back to the original archive plan
When you update the Stage‑1 plan archive, reflect these deltas in:
- schema file: alignment with `pipeline_runs`, `chunk_extractions`, `chunk_runs`
- hashing file: exact normalization algorithm
- prompt/schema file: disable RULE_INFERRED + define NOTE behavior (or disable NOTE)
- pipeline steps: updated cache hit auditing and embedding tracking
- repair flow: raw truncation limits
- tests: golden tests strategy and claim cap behavior
