# 06 — Repository API (async, batch-first, idempotent)

This is the main contract between services and Qdrant.

---

## 6.1 Interface (Protocol)

```python
class VectorStoreRepo(Protocol):
    async def ensure_ready(self) -> None

    async def upsert_points(self, points: list[ChunkPoint]) -> None
    async def delete_by_document(self, workspace_id: str, document_id: str) -> int
    async def delete_by_filter(self, flt: VectorFilter) -> int

    async def search(
        self,
        query_vector: list[float],
        flt: VectorFilter,
        limit: int,
        *,
        with_payload: bool = True,
        score_threshold: float | None = None,
    ) -> list[ScoredChunk]

    async def scroll_ids(
        self,
        flt: VectorFilter,
        batch_size: int = 1024,
    ) -> "AsyncIterator[list[UUID]]"

    async def count(self, flt: VectorFilter) -> int
    async def health(self) -> bool
```

## 6.2 Concrete implementation: QdrantVectorStoreRepo

Constructor dependencies:
- `client: AsyncQdrantClient`
- `spec_resolver: EmbeddingSetSpecResolver` (maps embedding_set_name/id → CollectionSpec)
- `settings: VectorStoreSettings`

### 6.2.1 ensure_ready()

- Builds CollectionSpec(s) for all active embedding sets
- Calls ensure_collection() for each
- If mismatch → raise MigrationRequired (explicit)

### 6.2.2 upsert_points(points)

Rules:
- Points must belong to **one embedding set / one collection per call** (locked by D2).
- Validate all points have same target collection.
- Batch by `settings.default_upsert_batch`.

Algorithm:
1) For each batch:
   - Convert to Qdrant `PointStruct`
   - Call `client.upsert(collection_name, points=batch, wait=True)`
2) Any transient errors → retry with exponential backoff (see 09)

Idempotency:
- Same `id` overwrites vector/payload → safe retry.

### 6.2.3 search(query_vector, flt, limit, ...)

Algorithm:
1) compile filter
2) call `client.search(...)` with:
   - collection_name
   - query_vector
   - limit
   - filter
   - with_payload flag
   - score_threshold if set
3) Map results to `ScoredChunk`

Hard rule:
- Enforce workspace_id in filter (reject if missing)

### 6.2.4 delete_by_document(workspace_id, document_id)

Implementation:
- Build VectorFilter(workspace_id=..., document_id=...)
- Use `delete_by_filter`

### 6.2.5 delete_by_filter(flt)

Algorithm:
1) compile filter
2) call Qdrant delete by filter selector
3) return number of deleted points (if Qdrant returns it; otherwise return 0 and log)

### 6.2.6 scroll_ids(flt)

Use Qdrant scroll/pagination:
- Return only IDs (no payload) for reindex or maintenance tasks.

### 6.2.7 count(flt)
- compile filter
- call `client.count(...)`

---

## 6.3 EmbeddingSetSpecResolver (bridges SQL → Qdrant)

This component maps SQL embedding_set record into CollectionSpec:

SQL table fields (minimum):
- `embedding_sets.id` (UUID)
- `embedding_sets.name` (str, unique)
- `embedding_sets.dim` (int)
- `embedding_sets.distance` (str)
- `embedding_sets.schema_version` (int)
- `embedding_sets.is_active` (bool)

Resolver:
- loads all active sets from SQL at startup (or cache with TTL)
- builds collection_name via D2 naming
- returns CollectionSpec used by ensure_collection & repo routing

