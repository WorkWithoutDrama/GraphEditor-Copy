# 04 — Collections and Indexes (Deterministic ensure_collection)

## Collection naming
`{collection_prefix}__{embedding_set_slug}__v{schema_version}`
Example: `chunks__e5_large__v1`

## Vector parameters (per embedding_set)
From SQL `embedding_set` record:
- `vector_size: int`
- `distance: "Cosine" | "Dot" | "Euclid"`

Store these in SQL and treat as authoritative.

## ensure_collection() algorithm
1) Compute target collection name from settings + embedding_set_slug + schema_version
2) Check if collection exists
3) If not exists:
   - Create it with vector_size + distance
4) If exists:
   - Validate vector_size + distance match expectations
   - If mismatch → raise `VectorSchemaMismatchError` (forces migration)

## Payload indexes
Create field indexes for:
- `workspace_id` (keyword)
- `document_id` (keyword)
- `created_at` (datetime) (optional but useful)
- `source` (keyword) (if used)
- `tags` (keyword list) (if used)

## Why indexes matter
Our architecture uses filters heavily:
- workspace isolation
- document-bound deletes
- optional time/source constraints

Without payload indexes, filtered search degrades.

