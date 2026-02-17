# Docling Module — Implementation Plan Archive

Date: **2026-02-16**  
Scope: **File ingestion → Docling parse → derived artifacts (Document.*_uri) → chunking → SQL persistence → handoff to embeddings/vector pipeline**  
**Integration:** Aligned with existing **Document** / **Chunk** models and **extract_runs** for FSM (see **13_integration_addendum.md** and **CRITIQUE.md**).

This archive is written to be **consistent with**:
- our async app style (non-blocking orchestration; heavy work in workers/threads),
- your existing **SQL DB module** (SQLAlchemy + upsert/bulk patterns; existing Document/Chunk schema),
- your existing **vector DB module** (Qdrant; collection naming owned by vector module; handoff includes workspace_id + embedding_set_id).

## Archive layout

```text
docling_module_plan_archive/
  00_README.md
  01_phase_A_foundation.md
  02_phase_B_inputs_storage.md
  03_phase_C_docling_conversion.md
  04_phase_D_artifacts_export.md
  05_phase_E_chunking.md
  06_phase_F_chunk_persistence.md
  07_phase_G_handoff_embeddings.md
  08_phase_H_tests_observability.md
  09_phase_I_rollout_backfill.md
  10_appendix_A_api_contracts.md
  11_appendix_B_error_taxonomy.md
  12_appendix_C_config_reference.md
  13_integration_addendum.md
  CRITIQUE.md
```

## How to read / implement
1. Start with **Phase A** to wire module boundaries, settings, and idempotency.
2. Implement in order through **Phase G** (end-to-end ingestion that enqueues embedding).
3. Add **Phase H** tests/observability before rolling to prod.
4. Use **Phase I** if you need backfill / re-chunk / re-embed flows.

## Non-goals
- Embedding computation itself (owned by embeddings module).
- Direct Qdrant schema design (owned by vector module), except the handoff contract.

## Docling references used (docs)
- DocumentConverter entry point and limits. citeturn0search0turn0search14  
- Chunking concepts, HybridChunker, contextualization/serialization. citeturn0search4turn0search1turn0search2

