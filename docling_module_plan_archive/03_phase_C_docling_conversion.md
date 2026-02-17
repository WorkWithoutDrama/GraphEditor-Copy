# 03 — Phase C: Docling Conversion (raw file → DoclingDocument)

## C0. Outcomes
- Convert raw bytes/stream/path into Docling structured document.
- Enforce file/page limits at conversion time.
- Capture conversion metadata + warnings.
- Persist parse result status checkpoint.

Docling entry point:
- `DocumentConverter` is the main conversion API. citeturn0search0
- For binary streams, Docling supports `DocumentStream(BytesIO(...))`. citeturn0search14

---

## C1. Converter initialization

Create a `ConverterFactory` that builds a singleton converter:
- `allowed_formats` from settings
- `format_options` if you need per-format flags (e.g., PDF OCR options)

Keep converter creation at module startup (worker init) to avoid per-job overhead.

Acceptance:
- Converter init happens once per worker process, not per file.

---

## C2. Source loading strategies

Worker resolves raw input from **SourceVersion** (raw file owned there; see Phase B). Then:

1) Read stream from SourceVersion’s storage → write to local temp file → pass path to converter (avoids loading huge files fully in memory).
2) For small files: use `DocumentStream` (in-memory) conversion. citeturn0search14

Decision:
- Implement both; choose by byte_size threshold.

Acceptance:
- Large documents do not OOM the worker.

---

## C3. Concurrency control

Parsing is typically CPU-heavy.
Do:
- In worker process, set max parallel parses:
  - `asyncio.Semaphore(settings.parse_concurrency)`
- Run conversion in:
  - process pool (best isolation) OR
  - `asyncio.to_thread(...)` if you already run ingestion in dedicated worker processes.

Rule:
- never run Docling conversion on the main API event loop thread.

Acceptance:
- API stays responsive under load.

---

## C4. Conversion call and limits

Call converter with:
- `max_file_size` and `max_num_pages` as hard safety limits. citeturn0search14

On success:
- update **extract_runs** `status=PARSED`
- store basic metadata in run or pass to Phase D for Document.stats_json:
  - `page_count`, `language` (if available), `warnings`

On failure:
- map to error taxonomy (Appendix B)
- update **extract_runs** `status=FAILED` with `error_code`, `error_message`

Acceptance:
- A malformed PDF fails cleanly and leaves the run in FAILED state with reason.

---

## C5. Re-parse policy and version pinning

Add a policy in settings:
- `allow_reparse_if_failed` (default true)
- `force_reparse` (manual/admin only)

Rule:
- if run is PARSED or later, do not re-parse unless forced.
- if run is FAILED, retries should reattempt conversion.

**Version pinning:** Pin Docling (and docling-core) in the lockfile. Store runtime version in `Document.extractor_version` and in `Document.stats_json["parser"]["version"]`. Recommend testing against a known stable version (e.g. docling 2.73.x).

Acceptance:
- No accidental “double parsing”; Docling version is traceable.

