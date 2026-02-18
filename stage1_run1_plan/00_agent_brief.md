# Stage 1 (Run-1) — Chunk → Claims Extraction (Implementation Plan)

## Why this document exists
We already have:
- SQL DB module (chunks stored)
- Vector DB module (Qdrant)
- Docling-based chunking module
- LLM client module (LiteLLM; local Ollama + Gemini)
- A temporary “glue” orchestrator for proof-of-concept

Now we implement the **first robust run** of the real pipeline: **Stage 1 (Run‑1)**.

This plan is written as a task brief for an engineer/agent who will implement it.  
**Important:** treat existing glue code as disposable. **No legacy compatibility guarantees.** Prefer clean architecture and correctness.

---

## High-level goal
Given already-stored document chunks, run an **LLM-based extractor** that produces a **Claim Ledger**:

- Many small, atomic **claims** per chunk (actors, objects, states, action rules, transitions, denials)
- Each claim carries **evidence** (snippet + chunk reference) and **epistemic tag**
- Claims are stored in **SQL** as the authoritative ledger
- Claims are embedded and indexed in **Qdrant** for later stages (normalization/composition)

This run must be:
- **Idempotent / cacheable**: same chunk + same prompt/model/version → do not call LLM again
- **Auditable**: store raw LLM response, validation errors, evidence, and run metadata
- **Conservative**: do not invent. If not supported by the chunk, do not output the claim (or mark as model-inferred with rationale).

---

## What Stage 1 is (and is not)

### Stage 1 is
- Chunk-level extraction only (“chunk-only context”)
- Produces **claims**, not “final domain objects”
- Stores evidence and provenance
- Creates embeddings for claims (retrieval index)

### Stage 1 is NOT
- Cross-chunk normalization / alias resolution (Stage 2 later)
- BusinessOperation composition from atomic actions (Stage 3 later)
- Human review UI or conflict resolution UI (but it must store enough data for them)

---

## Definition of Done
For a given document (or a batch of documents), Stage 1 can be executed such that:

1) For each chunk, we either:
   - reuse cached successful extraction, or
   - call LLM once (with retries/repair if needed) and persist the result

2) For each successful extraction, the system persists:
   - claim records in SQL (ledger)
   - evidence snippets linked to chunks
   - run + prompt + model metadata
   - raw LLM output (for audits and debugging)
   - claim embeddings in Qdrant (with payload for filtering later)

3) Stage 1 can be re-run safely:
   - it should skip work already done (cache hit)
   - it should not duplicate claims unless configured to “append-only” for experiments

---

## Consistency requirements (MVP strictness)
- Output must conform to a **strict JSON schema** (validated by Pydantic).
- Every claim must have:
  - `type`
  - structured `value` (type-specific)
  - `epistemic_tag`
  - at least one evidence snippet OR an explicit `rule_id` when evidence is not applicable (rare, rule-based only).
- If the model is uncertain: prefer **omitting** the claim over guessing.
- If a claim is guessed: it must be tagged `MODEL_INFERRED` with a rationale.

---

## Performance / caching principles
- Chunk extraction is **expensive** → cache at chunk level.
- Reuse cached results when the **input hash and prompt+model signature** match.
- Persist embeddings once per claim; avoid re-embedding duplicates unless explicitly requested.

---

## Deliverables produced by this plan
- New “stage1” orchestration entrypoint (CLI or callable)
- New SQL tables (or migrations) for claims + evidence + run metadata + caching keys
- Prompt pack (v1) + schema validators + repair flow
- Qdrant indexing of claims
- Tests (schema validation, caching behavior, and 1–2 golden chunks)
