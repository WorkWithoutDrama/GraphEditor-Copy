# 11 — Appendix B: Error Taxonomy & Mapping

## B1. Error codes

- `UNSUPPORTED_FORMAT`
- `FILE_TOO_LARGE`
- `TOO_MANY_PAGES`
- `STORAGE_READ_FAILED`
- `STORAGE_WRITE_FAILED`
- `PARSE_FAILED`
- `EXPORT_FAILED`
- `CHUNK_FAILED`
- `TOO_MANY_CHUNKS`
- `TIMEOUT_PARSE`
- `TIMEOUT_CHUNK`
- `DB_WRITE_FAILED`
- `ARTIFACT_HASH_MISMATCH`

## B2. Mapping rules

- Validation errors → `UNSUPPORTED_FORMAT | FILE_TOO_LARGE | TOO_MANY_PAGES`
- Docling conversion exceptions → `PARSE_FAILED`
- JSON/MD export exceptions → `EXPORT_FAILED`
- Token enforcement / splitter exceptions → `CHUNK_FAILED`
- Queue publish failure → keep `CHUNKED` and record job publish error separately

## B3. Stored fields
- **extract_runs** (operational state): `error_code`, `error_message` (short, human-readable), optionally `error_details` (json)
- Document has no status/error fields; failures are tracked on extract_runs.

