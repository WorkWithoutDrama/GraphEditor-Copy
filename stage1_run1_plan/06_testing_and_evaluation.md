# Testing + Evaluation Plan (Stage 1)

## Unit tests
1) **Signature hash**
- same inputs → same hash
- changing prompt_version/model_id → different hash

2) **Schema validation**
- valid JSON passes
- missing evidence fails
- invalid claim type fails

3) **Repair flow**
- raw output with minor JSON issues repaired successfully
- unrepaired output marks extraction FAILED and persists raw response

4) **DB persistence**
- claims and evidence created with correct foreign keys
- chunk_extractions uniqueness gate works

---

## Integration tests
Use a tiny test document:
- 3–5 chunks with simple rules (Admin signs Document, User cannot sign)
Run Stage 1 end-to-end against:
- SQLite test DB
- Qdrant test instance (or mocked client)

Assertions:
- number of claims created
- evidence snippets non-empty
- Qdrant points created with expected payload fields

---

## Golden tests (high value)
Pick 1–2 “golden chunks” and store:
- expected validated JSON output (or a normalized subset)
Compare actual output after schema normalization.

Because LLM outputs can vary, compare with:
- stable fields only (types, key presence, not exact wording)
- or run with deterministic model settings

---

## Evaluation checklist (manual, MVP)
After running Stage 1 on a real design doc:
- Are claims grounded to evidence?
- Are there many MODEL_INFERRED claims? (should be rare)
- Are action claims business-level (not UI steps)?
- Is the number of claims per chunk reasonable?
- Does rerun hit cache and avoid new LLM calls?

Record findings as issues to adjust prompt/schema (bump versions).
