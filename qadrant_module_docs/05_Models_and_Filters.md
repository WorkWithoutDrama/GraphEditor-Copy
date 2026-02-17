# 05 — Models and Filters (typed, compiled)

We will not allow “raw dict payloads” to leak into services.
Everything is typed in Pydantic models, then compiled into Qdrant models at the boundary.

---

## 5.1 Pydantic models

### ChunkPoint (input to upsert)

Fields:
- `id: UUID`  (point ID, equals chunk_id)
- `vector: list[float]`
- `payload: ChunkPayload`

### ChunkPayload

Required:
- `workspace_id: str`
- `document_id: str`  (store as string for portability)
- `chunk_index: int`
- `chunk_hash: str`
- `created_at: datetime`

Optional:
- `source: str | None`
- `tags: list[str] | None`

### ScoredChunk (output from search)

- `chunk_id: UUID`
- `score: float`
- `payload: ChunkPayload | MinimalPayload`

---

## 5.2 Filter abstraction (VectorFilter)

Create a typed filter model so callers cannot forget workspace filtering.

### VectorFilter

- `workspace_id: str` (required)
- `document_id: str | None`
- `source: str | None`
- `tags_any: list[str] | None`
- `created_after: datetime | None`
- `created_before: datetime | None`
- `chunk_ids: list[UUID] | None`  (rare; for “search within a set”)

Rules:
- Repo always enforces `workspace_id` in every compiled filter.
- Repo rejects empty workspace_id.

### Compiler

`compile_filter(f: VectorFilter) -> qdrant_client.models.Filter`

Implementation guidelines:
- `workspace_id` is always in `must`
- Add optional constraints as `must` conditions
- Tags: `must` with `MatchAny` or `MatchValue` depending on desired semantics
- Time ranges: `Range(gte=..., lte=...)`

---

## 5.3 Canonical filter recipes (examples)

1) Tenant + document:
- must: workspace_id == X
- must: document_id == D

2) Tenant + time window:
- must: workspace_id == X
- must: created_at in [after, before]

3) Tenant + tags:
- must: workspace_id == X
- must: tags has any of [..]

---

## 5.4 Payload size discipline

- Payload must be < ~2–4 KB per point in steady state (rule of thumb).
- If you need large metadata, store it in SQL and join on chunk_id.

