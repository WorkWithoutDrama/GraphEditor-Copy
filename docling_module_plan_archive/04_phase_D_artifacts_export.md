# 04 — Phase D: Artifact Export & Storage (DoclingDocument → Document.*_uri)

## D0. Outcomes
- Persist **replayable** outputs so you can re-chunk without re-parsing (via DoclingDocument.load_from_json).
- Store derived outputs in file store and record URIs on **Document** (no separate artifacts table).
- Use existing Document fields: `structure_json_uri`, `plain_text_uri`, `language`, `stats_json`.

---

## D1. Output types (mapped to Document)

There is **no artifacts table**. Derived outputs are written to file store and URIs stored on Document:

- **docling JSON** (lossless) → **required** → `Document.structure_json_uri`
- **plain text** (derived) → recommended → `Document.plain_text_uri`
- **optional** (markdown, tables, etc.) → store URI in `Document.stats_json["artifacts"]["markdown_uri"]` or similar

Why structure_json_uri is required:
- enables re-chunk via `DoclingDocument.load_from_json(...)` (Phase I)
- avoids expensive re-parse when tuning chunk settings

Acceptance:
- For every PARSED run, Document gets `structure_json_uri` (unless explicitly disabled in settings).

---

## D2. Storage rules

- Write docling JSON and plain text (and optional markdown) to **FileStorePort** (path strategy e.g. by document_id or content hash).
- Set on Document:
  - `structure_json_uri` (required)
  - `plain_text_uri` (recommended)
  - `language` (from conversion metadata if available)
  - `stats_json`: structured metadata, e.g.:
    - `parser`: `{ name: "docling", version: "..." }`
    - `chunking`: settings + `chunker_version`
    - `conversion`: page_count, warnings, timings
    - optional artifact refs (e.g. `markdown_uri`)

Acceptance:
- You can fetch docling JSON later for re-chunk without re-running conversion.

---

## D3. Export mechanics

Implement an exporter that:
- input: Docling conversion result (DoclingDocument)
- output: write JSON to file store → get URI; optionally plain text and markdown
- build Document DTO: structure_json_uri, plain_text_uri, language, stats_json

Export order: JSON first (required), then plain text, then optional markdown.

Acceptance:
- Export is deterministic for same Docling result.

---

## D4. DB persistence (Document upsert)

Persist **Document** in one transaction (no bulk_upsert_artifacts):
- get_or_create or upsert Document by `(source_version_id, extractor, extractor_version)` with the new URIs and stats_json.
- Conflict strategy: if row exists, update structure_json_uri, plain_text_uri, language, stats_json (idempotent for same run).

Acceptance:
- Re-runs are safe and cheap.

---

## D5. Checkpoint

After Document is updated with derived URIs:
- update **extract_runs** `status=ARTIFACTS_STORED`

Acceptance:
- If chunking crashes, you still have structure_json_uri for debugging/retry/re-chunk.
