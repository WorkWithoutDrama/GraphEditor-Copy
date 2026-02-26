"""Port interfaces for docling module (no SQLAlchemy, no Docling in repo)."""
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DocumentRepoPort(Protocol):
    """Document persistence: get_or_create, update, get."""

    def get_document(self, document_id: str) -> Any | None:
        ...

    def list_documents_by_source_version(self, source_version_id: str) -> list[Any]:
        ...

    def get_or_create_document(
        self,
        source_version_id: str,
        extractor: str,
        extractor_version: str,
        structure_json_uri: str,
        language: str | None = None,
        plain_text_uri: str | None = None,
        stats: dict[str, Any] | None = None,
    ) -> Any:  # Document DTO with .id
        ...

    def update_document(
        self,
        document_id: str,
        *,
        structure_json_uri: str | None = None,
        plain_text_uri: str | None = None,
        language: str | None = None,
        stats: dict[str, Any] | None = None,
    ) -> Any | None:  # Document DTO or None
        ...


@runtime_checkable
class ExtractRunsPort(Protocol):
    """Extract run FSM: get_or_create, update status."""

    def get_or_create_run(
        self,
        workspace_id: str,
        source_version_id: str,
        extractor: str,
        extractor_version: str,
        status: str = "QUEUED",
        trace_id: str | None = None,
    ) -> Any:  # Run DTO with .id
        ...

    def get_run(
        self,
        workspace_id: str,
        source_version_id: str,
        extractor: str,
        extractor_version: str,
    ) -> Any | None:
        ...

    def get_by_id(self, run_id: str) -> Any | None:
        ...

    def list_by_status(self, statuses: list[str], limit: int = 500) -> list[Any]:
        ...

    def update_run_status(
        self,
        run_id: str,
        status: str,
        error_code: str | None = None,
        error_message: str | None = None,
        started_at: Any = None,
        finished_at: Any = None,
        chunker_version: str | None = None,
    ) -> None:
        ...


class ChunkCreateLike(Protocol):
    """Minimal chunk shape for bulk_upsert."""

    chunk_index: int
    chunk_hash: str
    text: str | None
    text_uri: str | None
    page_start: int | None
    page_end: int | None
    meta_json: str | None


@runtime_checkable
class ChunkRepoPort(Protocol):
    """Chunk persistence: bulk upsert, return inserted count."""

    def bulk_upsert_chunks(
        self,
        document_id: str,
        chunks: list[ChunkCreateLike],
        *,
        batch_rows: int = 200,
        batch_max_bytes: int = 5 * 1024 * 1024,
    ) -> int:
        ...


@runtime_checkable
class FileStorePort(Protocol):
    """Derived outputs only: put_bytes, open_stream."""

    def put_bytes(self, key: str, data: bytes) -> str:
        """Write bytes; return URI."""
        ...

    def open_stream(self, uri: str):  # file-like
        """Open stream for reading."""
        ...


@runtime_checkable
class JobPublisherPort(Protocol):
    """Publish job with envelope."""

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        ...


@runtime_checkable
class SourceContentPort(Protocol):
    """Read raw file from SourceVersion storage."""

    def open_raw_stream(self, source_version_id: str):
        """Return file-like for raw content. Caller closes."""
        ...


class TokenizerSpec(Protocol):
    """Token count for chunk sizing (embeddings module owns model)."""

    def count_tokens(self, text: str) -> int:
        ...
