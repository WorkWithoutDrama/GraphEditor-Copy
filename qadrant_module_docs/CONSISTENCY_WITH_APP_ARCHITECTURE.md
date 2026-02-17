# Consistency with the App Architecture (derived in our chat)

## Architecture summary (from our discussion)
- Async pipeline:
  Ingestion → Docling normalization → Chunking → Embedding/Ranking → Storage
- SQLAlchemy + Pydantic (+ PydanticAI in the app layer)
- `events` append-only + `run_items` current status via UPSERT with uniqueness:
  UNIQUE(run_id, stage, target_type, target_id)
- Quadrant/Qdrant is the vector store
- Stage idempotency and restartability are critical

## Where this Qdrant module fits
- It is the vector-DB part of the **Storage** step.
- It is invoked by an async **VECTOR_INDEX worker** driven by `run_items`.

## Consistency checklist
✅ Async-first: uses AsyncQdrantClient, batch operations  
✅ Idempotent: point_id == chunk_id, safe upsert retries  
✅ Stage tracking: integrates with run_items UPSERT flow  
✅ Separation of concerns: no chunking/embedding logic in vectorstore module  
✅ SQL is source of truth: vectors can be rebuilt/reindexed from SQL  
✅ Multitenancy: enforced workspace filter by default  
✅ Operational safety: ensure_collection() + schema mismatch detection + safe migrations  
✅ Testing: docker integration tests

## Assumptions you must align in SQL
- Prefer chunk_id as UUID (or map to uint64)
- Have a stable embedding_set slug and its vector params in SQL/config
- Have a chunk_embedding record (or equivalent) to serve as VECTOR_INDEX target identity

If any of these differ in your current schema, only the plumbing changes; the module behavior stays consistent.

