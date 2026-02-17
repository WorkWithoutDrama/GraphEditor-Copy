"""Run tracking service — start/finish/fail run, append events."""
from typing import Any

from sqlalchemy.orm import Session

from app.db.repositories.run_repo import RunRepo, RunItemRepo, EventRepo


class RunTrackingService:
    def __init__(self) -> None:
        self._run_repo = RunRepo()
        self._event_repo = EventRepo()
        self._item_repo = RunItemRepo()

    def start_run(
        self,
        session: Session,
        workspace_id: str,
        run_type: str,
        trigger: str = "manual",
        meta: dict[str, Any] | None = None,
    ) -> str:
        run = self._run_repo.start_run(session, workspace_id, run_type, trigger, meta)
        return run.id

    def finish_run(self, session: Session, run_id: str) -> None:
        self._run_repo.finish_run(session, run_id)

    def fail_run(
        self,
        session: Session,
        run_id: str,
        error_message: str | None = None,
    ) -> None:
        self._run_repo.fail_run(session, run_id, error_message)

    def append_event(
        self,
        session: Session,
        run_id: str,
        level: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._event_repo.append_event(session, run_id, level, event_type, payload)

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
    ) -> None:
        self._item_repo.upsert_item(
            session, run_id, stage, target_type, target_id,
            status, error_message, metrics,
        )
