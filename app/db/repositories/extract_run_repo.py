"""ExtractRun repository: get_or_create_run, update_run_status."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models.extract_run import ExtractRun
from app.db.schemas.extract_run import ExtractRunDTO


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExtractRunRepo:
    """Returns DTOs/ids only (R1)."""

    def get_or_create_run(
        self,
        session: Session,
        workspace_id: str,
        source_version_id: str,
        extractor: str,
        extractor_version: str,
        status: str = "QUEUED",
        trace_id: str | None = None,
    ) -> ExtractRunDTO:
        """Get existing run or create with status QUEUED. Conflict-safe upsert."""
        existing = session.execute(
            select(ExtractRun).where(
                ExtractRun.workspace_id == workspace_id,
                ExtractRun.source_version_id == source_version_id,
                ExtractRun.extractor == extractor,
                ExtractRun.extractor_version == extractor_version,
            )
        ).scalar_one_or_none()
        if existing:
            # Re-enqueue: allow updating to QUEUED
            if status == "QUEUED":
                existing.status = status
                existing.updated_at = _utc_now()
                session.flush()
            return ExtractRunDTO.model_validate(existing)
        from uuid import uuid4

        now = _utc_now()
        stmt = sqlite_insert(ExtractRun).values(
            id=str(uuid4()),
            workspace_id=workspace_id,
            source_version_id=source_version_id,
            extractor=extractor,
            extractor_version=extractor_version,
            status=status,
            attempt=1,
            trace_id=trace_id,
            created_at=now,
            updated_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                "workspace_id",
                "source_version_id",
                "extractor",
                "extractor_version",
            ],
            set_={"status": status, "updated_at": now},
        )
        session.execute(stmt)
        session.flush()
        row = session.execute(
            select(ExtractRun).where(
                ExtractRun.workspace_id == workspace_id,
                ExtractRun.source_version_id == source_version_id,
                ExtractRun.extractor == extractor,
                ExtractRun.extractor_version == extractor_version,
            )
        ).scalar_one()
        return ExtractRunDTO.model_validate(row)

    def get_run(
        self,
        session: Session,
        workspace_id: str,
        source_version_id: str,
        extractor: str,
        extractor_version: str,
    ) -> ExtractRunDTO | None:
        row = session.execute(
            select(ExtractRun).where(
                ExtractRun.workspace_id == workspace_id,
                ExtractRun.source_version_id == source_version_id,
                ExtractRun.extractor == extractor,
                ExtractRun.extractor_version == extractor_version,
            )
        ).scalar_one_or_none()
        return ExtractRunDTO.model_validate(row) if row else None

    def get_by_id(self, session: Session, run_id: str) -> ExtractRunDTO | None:
        row = session.get(ExtractRun, run_id)
        return ExtractRunDTO.model_validate(row) if row else None

    def update_run_status(
        self,
        session: Session,
        run_id: str,
        status: str,
        error_code: str | None = None,
        error_message: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        chunker_version: str | None = None,
    ) -> None:
        run = session.get(ExtractRun, run_id)
        if not run:
            return
        run.status = status
        run.updated_at = _utc_now()
        if error_code is not None:
            run.error_code = error_code
        if error_message is not None:
            run.error_message = error_message
        if started_at is not None:
            run.started_at = started_at
        if finished_at is not None:
            run.finished_at = finished_at
        if chunker_version is not None:
            run.chunker_version = chunker_version
        session.flush()

    def list_by_status(
        self, session: Session, statuses: list[str], limit: int = 500
    ) -> list[ExtractRunDTO]:
        rows = (
            session.execute(
                select(ExtractRun).where(ExtractRun.status.in_(statuses)).limit(limit)
            )
        ).scalars().all()
        return [ExtractRunDTO.model_validate(r) for r in rows]
