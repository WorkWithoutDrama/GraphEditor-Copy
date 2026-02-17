"""Source and SourceVersion repositories."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.source import Source, SourceVersion
from app.db.schemas.source import SourceCreate, SourceDTO, SourceVersionCreate, SourceVersionDTO


class SourceRepo:
    def create(
        self,
        session: Session,
        workspace_id: str,
        source_type: str,
        external_ref: str | None = None,
        title: str | None = None,
    ) -> SourceDTO:
        s = Source(
            workspace_id=workspace_id,
            source_type=source_type,
            external_ref=external_ref,
            title=title,
        )
        session.add(s)
        session.flush()
        return SourceDTO.model_validate(s)

    def get(self, session: Session, id: str) -> SourceDTO | None:
        row = session.get(Source, id)
        return SourceDTO.model_validate(row) if row else None

    def list_by_workspace(self, session: Session, workspace_id: str) -> list[SourceDTO]:
        rows = session.execute(select(Source).where(Source.workspace_id == workspace_id)).scalars().all()
        return [SourceDTO.model_validate(r) for r in rows]


class SourceVersionRepo:
    def create_or_get(
        self,
        session: Session,
        source_id: str,
        content_sha256: str,
        storage_uri: str,
        ingested_at: datetime,
        mime_type: str | None = None,
        size_bytes: int | None = None,
        ingest_meta_json: str | None = None,
    ) -> SourceVersionDTO:
        existing = session.execute(
            select(SourceVersion).where(SourceVersion.content_sha256 == content_sha256)
        ).scalar_one_or_none()
        if existing:
            return SourceVersionDTO.model_validate(existing)
        v = SourceVersion(
            source_id=source_id,
            content_sha256=content_sha256,
            storage_uri=storage_uri,
            ingested_at=ingested_at,
            mime_type=mime_type,
            size_bytes=size_bytes,
            ingest_meta_json=ingest_meta_json,
        )
        session.add(v)
        session.flush()
        return SourceVersionDTO.model_validate(v)

    def get(self, session: Session, id: str) -> SourceVersionDTO | None:
        row = session.get(SourceVersion, id)
        return SourceVersionDTO.model_validate(row) if row else None

    def get_by_hash(self, session: Session, content_sha256: str) -> SourceVersionDTO | None:
        row = session.execute(
            select(SourceVersion).where(SourceVersion.content_sha256 == content_sha256)
        ).scalar_one_or_none()
        return SourceVersionDTO.model_validate(row) if row else None
