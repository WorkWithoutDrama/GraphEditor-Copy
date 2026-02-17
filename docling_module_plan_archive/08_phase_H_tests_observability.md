# 08 — Phase H: Tests, Observability, and Performance Guardrails

## H0. Outcomes
- Confidence that ingestion is deterministic and idempotent.
- Metrics + logs show where time goes.
- Large documents don’t break the service.

---

## H1. Unit tests (fast)

1) `ids.py`
- same inputs → same ids
- changing settings → changed chunk ids (if settings included in hashing)

2) `chunking.py`
- hard max tokens enforcement works
- overlap behaves deterministically

3) `repo.py`
- bulk upsert uses conflict handling (no IntegrityError loops)

Acceptance:
- Tests run in < 2s.

---

## H2. Integration tests (realistic docs)

Corpus:
- small PDF with headings + tables
- DOCX
- Markdown
- scanned PDF (optional OCR)

Assertions:
- extract_runs statuses progress correctly
- Document.structure_json_uri exists
- chunk_count > 0
- no chunk exceeds max_tokens
- rerun is idempotent (same counts, no duplicates)

Acceptance:
- One command spins up DB + runs ingestion end-to-end.

---

## H3. Observability

### Logs (structured)
Log at each checkpoint:
- `document_id`, `sha256`, `stage`, `duration_ms`, `chunk_count`

### Metrics
- `docling_parse_seconds` histogram
- `docling_export_seconds` histogram
- `docling_chunk_seconds` histogram
- `chunks_per_document` histogram
- `ingest_failures_total{error_code=...}` counter

Acceptance:
- You can answer: “what is slow” and “what fails” from dashboards.

---

## H4. Performance guardrails

- Set a hard cap on:
  - max file size
  - max pages
  - max total extracted text chars
  - max chunks per document (e.g., 10k)

- Add circuit-breakers:
  - if parse exceeds time limit → fail with `TIMEOUT_PARSE`
  - if chunk count exceeds limit → fail with `TOO_MANY_CHUNKS`

Acceptance:
- Worst-case documents cannot take down the worker.

---

## H5. Security and operations (AuthZ, rate limiting, backfill)

- **AuthZ:** Who can enqueue extraction and run backfill is enforced at the **API layer**. Worker trusts jobs already authorized by API.
- **Rate limiting:** Apply at ingest endpoint (per workspace/user) and/or at job consumption (max concurrent jobs per workspace).
- **Backfill / admin:** Backfill endpoints and tasks (re-run failed extracts, re-chunk for new chunker_version, re-embed) must be **admin-only**.

