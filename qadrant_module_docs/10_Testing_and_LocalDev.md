# 10 — Testing and Local Development

---

## 10.1 Local Qdrant (docker-compose)

Run Qdrant in local dev/test with a dedicated docker compose file.
Use fixed ports:
- REST: 6333
- gRPC: 6334

Make sure tests can run in CI.

## 10.2 Integration tests (must-have)

Write tests that run against real Qdrant (docker):

1) `test_ensure_collection_creates_and_indexes`
2) `test_upsert_then_search_returns_expected_ids`
3) `test_delete_by_document_removes_points`
4) `test_workspace_isolation_filter_is_enforced`
5) `test_schema_mismatch_raises_migration_required`

Notes:
- Keep tests small, use random UUIDs.
- Ensure cleanup: delete test collection after run (or use versioned random names in tests).

## 10.3 Unit tests (optional)

Use `QdrantLocal` for fast unit tests for mapping code:
- filter compilation
- payload serialization
- batch splitting logic

Still keep at least the integration suite.

## 10.4 Deterministic fixtures

- Seed vectors with simple numeric patterns.
- Use cosine distance and known nearest neighbors.

