"""PipelineRun, ChunkRun, ChunkExtraction repositories for MVP orchestrator."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models.pipeline_run import ChunkExtraction, ChunkRun, PipelineRun


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PipelineRunRepo:
    """Create and update pipeline runs."""

    def create(
        self,
        session: Session,
        workspace_id: str,
        document_id: str,
        *,
        llm_profile: str | None = None,
        prompt_name: str | None = None,
    ) -> PipelineRun:
        now = _utc_now()
        run = PipelineRun(
            id=str(uuid4()),
            workspace_id=workspace_id,
            document_id=document_id,
            status="RUNNING",
            llm_profile=llm_profile,
            prompt_name=prompt_name,
            started_at=now,
        )
        session.add(run)
        session.flush()
        return run

    def get(self, session: Session, run_id: str) -> PipelineRun | None:
        return session.get(PipelineRun, run_id)

    def finalize(
        self,
        session: Session,
        run_id: str,
        status: str,
        *,
        error_summary: str | None = None,
    ) -> None:
        run = session.get(PipelineRun, run_id)
        if not run:
            return
        run.status = status
        run.finished_at = _utc_now()
        if error_summary is not None:
            run.error_summary = error_summary
        session.flush()


class ChunkRunRepo:
    """Bulk create chunk_runs and update status."""

    def bulk_ensure(self, session: Session, run_id: str, chunk_ids: list[str]) -> int:
        """Ensure chunk_runs exist for each chunk; ON CONFLICT DO NOTHING. Returns count created."""
        if not chunk_ids:
            return 0
        stmt = sqlite_insert(ChunkRun).values(
            [
                {
                    "id": str(uuid4()),
                    "run_id": run_id,
                    "chunk_id": cid,
                    "status": "PENDING",
                    "attempts": 0,
                }
                for cid in chunk_ids
            ]
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=["run_id", "chunk_id"])
        result = session.execute(stmt)
        session.flush()
        return result.rowcount or 0

    def list_pending(self, session: Session, run_id: str) -> list[ChunkRun]:
        rows = session.execute(
            select(ChunkRun).where(
                ChunkRun.run_id == run_id,
                ChunkRun.status == "PENDING",
            )
        ).scalars().all()
        return list(rows)

    def mark_done(self, session: Session, run_id: str, chunk_id: str, *, latency_ms: int | None = None) -> None:
        row = session.execute(
            select(ChunkRun).where(ChunkRun.run_id == run_id, ChunkRun.chunk_id == chunk_id)
        ).scalar_one_or_none()
        if not row:
            return
        row.status = "DONE"
        if latency_ms is not None:
            row.latency_ms = latency_ms
        session.flush()

    def mark_error(
        self,
        session: Session,
        run_id: str,
        chunk_id: str,
        *,
        error_type: str | None = None,
        error_message: str | None = None,
        increment_attempts: bool = True,
    ) -> None:
        row = session.execute(
            select(ChunkRun).where(ChunkRun.run_id == run_id, ChunkRun.chunk_id == chunk_id)
        ).scalar_one_or_none()
        if not row:
            return
        row.status = "ERROR"
        if error_type is not None:
            row.error_type = error_type
        if error_message is not None:
            row.error_message = error_message[:4096]
        if increment_attempts:
            row.attempts = (row.attempts or 0) + 1
        session.flush()


class ChunkExtractionRepo:
    """Upsert chunk_extractions (idempotent by run_id, chunk_id, prompt_name)."""

    def upsert(
        self,
        session: Session,
        chunk_id: str,
        run_id: str,
        prompt_name: str,
        *,
        model: str | None = None,
        raw_text: str | None = None,
        parsed_json: str | None = None,
        usage_json: str | None = None,
        validation_error: str | None = None,
    ) -> None:
        stmt = sqlite_insert(ChunkExtraction).values(
            id=str(uuid4()),
            chunk_id=chunk_id,
            run_id=run_id,
            prompt_name=prompt_name,
            model=model,
            raw_text=raw_text,
            parsed_json=parsed_json,
            usage_json=usage_json,
            validation_error=validation_error,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["run_id", "chunk_id", "prompt_name"],
            set_={
                "model": model,
                "raw_text": raw_text,
                "parsed_json": parsed_json,
                "usage_json": usage_json,
                "validation_error": validation_error,
            },
        )
        session.execute(stmt)
        session.flush()

    def list_by_run(self, session: Session, run_id: str, limit: int = 100) -> list[ChunkExtraction]:
        rows = (
            session.execute(
                select(ChunkExtraction).where(ChunkExtraction.run_id == run_id).limit(limit)
            )
        ).scalars().all()
        return list(rows)
