# 02 — Locked Decisions (to remove ambiguity)

These defaults are chosen to match our architecture and keep the first implementation stable.

## D1: Async API only
- The repository uses `AsyncQdrantClient`.
- If a sync path is needed later, add a thin adapter.

## D2: Point identity = Chunk ID (UUID)
- **Point ID** is a UUID that equals `chunk_id` in SQL.
- This makes upserts naturally idempotent and join-friendly.

> If your SQL chunk_id is currently BIGINT, you can use uint64 point IDs instead.
> But UUID is recommended to avoid cross-db integer collisions and to simplify future sharding.

## D3: Collection strategy = one collection per embedding_set
- Collection name: `chunks__{embedding_set_slug}__v{schema_version}`
- Rationale: vector size/distance are tied to embedding_set; separate collections avoid mixing.

## D4: Multitenancy = payload filter, not per-workspace collections
- Always store `workspace_id` payload and enforce it in queries/deletes.
- Avoid “one collection per tenant” unless a tenant is massive.

## D5: Payload schema is minimal
We store only:
- join keys for SQL
- filter fields
- diagnostics

Never store full chunk text in Qdrant in v1.

## D6: Migration strategy = new collection + reindex + switch
Avoid risky in-place changes; do:
- create vNext
- reindex via scroll
- flip routing
- delete old after grace

