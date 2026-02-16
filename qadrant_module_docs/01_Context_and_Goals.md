# 01 — Context and Goals

## Architecture alignment
Our app pipeline (async) is:

1) **Document ingestion**  
2) **Docling normalization**  
3) **Chunking**  
4) **Embedding + ranking prep** (embedding generation)  
5) **Storage**  
   - SQL: documents, chunks, embeddings metadata, run_items stage tracking
   - Qdrant: vector index for retrieval

This module is responsible ONLY for the **Qdrant Storage** portion of step (5), and the worker stage that writes vectors into Qdrant.

## Design goals
- **Async-first**: use `AsyncQdrantClient`, batch operations only.
- **Idempotent**: retries are safe; upserts overwrite deterministically.
- **Typed boundary**: service layer never deals with raw Qdrant dicts.
- **Filterable multitenancy**: enforce `workspace_id` filter by default.
- **Operational safety**: ensure_collection(), index creation, safe migrations.
- **Testable**: docker-based integration tests.

## Non-goals (explicit)
- Generating embeddings
- Choosing prompts/models
- Chunking text
- Reranking and scoring logic (outside Qdrant)

