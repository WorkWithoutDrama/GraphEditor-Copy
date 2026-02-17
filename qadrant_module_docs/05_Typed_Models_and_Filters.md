# 05 — Typed Models and Filters

## ChunkPoint (Pydantic)
Fields:
- `id: UUID`  (Qdrant point id)
- `vector: list[float]`
- `payload: ChunkPayload`

## ChunkPayload (Pydantic)
Minimum:
- `workspace_id: str`
- `document_id: str` (UUID or string)
- `chunk_id: str` (optional redundancy)
- `chunk_index: int`
- `embedding_set: str` (optional; usually in collection name)
- `created_at: datetime`
Optional:
- `source: str`
- `tags: list[str]`

## ScoredChunk (DTO)
- `chunk_id: UUID`
- `score: float`
- `payload: dict` (only whitelisted subset)
- optional `vector: None` (we usually don’t return vectors)

## VectorFilter abstraction
Do NOT accept raw Qdrant filters outside the repo layer.
Create our own filter AST, e.g.:

- `Workspace(workspace_id)`
- `Document(document_id)`
- `And([...])`
- `Or([...])`
- `HasTag(tag)`
- `CreatedAfter(dt)` / `CreatedBefore(dt)`

Repo compiles to Qdrant filter objects.

## Tenant enforcement
If settings say `workspace_enforced=True`:
- every search/delete must include workspace filter
- repo throws if missing (fail closed)

This aligns with our multitenant-safe architecture.

