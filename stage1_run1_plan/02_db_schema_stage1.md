# SQL Schema Additions for Stage 1 (Claim Ledger + Caching)

> Adjust naming to your project conventions. The important part is relationships and indices.

## 1) `runs`
Represents one execution of Stage 1 over one document or batch.

**Fields**
- `run_id` (uuid, pk)
- `run_kind` (e.g., `STAGE1_EXTRACT`)
- `doc_id` (nullable if batch)
- `status` (`RUNNING|SUCCESS|PARTIAL|FAILED`)
- `started_at`, `finished_at`
- `config_json` (prompt version, model id, settings)
- `stats_json` (chunks_total, chunks_cached, chunks_success, chunks_failed, token usage)

**Indices**
- `(run_kind, doc_id, started_at desc)`

---

## 2) `chunk_extractions`
Caching + status per chunk per extraction signature.

**Fields**
- `chunk_extraction_id` (uuid, pk)
- `chunk_id` (fk)
- `run_id` (fk)
- `signature_hash` (varchar, indexed)
- `prompt_version`
- `extractor_version`
- `model_id`
- `status` (`CACHED|SUCCESS|FAILED|SKIPPED`)
- `attempts` (int)
- `error_type`, `error_message` (nullable)
- `llm_call_id` (fk, nullable)
- `created_at`

**Uniqueness**
- unique `(chunk_id, signature_hash)`  ✅ (this is the cache gate)

**Indices**
- `(chunk_id, created_at desc)`
- `(signature_hash)`

---

## 3) `llm_calls`
Auditable record of LLM requests/responses.

**Fields**
- `llm_call_id` (uuid, pk)
- `run_id` (fk)
- `chunk_id` (fk, nullable)
- `provider` (ollama/gemini/…)
- `model` (name)
- `request_json` (the prompt, parameters)
- `response_text` (raw)
- `response_json` (nullable, parsed)
- `latency_ms`, `prompt_tokens`, `completion_tokens` (if available)
- `status` (`SUCCESS|FAILED`)
- `error_message` (nullable)
- `created_at`

---

## 4) `claims`
The central claim ledger table.

**Fields**
- `claim_id` (uuid, pk)
- `run_id` (fk)
- `chunk_id` (fk)
- `claim_type` (enum/string: ACTOR/OBJECT/STATE/ACTION/DENY/NOTE)
- `subject_type` (optional; for later grouping)
- `subject_text` (optional; canonical comes later)
- `predicate` (optional)
- `value_json` (json)
- `epistemic_tag` (EXPLICIT/IMPLICIT/RULE_INFERRED/MODEL_INFERRED)
- `rule_id` (nullable)
- `confidence` (nullable float)
- `review_status` (UNREVIEWED by default)
- `superseded_by` (nullable fk to claims)
- `created_at`

**Indices**
- `(chunk_id)`
- `(claim_type)`
- `(review_status)`
- `(superseded_by)`
- For later conflict grouping (optional now): `(subject_text, predicate)`

---

## 5) `claim_evidence`
Many-to-one evidence snippets for each claim.

**Fields**
- `evidence_id` (uuid, pk)
- `claim_id` (fk)
- `chunk_id` (fk)
- `snippet_text` (text)
- `char_start`, `char_end` (nullable)
- `created_at`

**Indices**
- `(claim_id)`

---

## Migration notes
- Prefer alembic migration with forward-only changes.
- Ensure SQLite supports required indices and uniqueness.
- Keep `value_json` flexible (Stage 1 schema may evolve).
