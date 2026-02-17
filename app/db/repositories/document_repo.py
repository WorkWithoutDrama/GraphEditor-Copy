"""Document repository."""
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.schemas.document import DocumentCreate, DocumentDTO


def _stats_to_json(stats: dict[str, Any] | None) -> str | None:
    if stats is None:
        return None
    return json.dumps(stats, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


class DocumentRepo:
    def create_or_get(
        self,
        session: Session,
        source_version_id: str,
        extractor: str,
        extractor_version: str,
        structure_json_uri: str,
        language: str | None = None,
        plain_text_uri: str | None = None,
        stats: dict[str, Any] | None = None,
    ) -> DocumentDTO:
        existing = session.execute(
            select(Document).where(
                Document.source_version_id == source_version_id,
                Document.extractor == extractor,
                Document.extractor_version == extractor_version,
            )
        ).scalar_one_or_none()
        if existing:
            return DocumentDTO.model_validate(existing)
        d = Document(
            source_version_id=source_version_id,
            extractor=extractor,
            extractor_version=extractor_version,
            structure_json_uri=structure_json_uri,
            language=language,
            plain_text_uri=plain_text_uri,
            stats_json=_stats_to_json(stats),
        )
        session.add(d)
        session.flush()
        return DocumentDTO.model_validate(d)

    def update_document(
        self,
        session: Session,
        document_id: str,
        *,
        structure_json_uri: str | None = None,
        plain_text_uri: str | None = None,
        language: str | None = None,
        stats: dict[str, Any] | None = None,
    ) -> DocumentDTO | None:
        doc = session.get(Document, document_id)
        if not doc:
            return None
        if structure_json_uri is not None:
            doc.structure_json_uri = structure_json_uri
        if plain_text_uri is not None:
            doc.plain_text_uri = plain_text_uri
        if language is not None:
            doc.language = language
        if stats is not None:
            doc.stats_json = _stats_to_json(stats)
        session.flush()
        return DocumentDTO.model_validate(doc)

    def get_by_id(self, session: Session, document_id: str) -> DocumentDTO | None:
        row = session.get(Document, document_id)
        return DocumentDTO.model_validate(row) if row else None

    def list_by_source_version(
        self, session: Session, source_version_id: str
    ) -> list[DocumentDTO]:
        rows = session.execute(
            select(Document).where(Document.source_version_id == source_version_id)
        ).scalars().all()
        return [DocumentDTO.model_validate(r) for r in rows]
