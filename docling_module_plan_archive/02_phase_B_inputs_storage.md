# 02 — Phase B: Inputs & Enqueue (SourceVersion → extract_runs QUEUED)

## B0. Outcomes
- Accept ingest request keyed by **workspace_id**, **source_version_id**, **embedding_set_id**.
- **Raw file is owned by SourceVersion** (already persisted); Docling does not store raw — it only **reads** from SourceVersion’s URI/stream later in the worker.
- Create/update **extract_runs** row (status `QUEUED`) and enqueue **docling.extract** job.
- Return immediately (parsing runs in worker).

---

## B1. Input contract

Docling module accepts:
- `workspace_id` (required; tenant boundary)
- `source_version_id` (required; identifies the source version whose raw file is already stored)
- `embedding_set_id` (required for handoff; used to resolve tokenizer and target collection)

Optional for worker: source URI or stream from SourceVersion storage (worker resolves from source_version_id to read raw bytes).

Acceptance:
- The module can be driven by API (after upload creates SourceVersion), background jobs, or backfill tasks.

---

## B2. Idempotency

Idempotency key: `(workspace_id, source_version_id, extractor="docling", extractor_version)`.
- Stored in **extract_runs** (unique on these fields).
- Document row is created in the **worker** after parse (Phase C/D) with same natural key.

Acceptance:
- Same source_version + same extractor version dedupes correctly; no duplicate Document rows.

---

## B3. Raw file storage (none in Docling)

**Raw file is owned by SourceVersion.** Docling module:
- does **not** store raw files;
- **reads** from SourceVersion’s stored URI/stream in the worker when running conversion (Phase C).

FileStorePort in Docling is used only for **derived** outputs (docling JSON, plain text, etc.) in Phase D.

Acceptance:
- No duplicate raw storage; single source of truth for raw content.

---

## B4. DB writes (API path)

- **extract_runs:** get_or_create run for `(workspace_id, source_version_id, extractor, extractor_version)` with `status=QUEUED`.
- Use conflict-safe upsert (e.g. ON CONFLICT DO NOTHING or DO UPDATE) so re-enqueue is safe.

Acceptance:
- Re-enqueue produces ~O(1) DB work, not O(n) exceptions.

---

## B5. API/Worker wiring (non-blocking)

**API process:**
- Validate request (workspace_id, source_version_id, embedding_set_id).
- Ensure SourceVersion exists and raw file is available.
- Create/update extract_runs → `QUEUED`.
- Enqueue **docling.extract** job (with required envelope: job_id, workspace_id, source_version_id, etc.; see Appendix A).
- Return `{source_version_id, extractor="docling", extractor_version, status="QUEUED"}`.

**Worker process** (Phase C onward): consumes docling.extract, runs conversion → export → chunking → persist Document/Chunks → enqueue embed job.

Acceptance:
- Ingest endpoint remains fast; parsing is resilient to restarts (job can be retried).

