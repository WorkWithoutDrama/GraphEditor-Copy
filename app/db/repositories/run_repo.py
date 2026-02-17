"""Run, RunItem, and Event repositories."""
from datetime import datetime, timezone
from typing import Any
import json
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models.run import Run, RunItem, Event
from app.db.models.source import SourceVersion
from app.db.models.document import Document
from app.db.models.chunk import Chunk


def _meta_to_json(meta: dict[str, Any] | None) -> str | None:
    if meta is None:
        return None
    return json.dumps(meta, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _validate_target(session: Session, target_type: str, target_id: str) -> bool:
    """Validate that target_id exists in the table for target_type."""
    if target_type == "source_version":
        return session.get(SourceVersion, target_id) is not None
    if target_type == "document":
        return session.get(Document, target_id) is not None
    if target_type == "chunk":
        return session.get(Chunk, target_id) is not None
    return False


class RunRepo:
    def start_run(
        self,
        session: Session,
        workspace_id: str,
        run_type: str,
        trigger: str,
        meta: dict[str, Any] | None = None,
    ) -> Run:
        now = datetime.now(timezone.utc)
        r = Run(
            workspace_id=workspace_id,
            run_type=run_type,
            status="running",
            trigger=trigger,
            started_at=now,
            meta_json=_meta_to_json(meta),
        )
        session.add(r)
        session.flush()
        return r

    def finish_run(self, session: Session, run_id: str) -> None:
        run = session.get(Run, run_id)
        if run:
            run.finished_at = datetime.now(timezone.utc)
            run.status = "succeeded"
            session.flush()

    def fail_run(
        self,
        session: Session,
        run_id: str,
        error_message: str | None = None,
    ) -> None:
        run = session.get(Run, run_id)
        if run:
            run.finished_at = datetime.now(timezone.utc)
            run.status = "failed"
            session.flush()


class RunItemRepo:
    def upsert_item(
        self,
        session: Session,
        run_id: str,
        stage: str,
        target_type: str,
        target_id: str,
        status: str,
        error_message: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> RunItem:
        if not _validate_target(session, target_type, target_id):
            raise ValueError(f"target_id {target_id} not found for target_type {target_type}")
        metrics_json = json.dumps(metrics, ensure_ascii=False, separators=(",", ":"), sort_keys=True) if metrics else None
        now = datetime.now(timezone.utc)
        stmt = sqlite_insert(RunItem).values(
            id=str(uuid4()),
            run_id=run_id,
            stage=stage,
            target_type=target_type,
            target_id=target_id,
            status=status,
            error_message=error_message,
            metrics_json=metrics_json,
            created_at=now,
            updated_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["run_id", "stage", "target_type", "target_id"],
            set_={
                "status": status,
                "error_message": error_message,
                "metrics_json": metrics_json,
                "updated_at": now,
            },
        )
        session.execute(stmt)
        session.flush()
        row = session.execute(
            select(RunItem).where(
                RunItem.run_id == run_id,
                RunItem.stage == stage,
                RunItem.target_type == target_type,
                RunItem.target_id == target_id,
            )
        ).scalar_one()
        return row


class EventRepo:
    def append_event(
        self,
        session: Session,
        run_id: str,
        level: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> Event:
        now = datetime.now(timezone.utc)
        payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) if payload else None
        e = Event(
            run_id=run_id,
            ts=now,
            level=level,
            event_type=event_type,
            payload_json=payload_json,
        )
        session.add(e)
        session.flush()
        return e

    def list_events(self, session: Session, run_id: str, limit: int = 100) -> list[Event]:
        rows = (
            session.execute(
                select(Event)
                .where(Event.run_id == run_id)
                .order_by(Event.ts.desc())
                .limit(limit)
            )
        ).scalars().all()
        return list(rows)
