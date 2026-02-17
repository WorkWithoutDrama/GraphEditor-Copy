# 09 — Phase I: Rollout, Backfill, Re-chunking, and Versioning

## I0. Outcomes
- Safe rollout to production.
- Ability to reprocess documents when you tune chunk settings or upgrade Docling.
- No vector DB corruption during reprocessing.

---

## I1. Version fields (existing schema)

- **Parser version:** Store in `Document.extractor_version` (Docling runtime version) and in `Document.stats_json["parser"]["version"]`.
- **Chunker version:** `chunker_version = sha256(json.dumps(chunk_settings, sort_keys=True))`. Store in `Document.stats_json["chunking"]` and in each `Chunk.meta_json["chunker_version"]`.

Acceptance:
- You can compare chunks produced by different settings.

---

## I2. Re-chunk strategy (from stored Docling JSON)

**Preferred:** Re-chunk from **Document.structure_json_uri** (no re-parse). Docling supports **DoclingDocument.load_from_json(path)**:
1) Load JSON from structure_json_uri
2) Run chunker with new settings → new chunker_version
3) Insert chunks (new chunk_hashes)
4) Enqueue embeddings for the new chunker_version

**Fallback:** If structure_json_uri is missing or unreadable, reconvert from source (SourceVersion).

Expose a service method: **rechunk(workspace_id, document_id, embedding_set_id, chunk_settings)**.

Acceptance:
- Tuning chunk settings does not require re-upload when structure_json_uri exists.

---

## I3. Qdrant coexistence policy (vector module owns naming)

Collection naming is owned by the **vector/embeddings module** (e.g. workspace_id + embedding_set_id + schema_version). Options for multiple chunker versions:
- Separate collections per chunker_version (if vector module supports it), or
- Single collection with payload field `chunker_version`; queries filter by version.

Docling only hands off workspace_id, embedding_set_id, document_id, chunker_version; vector module decides layout.

Acceptance:
- You can roll back chunking changes without losing old index.

---

## I4. Backfill job (admin-only)

Create an **admin-only** task:
- find **extract_runs** with status FAILED or QUEUED and enqueue docling.extract
- find runs CHUNKED but not fully indexed and enqueue embeddings

Acceptance:
- You can “heal” the system after downtime; only admins can run backfill.

