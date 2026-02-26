# 04 — Collection Spec and ensure_collection()

This file defines the **exact** behavior of schema creation/validation.

---

## 4.1 CollectionSpec (internal typed model)

Define a Pydantic model:

- `name: str`
- `vector_size: int`
- `distance: Literal["Cosine","Dot","Euclid"]`
- `schema_version: int`
- `payload_indexes: list[PayloadIndexSpec]`
- `hnsw_config: HnswSpec | None`

Where `PayloadIndexSpec` contains:
- `field_name: str`
- `field_schema: Literal["keyword","integer","float","datetime","text","bool"]`
- optional params (range/lookup/ordering) only when needed

## 4.2 Locked baseline payload indexes

Create these indexes **always**:

1) `workspace_id` → keyword  
2) `document_id` → keyword  
3) `chunk_hash` → keyword  
4) `chunk_index` → integer  
5) `created_at` → datetime  
6) Optional: `source` → keyword  
7) Optional: `tags` → keyword (list)  

## 4.3 Collection creation parameters (defaults)

Vectors config:
- `size = vector_size`
- `distance = distance`

HNSW config:
- Default (safe general purpose):
  - `m = 16`
  - `ef_construct = 128`

Multitenant optimization toggle (if `multitenant_mode=True`):
- Use Qdrant-recommended approach for payload-partitioned multi-tenant collections:
  - `payload_m = 16`
  - `m = 0`  (disable global index)
This should be enabled only when you **always** filter by workspace.

## 4.4 ensure_collection() algorithm (no ambiguity)

Function:
`async def ensure_collection(client, spec: CollectionSpec) -> None`

Steps:
1) If collection does not exist → `create_collection(...)` with vectors_config + (optional) hnsw_config
2) Fetch collection info (`get_collection`) and validate:
   - vector size matches
   - distance matches
   - named vectors not present (since we locked single vector)
3) Create/ensure payload indexes:
   - For each index in spec.payload_indexes:
     - call `create_payload_index(collection_name, field_name, field_schema=...)`
     - handle “already exists” gracefully (treat as OK)
4) Store/validate schema version:
   - We encode version in collection name. If wrong, we *do not* mutate in place.
   - Instead, we raise a **MigrationRequired** error that points to the reindex plan.

### Why this strictness?
Qdrant can update some configs in place, but “strict validate + explicit migration” is safer and mirrors our DB archive principles.

## 4.5 Collection name builder (deterministic)

`build_collection_name(prefix, embedding_set_name, schema_version) -> str`

Example:
- `chunks__e5_large__v1`

Rule:
- Do NOT include timestamps or random suffixes.
- If you change vector_size/distance/payload schema meaningfully → increment schema_version.

