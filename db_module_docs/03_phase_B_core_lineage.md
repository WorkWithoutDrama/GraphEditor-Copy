# 03 — Phase B: Core lineage schema (workspaces/sources/versions/documents)

## Goal
Implement the minimal content provenance chain to support ingestion + extraction tracking.

Entities:
- Workspace
- Source (document identity)
- SourceVersion (immutable content version, dedupe by hash)
- Document (extraction output for a given version and extractor version)

## Deliverables
- ORM models for tables above
- Alembic migration `001_create_core_lineage_tables`
- Repositories with idempotent operations
- Pydantic DTOs and Create schemas
- Tests: dedupe behavior, relationships, basic queries

## Schema (recommended)

### workspaces
- `id` TEXT PK
- `name` TEXT NOT NULL UNIQUE within system (or unique per user if multi-tenant later)
- `created_at`, `updated_at`

### sources
- `id` TEXT PK
- `workspace_id` FK → workspaces.id (ON DELETE CASCADE)
- `title` TEXT NULL
- `source_type` TEXT NOT NULL  (enum-like: file/url/markdown/etc.)
- `external_ref` TEXT NULL      (url, external id, etc.)
- timestamps
Indexes:
- `(workspace_id)`

### source_versions
- `id` TEXT PK
- `source_id` FK → sources.id (ON DELETE CASCADE)
- `content_sha256` TEXT NOT NULL
- `mime_type` TEXT NULL
- `size_bytes` INTEGER NULL
- `storage_uri` TEXT NOT NULL   (where raw file lives)
- `ingested_at` DATETIME NOT NULL
- `ingest_meta_json` TEXT NULL  (small JSON)
Constraints:
- UNIQUE `(content_sha256)` — **global dedupe**: same content stored once; first inserter's source_id; others reuse existing row.
Indexes:
- `content_sha256`

### documents
- `id` TEXT PK
- `source_version_id` FK → source_versions.id (ON DELETE CASCADE)
- `extractor` TEXT NOT NULL          (e.g. "docling")
- `extractor_version` TEXT NOT NULL
- `language` TEXT NULL
- `structure_json_uri` TEXT NOT NULL
- `plain_text_uri` TEXT NULL
- `stats_json` TEXT NULL
Constraints:
- UNIQUE `(source_version_id, extractor, extractor_version)`
Indexes:
- `source_version_id`

## Tasks (step-by-step)

### B1 — Implement ORM models
Create files under `app/db/models/`:
- `workspace.py`
- `source.py` (Source + SourceVersion)
- `document.py`

Use SQLAlchemy 2.x typing:
- `Mapped[str]`
- `mapped_column(String, ...)`

### B2 — Relationships
- Workspace.sources
- Source.versions
- SourceVersion.documents
Ensure cascades match intended deletion semantics.

### B3 — Migration
Create `001_create_core_lineage_tables`.
Review generated SQL:
- FKs exist
- indexes exist
- uniqueness constraints exist

### B4 — Pydantic schemas
Define:
- DTOs: `WorkspaceDTO`, `SourceDTO`, `SourceVersionDTO`, `DocumentDTO`
- Creates: `WorkspaceCreate`, `SourceCreate`, `SourceVersionCreate`, `DocumentCreate`

**Required:** DTOs must set `model_config = ConfigDict(from_attributes=True)` for `Model.model_validate(orm_instance)` (Pydantic v2 standard for SQLAlchemy ORM).

Use strict typing and validated JSON fields:
- `ingest_meta: dict[str, Any] | None` but stored as JSON string in DB
- same for `stats`

### B5 — Repositories
Implement minimal repo methods:

WorkspaceRepo
- `create(name)`
- `get(id)`
- `get_by_name(name)`

SourceRepo
- `create(workspace_id, source_type, external_ref, title)`
- `get(id)`
- `list_by_workspace(workspace_id)`

SourceVersionRepo
- `create_or_get(source_id, content_sha256, storage_uri, ...)`  **idempotent** — global dedupe by content_sha256; if exists, return existing (regardless of source_id).
- `get(id)`
- `get_by_hash(content_sha256)`

DocumentRepo
- `create_or_get(source_version_id, extractor, extractor_version, structure_json_uri, ...)` **idempotent**
- `list_by_source_version(source_version_id)`

Implementation hints:
- Prefer `INSERT ...` then handle IntegrityError by SELECTing existing row
- Keep transaction small and deterministic
- Return DTOs

### B6 — Tests
Create tests covering:
- create workspace/source/version
- inserting same version twice returns same record (dedupe)
- document uniqueness by `(source_version_id, extractor, extractor_version)`

## Acceptance checks
- Migration applies cleanly on empty DB
- All repo methods covered by tests
- Dedupe works reliably under repeated calls
- No large blobs stored; only URIs and small JSON

## Pitfalls to avoid
- Using Python Enums that autogenerate different values across migrations; store enums as TEXT
- Missing indexes on hash fields → slow dedupe
- Storing large docling JSON in DB → keep only URIs
