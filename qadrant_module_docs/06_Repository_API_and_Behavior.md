# 06 — Repository API and Behavior

## Interface
`QdrantVectorRepo` methods (async):

- `ensure_collection(embedding_set_slug) -> None`
- `upsert(points: list[ChunkPoint], embedding_set_slug) -> None`
- `search(query_vector, embedding_set_slug, filter: VectorFilter, limit: int, offset: int|None) -> list[ScoredChunk]`
- `delete_by_filter(embedding_set_slug, filter: VectorFilter) -> int`
- `delete_by_document(embedding_set_slug, workspace_id, document_id) -> int`
- `scroll_ids(embedding_set_slug, filter: VectorFilter, batch: int) -> AsyncIterator[list[UUID]]`
- `health() -> bool`

## Batch-first rules
- Upsert in batches (default 256; tune by vector size)
- Delete by filter (server-side)
- Search returns IDs + scores + small payload subset

## Idempotency rules
- Point ID == SQL chunk_id
- Upsert overwrites existing point with same ID
- Re-running a VECTOR_INDEX stage is always safe

## Error semantics
- Collection mismatch → explicit typed error → pipeline marks stage failed (action: migrate)
- Transient network errors → retries → if still failing, stage failed but retryable

