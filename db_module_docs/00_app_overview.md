# 00 — High-level application overview (context)

## What the application does (problem → pipeline)

We ingest documents of many formats (PDF/DOCX/Markdown/HTML/etc.), normalize them into a structured representation,
produce text chunks suitable for retrieval, and store chunk embeddings in a vector database for later RAG retrieval.

Typical end-to-end flow:

1. **Ingest**
   - Receive a document (file upload / URI / repository).
   - Persist the raw file to storage (filesystem/object storage).
   - Compute `content_sha256` for idempotency + dedupe.

2. **Normalize / Extract (Docling)**
   - Convert to a normalized structured format (Docling-like JSON + plain text + layout hints).
   - Store large structured output in storage.
   - Record references and stats in relational DB.

3. **Chunk**
   - Split extracted text into deterministic chunks with metadata (section path, page range, offsets).
   - Persist chunks in relational DB (or store text in storage and keep URI in DB).

4. **Embed**
   - Create embeddings for each chunk using a configured embedding model.
   - Store vectors in **Qdrant**.
   - Store pointers from chunks → Qdrant `point_id` in relational DB.

5. **Retrieve**
   - For a user query: embed query, search Qdrant, optionally rerank, return source chunks.
   - Optionally persist query logs/results to DB for evaluation.

## Where the DB module fits

The DB module is the **system of record** for:
- document identity and versioning (dedupe, provenance),
- structured extraction references and stats,
- chunks and their metadata,
- embedding set definitions and pointers into Qdrant,
- pipeline runs, events, and errors for observability.

The DB module is **not** the vector store (Qdrant is), and it should not contain large binary data.

## Design goals

- **Idempotency:** repeated ingestion/chunking/embedding runs do not create duplicates.
- **Traceability:** every chunk can be traced back to source/version and extraction parameters.
- **Operational robustness:** clear run/event logs, safe concurrency on SQLite, recoverable failures.
- **Testability:** repositories/services with deterministic behavior and unit/integration tests.
- **Portability:** SQLite now, easy path to Postgres later (avoid SQLite-only assumptions).

## External dependencies (relevant to DB)

- SQLAlchemy 2.x (ORM + engine/session)
- Alembic (migrations)
- Pydantic v2 (DTOs + create/update schemas)
- pydantic-settings (configuration)
- aiosqlite (async-first DB access)
- Qdrant is external; DB stores only references.
