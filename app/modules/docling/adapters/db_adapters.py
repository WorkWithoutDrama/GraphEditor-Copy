"""Adapters wrapping app.db.repositories (implement docling ports). Session-bound."""
from typing import Any

from sqlalchemy.orm import Session

from app.db.repositories.chunk_repo import ChunkPayload, ChunkRepo
from app.db.repositories.document_repo import DocumentRepo
from app.db.repositories.extract_run_repo import ExtractRunRepo
from app.modules.docling.ports import ChunkCreateLike


class DocumentRepoAdapter:
    """Implements DocumentRepoPort using app.db.repositories.DocumentRepo."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = DocumentRepo()

    def get_or_create_document(
        self,
        source_version_id: str,
        extractor: str,
        extractor_version: str,
        structure_json_uri: str,
        language: str | None = None,
        plain_text_uri: str | None = None,
        stats: dict[str, Any] | None = None,
    ) -> Any:
        return self._repo.create_or_get(
            self._session,
            source_version_id=source_version_id,
            extractor=extractor,
            extractor_version=extractor_version,
            structure_json_uri=structure_json_uri,
            language=language,
            plain_text_uri=plain_text_uri,
            stats=stats,
        )

    def update_document(
        self,
        document_id: str,
        *,
        structure_json_uri: str | None = None,
        plain_text_uri: str | None = None,
        language: str | None = None,
        stats: dict[str, Any] | None = None,
    ) -> Any | None:
        return self._repo.update_document(
            self._session,
            document_id,
            structure_json_uri=structure_json_uri,
            plain_text_uri=plain_text_uri,
            language=language,
            stats=stats,
        )

    def get_document(self, document_id: str) -> Any | None:
        return self._repo.get_by_id(self._session, document_id)

    def list_documents_by_source_version(self, source_version_id: str) -> list[Any]:
        return self._repo.list_by_source_version(
            self._session, source_version_id
        )


class ExtractRunsAdapter:
    """Implements ExtractRunsPort using app.db.repositories.ExtractRunRepo."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = ExtractRunRepo()

    def get_or_create_run(
        self,
        workspace_id: str,
        source_version_id: str,
        extractor: str,
        extractor_version: str,
        status: str = "QUEUED",
        trace_id: str | None = None,
    ) -> Any:
        return self._repo.get_or_create_run(
            self._session,
            workspace_id=workspace_id,
            source_version_id=source_version_id,
            extractor=extractor,
            extractor_version=extractor_version,
            status=status,
            trace_id=trace_id,
        )

    def get_run(
        self,
        workspace_id: str,
        source_version_id: str,
        extractor: str,
        extractor_version: str,
    ) -> Any | None:
        return self._repo.get_run(
            self._session,
            workspace_id=workspace_id,
            source_version_id=source_version_id,
            extractor=extractor,
            extractor_version=extractor_version,
        )

    def get_by_id(self, run_id: str) -> Any | None:
        return self._repo.get_by_id(self._session, run_id)

    def list_by_status(
        self, statuses: list[str], limit: int = 500
    ) -> list[Any]:
        return self._repo.list_by_status(
            self._session, statuses, limit=limit
        )

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
        self._repo.update_run_status(
            self._session,
            run_id,
            status=status,
            error_code=error_code,
            error_message=error_message,
            started_at=started_at,
            finished_at=finished_at,
            chunker_version=chunker_version,
        )


class ChunkRepoAdapter:
    """Implements ChunkRepoPort using app.db.repositories.ChunkRepo."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = ChunkRepo()

    def _to_payload(self, c: ChunkCreateLike) -> ChunkPayload:
        return ChunkPayload(
            chunk_hash=c.chunk_hash,
            chunk_index=c.chunk_index,
            text=c.text,
            text_uri=c.text_uri,
            start_char=None,
            end_char=None,
            page_start=c.page_start,
            page_end=c.page_end,
            meta_json=c.meta_json,
        )

    def bulk_upsert_chunks(
        self,
        document_id: str,
        chunks: list[ChunkCreateLike],
        *,
        batch_rows: int = 200,
        batch_max_bytes: int = 5 * 1024 * 1024,
    ) -> int:
        payloads = [self._to_payload(c) for c in chunks]
        return self._repo.bulk_upsert_chunks(
            self._session,
            document_id,
            payloads,
            batch_rows=batch_rows,
            batch_max_bytes=batch_max_bytes,
        )
