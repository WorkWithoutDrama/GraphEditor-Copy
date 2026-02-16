"""Phase D: Runs and events — lifecycle, failure, run_items upsert."""
from datetime import datetime, timezone

import pytest

from app.db.config import DBConfig
from app.db.session import init_db, session_scope
from app.db.repositories.workspace_repo import WorkspaceRepo
from app.db.repositories.source_repo import SourceRepo, SourceVersionRepo
from app.db.repositories.document_repo import DocumentRepo
from app.db.repositories.run_repo import RunRepo, RunItemRepo, EventRepo
from app.db.services.run_tracking import RunTrackingService
from app.db.models.run import Run, RunItem


@pytest.fixture
def lineage_with_doc(db_config, db_with_tables):
    init_db(db_config)
    with session_scope() as session:
        w = WorkspaceRepo().create(session, "ws1")
        s = SourceRepo().create(session, w.id, "file")
        now = datetime.now(timezone.utc)
        v = SourceVersionRepo().create_or_get(session, s.id, "a" * 64, "uri", now)
        d = DocumentRepo().create_or_get(session, v.id, "docling", "1.0", "s3://struct.json")
    return {"workspace_id": w.id, "source_version_id": v.id, "document_id": d.id}


def test_run_lifecycle(db_config, db_with_tables, lineage_with_doc):
    init_db(db_config)
    tracking = RunTrackingService()
    with session_scope() as session:
        run_id = tracking.start_run(session, lineage_with_doc["workspace_id"], "ingest", "manual")
        tracking.append_event(session, run_id, "info", "DOC_INGESTED", {"doc": "1"})
        tracking.finish_run(session, run_id)
    with session_scope() as session:
        run = session.get(Run, run_id)
        assert run is not None
        assert run.status == "succeeded"
        assert run.finished_at is not None
    with session_scope() as session:
        events = EventRepo().list_events(session, run_id, limit=10)
        assert len(events) >= 1
        assert any(e.event_type == "DOC_INGESTED" for e in events)


def test_fail_run(db_config, db_with_tables, lineage_with_doc):
    init_db(db_config)
    tracking = RunTrackingService()
    with session_scope() as session:
        run_id = tracking.start_run(session, lineage_with_doc["workspace_id"], "ingest", "manual")
        tracking.append_event(session, run_id, "error", "INGEST_FAILED", {"reason": "timeout"})
        tracking.fail_run(session, run_id, error_message="timeout")
    with session_scope() as session:
        run = session.get(Run, run_id)
        assert run.status == "failed"
        assert run.finished_at is not None


def test_run_items_upsert(db_config, db_with_tables, lineage_with_doc):
    init_db(db_config)
    run_repo = RunRepo()
    item_repo = RunItemRepo()
    doc_id = lineage_with_doc["document_id"]
    with session_scope() as session:
        run = run_repo.start_run(session, lineage_with_doc["workspace_id"], "chunk", "manual")
        run_id = run.id
    with session_scope() as session:
        item_repo.upsert_item(
            session, run_id, "chunk", "document", doc_id, "running"
        )
    with session_scope() as session:
        item_repo.upsert_item(
            session, run_id, "chunk", "document", doc_id, "succeeded"
        )
    with session_scope() as session:
        from sqlalchemy import select, func
        count = session.execute(
            select(func.count()).select_from(RunItem).where(RunItem.run_id == run_id)
        ).scalar()
        assert count == 1
