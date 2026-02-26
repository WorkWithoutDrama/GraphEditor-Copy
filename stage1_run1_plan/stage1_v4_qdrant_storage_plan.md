# Plan: Store Stage‑1 v4 “Claim Cards” in Qdrant for Stage‑2 Dedup Retrieval

This plan implements **vector indexing** for the **Stage‑1 v4 minimal explicit claims** (“cards”) so Stage‑2 (dedup/normalization) can retrieve relevant prior claims quickly.

It follows our architecture decisions:
- **SQL is the source of truth** (claim ledger + evidence + run metadata)
- **Qdrant is retrieval-only** (embeddings + small payload to point back to SQL)
- **Caching/idempotency** is mandatory (do not re-embed or re-upsert unnecessarily)
- Stage‑1 remains **explicit-only**; Stage‑2 will do cross-chunk reasoning and conflict work later.

---

## 0) Scope and non-goals

### In scope
- Convert validated Stage‑1 v4 claims into **Qdrant points**
- Store embeddings and retrieval payload
- Idempotent upsert (safe to rerun)
- Minimal “card text” design tuned for Stage‑2 prompt injection
- SQL bookkeeping to track embedding/upsert status

### Out of scope
- Any dedup/normalization logic (Stage‑2)
- Any BusinessOperation composition (Stage‑3)
- Human review tooling

---

## 1) Inputs and outputs

### Input
Validated Stage‑1 output (v4 minimal explicit), persisted to SQL as `claims` + `claim_evidence`, e.g.:

- Claim types: `ACTOR`, `OBJECT`, `ACTION` (and rarely `STATE`, `DENY`)
- Evidence snippets are already substring-validated
- Some duplicates can exist (e.g., repeated ACTOR “Пользователь” across bullets)

### Output
- Qdrant collection contains one point per claim card (recommended: **one point per SQL claim**)
- Each point payload includes stable identifiers and small display text, so Stage‑2 can:
  1) retrieve top‑K similar cards via vector search
  2) fetch full claim + evidence from SQL via `claim_id`

---

## 2) Retrieval unit choice: “point per claim” (recommended)

### Why “point per claim”
- Preserves provenance: each point links to a concrete chunk + evidence
- Keeps implementation simple and fully auditable
- Stage‑2 can still dedupe results by a `dedupe_key` (see §4.3)

### Optional later upgrade
If duplicates become noisy, add a separate “aggregated card” collection later. For MVP Stage‑2, *post‑process search results* to unique by `dedupe_key` is enough.

---

## 3) Qdrant collection design

### 3.1 Collection name
Use a stable collection name, e.g.:
- `stage1_cards` (recommended)

Keep older collections only if you need historical comparability; otherwise, use payload filters by `prompt_version`/`extractor_version`.

### 3.2 Vector configuration
- distance: `Cosine`
- vector size: determined by embedding model (store it in config; validate on startup)

### 3.3 Payload schema (minimum)
Payload fields to store on every point:

**Identity / filtering**
- `claim_id` (uuid string)  ← also use as point ID
- `doc_id` (uuid/string)
- `chunk_id` (uuid/string)
- `run_id` (uuid/string)
- `claim_type` (ACTOR|OBJECT|ACTION|STATE|DENY)
- `prompt_version` (e.g., `chunk_claims_extract_v4_minimal_explicit_v2`)
- `extractor_version`
- `model_id` (LLM used for extraction)
- `embedding_model_id`
- `epistemic_tag` (EXPLICIT)

**Card text**
- `card_text` (short)
- `evidence_snippet` (short, <=300 chars)

**Fast filters (optional but helpful)**
- For ACTOR/OBJECT: `name`
- For ACTION: `actor`, `verb`, `object`

**Dedup assist**
- `dedupe_key` (string; deterministic key for Stage‑2 result grouping)

> Do **not** store full JSON in Qdrant if SQL already has it. Keep Qdrant payload small and stable.

### 3.4 Payload indexes (create once)
Create payload indexes in Qdrant for fast filtering:
- `doc_id` (keyword)
- `chunk_id` (keyword)
- `claim_type` (keyword)
- `prompt_version` (keyword)
- `extractor_version` (keyword)
- `dedupe_key` (keyword)

---

## 4) Card text + embedding text construction

Stage‑2 retrieval depends heavily on **consistent card strings**.

### 4.1 Card text templates (display + embedding base)

**ACTOR**
- `card_text = "ACTOR | <ActorName>"`
- `embedding_text = "ACTOR: <ActorName>. Evidence: <snippet>"`

**OBJECT**
- `card_text = "OBJECT | <ObjectName>"`
- `embedding_text = "OBJECT: <ObjectName>. Evidence: <snippet>"`

**ACTION**
- `card_text = "ACTION | <Actor> <Verb> <Object>"`
- If qualifiers exist: append `| q=<qual1,qual2>`
- `embedding_text = "ACTION: <Actor> <Verb> <Object>. Evidence: <bullet snippet>"`

**STATE (rare in v4)**
- `card_text = "STATE | <ObjectName> | <State>"`
- `embedding_text = "STATE: <ObjectName> is <State>. Evidence: <snippet>"`

**DENY (rare in v4)**
- `card_text = "DENY | <Actor> !<Verb> <Object>"`
- `embedding_text = "DENY: <Actor> cannot <Verb> <Object>. Evidence: <snippet>"`

### 4.2 Evidence snippet selection
For a point payload, store one representative snippet:
- Prefer the first evidence snippet
- For ACTION, prefer the **full bullet line** evidence (if your validator enforces it)

Keep full multi-evidence in SQL; Qdrant stores one snippet for preview/prompt injection.

### 4.3 `dedupe_key` definition (used by Stage‑2 to reduce duplicates)
Compute a deterministic key from **normalized value fields**:

- ACTOR: `actor::<norm(name)>`
- OBJECT: `object::<norm(name)>`
- ACTION: `action::<norm(actor)>::<norm(verb)>::<norm(object)>`
- STATE: `state::<norm(object_name)>::<norm(state)>`
- DENY: `deny::<norm(actor)>::<norm(verb)>::<norm(object)>`

Normalization (v4):
- strip whitespace
- collapse internal spaces to single space
- lowercase (RU safe) for matching

Stage‑2 retrieval can:
- take top‑K results,
- then unique them by `dedupe_key` (keep best score per key),
- then fetch SQL details for selected claim_ids.

---

## 5) SQL bookkeeping changes (minimal)

You already have a claim ledger. Add just enough fields to track indexing.

### 5.1 Add columns to `claims` (recommended)
- `embedding_status` ENUM/TEXT: `PENDING|EMBEDDED|FAILED`
- `embedded_at` datetime nullable
- `embedding_model_id` text nullable
- `qdrant_collection` text nullable (default `stage1_cards`)
- `qdrant_point_id` text nullable (store `claim_id` or explicit)
- `card_text` text nullable (store generated card_text for debugging)
- `dedupe_key` text nullable (store to avoid recompute later)

If you prefer a separate table:
- `claim_vector_index(claim_id, embedding_model_id, status, embedded_at, qdrant_point_id, error)`

### 5.2 When to set `embedding_status`
- After persisting claims: set `PENDING`
- After successful Qdrant upsert: set `EMBEDDED` + `embedded_at`
- On failures: set `FAILED` + store error message (in `llm_calls` or a new column)

---

## 6) Implementation steps

### Step 1 — Add an indexing entrypoint
Create a dedicated function/service, not embedded in “glue”:

- `index_stage1_claims_to_qdrant(run_id: UUID, *, only_pending: bool = True)`

Responsibilities:
1) Load claims for a run (or for a doc) from SQL
2) Filter to those needing indexing (`embedding_status != EMBEDDED` if only_pending)
3) Build `card_text`, `embedding_text`, `payload`, `dedupe_key`
4) Batch-embed embedding_text
5) Batch-upsert to Qdrant
6) Update SQL statuses

### Step 2 — Ensure Qdrant collection exists on startup
In your Qdrant module:
- `ensure_collection(name, vector_size, distance)`
- `ensure_payload_indexes(name, fields=[...])`

Run once at app startup or before first upsert.

### Step 3 — Build embedding batcher
Use your existing embedding client:
- Accept list[str] embedding_texts
- Return vectors
- Handle provider rate limits and retries

Batch size config:
- start with 32 or 64; tune based on model/provider.

### Step 4 — Upsert points to Qdrant (idempotent)
Point ID strategy (recommended):
- `point_id = claim_id` (stable)
Upsert payload + vector. Re-upsert is safe.

### Step 5 — Mark SQL rows as embedded
Wrap in a DB transaction per batch:
- On successful Qdrant upsert for a batch:
  - update those claim rows to `EMBEDDED`
- On failure:
  - update to `FAILED` with error, continue next batch (don’t abort run)

### Step 6 — Integrate into Stage‑1 run pipeline
After Stage‑1 extraction for a run completes:
- call `index_stage1_claims_to_qdrant(run_id)`
- If Qdrant is down:
  - keep claims in SQL with `PENDING` or `FAILED`
  - allow re-run of indexer later: `index_missing --run-id ...`

---

## 7) Handling duplicates (practical MVP policy)

Because Stage‑1 v4 may emit repeated ACTOR claims (e.g., “Пользователь” for each bullet), you have two safe options:

### Option A (default MVP): index all, dedupe on retrieval
- Index all claim points
- Stage‑2 retrieval:
  - vector search → top‑K
  - unique by `dedupe_key`
  - fetch SQL details for selected claim_ids

Pros: simplest; keeps evidence variety.  
Cons: Qdrant results may have many near-duplicates; Stage‑2 must dedupe.

### Option B (slightly better): index all ACTION claims, but only one ACTOR/OBJECT per chunk
- In the indexer, for ACTOR and OBJECT:
  - keep first occurrence per `(chunk_id, dedupe_key)`
- Always index ACTION claims (they carry the most useful context)

Pros: lower noise, better retrieval diversity.  
Cons: minor extra logic.

Recommendation: **Option B** for ACTOR/OBJECT, keep ACTION full.

---

## 8) Error handling and resilience

### 8.1 Qdrant unavailable
- Do not fail Stage‑1 extraction.
- Mark embedding_status as `FAILED` and record error.
- Provide a CLI/job: `embed_missing_claims --run-id <id>`.

### 8.2 Embedding errors / dimension mismatch
- Validate returned vector length equals collection vector size.
- On mismatch: mark batch failed, stop (configuration error).

### 8.3 Payload size / bad unicode
- Keep `card_text` and `evidence_snippet` short.
- Store full evidence in SQL only.

---

## 9) CLI / operational tooling

Add CLI commands:

1) `stage1_index_qdrant --run-id <id> [--all|--pending]`
2) `qdrant_recreate_collection --name stage1_cards` (dangerous; dev only)

Also add lightweight stats printouts:
- claims_total, pending, embedded, failed

---

## 10) Tests

### Unit tests
- `card_text` generation per claim type
- `dedupe_key` normalization and stability
- indexer selects correct claims (pending only)
- SQL status transitions

### Integration test (with test Qdrant)
- Run indexing on a run with a few claims
- Verify points exist with:
  - correct `claim_id` as point id
  - payload fields set
  - searchable by `doc_id` filter
- Verify rerun is idempotent (no new SQL updates besides timestamps)

---

## 11) Stage‑2 retrieval contract (what this enables)
Stage‑2 will query Qdrant with:
- query vector from the new claim’s embedding_text
- filters:
  - same `doc_id` (optional; or across all docs if desired)
  - `claim_type` (e.g., only ACTION when normalizing actions)
  - same `prompt_version` or compatible versions

Then Stage‑2 will:
- unique by `dedupe_key`
- fetch corresponding SQL claims + evidence for prompt injection and dedup decisions

This keeps Qdrant purely as an index and SQL as the authoritative ledger.

---

## 12) Definition of Done
- After a Stage‑1 v4 run, all persisted claims are indexed in `stage1_cards` (or marked failed with reason).
- Qdrant payload contains `claim_id`, `doc_id`, `chunk_id`, `claim_type`, `dedupe_key`, and `card_text`.
- Stage‑2 can retrieve top‑K similar cards and fetch their evidence from SQL via `claim_id`.
- Re-running the index step does not duplicate work (idempotent).
