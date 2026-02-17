# 08 — Migrations and Reindex

## When do we need a migration?
- embedding vector size changed
- distance metric changed
- payload indexing changes that require reindex (rare)
- schema_version bumped

## Safe migration (recommended)
1) Create new collection:
   `chunks__{embedding_set_slug}__v{schema_version+1}`
2) Reindex:
   - scroll old collection points
   - for each batch:
     - fetch payload + vector (or if vectors not stored/returned: rebuild from SQL)
     - upsert into new collection
3) Switch routing:
   - change settings schema_version OR update embedding_set->collection mapping in SQL config
4) Keep old collection for rollback window
5) Delete old collection after confirmation

## Notes
- Prefer reindexing from SQL if possible (SQL remains source of truth).
- Keep a migration log record in SQL (embedding_set_migrations table) with start/end, counts.

