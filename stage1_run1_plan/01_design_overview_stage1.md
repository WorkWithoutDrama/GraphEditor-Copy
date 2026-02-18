# Stage 1 Design Overview — Chunk → Claim Ledger

## Pipeline sketch

**Inputs**
- `Document` (already ingested)
- `Chunks` stored in SQL (id, doc_id, text, metadata)

**Processing**
1) Select chunks to process (uncached)
2) For each chunk:
   - build extraction prompt (chunk-only)
   - call LLM
   - parse/validate strict JSON
   - write claims + evidence + provenance to SQL
   - embed claim texts and upsert to Qdrant
3) Mark chunk extraction status (success/fail) with metadata

**Outputs**
- SQL: `claims`, `claim_evidence`, `chunk_extractions`, `llm_calls`, `runs`
- Qdrant: `claims` collection for retrieval (Stage 2+)

---

## Core design decisions (why)

### 1) Store claims (not “truth”)
Stage 1 writes **claims** that can be conflicting or duplicated.  
This makes later normalization and human review possible.

### 2) Chunk-only extraction
Stage 1 must not inject prior claims as context, to avoid:
- anchoring on old mistakes
- reinforcing model-inferred guesses

### 3) Evidence-first
Every claim is grounded to a chunk snippet.  
This supports:
- admin review later
- conflict resolution later
- trustworthiness and debugging now

### 4) Append-only with tombstones, not deletion
Even if later stages dedupe/supersede, Stage 1 should preserve:
- what was extracted
- when and by which prompt/model
- raw response

---

## Claim categories (v1)
Stage 1 extracts atomic claims such as:

- `ACTOR` — role/system participant
- `OBJECT` — business object type
- `STATE` — object state label
- `ACTION` — atomic action (business goal, actor allowed, target object, allowed states, effect state/no-change)
- `DENY` — actor explicitly cannot perform an action (authorization denial)
- `NOTE` — (optional) important business constraint that doesn't fit yet (keep minimal)

**Important:** Stage 1 should avoid deep composition.  
If the chunk describes a “macro” operation (“Publish”), Stage 1 may still emit multiple atomic action claims if explicitly stated; otherwise emit minimal action claim(s) and leave composition for later stages.

---

## Provenance model
Every claim stores:
- `run_id` and `chunk_id`
- `prompt_version` and `model_id`
- `epistemic_tag` (`EXPLICIT`, `IMPLICIT`, `RULE_INFERRED`, `MODEL_INFERRED`)
- evidence snippet(s) with offsets when possible

---

## Qdrant usage (Stage 1 only)
Stage 1 writes embeddings for claims so Stage 2 can:
- retrieve similar claims quickly
- compare evidence snippets
- dedupe/normalize

Stage 1 **must not** query Qdrant or use retrieval for extraction.

---

## Idempotency boundary
Stage 1 caching key must include:
- `chunk_content_hash` (normalized)
- `prompt_version`
- `extractor_version` (code version or schema version)
- `model_id` (provider/model)
- any important inference settings (temperature, etc. if they matter)

If a cached successful extraction exists for that key:
- skip LLM call
- reuse persisted claim IDs
