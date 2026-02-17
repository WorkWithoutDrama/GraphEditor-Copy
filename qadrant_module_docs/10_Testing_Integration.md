# 10 — Testing (Integration-first)

## Why integration tests
Vector DB correctness depends on real server behavior.

## Setup
- docker-compose service `qdrant` (port 6333)
- pytest marker `integration`

## Tests to implement
1) `test_ensure_collection_creates_and_indexes`
2) `test_upsert_then_search_returns_expected_chunk_ids`
3) `test_delete_by_document_removes_points`
4) `test_workspace_enforcement_blocks_missing_workspace_filter`
5) `test_schema_mismatch_raises`

## Determinism tips
- Fix random seed for generated vectors
- Use small vector sizes in tests (e.g., 8 dims)

