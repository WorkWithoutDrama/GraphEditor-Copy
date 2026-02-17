# 03 — Settings and Client (Async-first)

## Settings (Pydantic)
Define `VectorStoreSettings`:

- `qdrant_url: str`
- `qdrant_api_key: str | None`
- `prefer_grpc: bool = False` (start with REST; switch if needed)
- `timeout_s: float = 10.0`
- `retries: int = 3`
- `retry_backoff_base_s: float = 0.5`
- `collection_prefix: str = "chunks"`
- `schema_version: int = 1`
- `workspace_enforced: bool = True`

## Client factory
Create `AsyncQdrantClient` in `client.py`:

- One shared client per process (DI container / app lifespan).
- Use explicit timeout.
- Wrap calls in retry helper (see section 09).

## Dependency injection
Expose `get_vectorstore_repo()` that depends on settings + client.

## Why this matches our app
- Our app is async end-to-end; Qdrant operations happen in worker tasks.
- Single shared client reduces connection overhead.

