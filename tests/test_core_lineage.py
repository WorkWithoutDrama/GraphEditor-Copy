"""Phase B: Core lineage — workspace, source, version, document; dedupe."""
from datetime import datetime, timezone

import pytest

from app.db.config import DBConfig
from app.db.session import init_db, session_scope
from app.db.repositories.workspace_repo import WorkspaceRepo
from app.db.repositories.source_repo import SourceRepo, SourceVersionRepo
from app.db.repositories.document_repo import DocumentRepo


@pytest.fixture
def repos():
    return {
        "workspace": WorkspaceRepo(),
        "source": SourceRepo(),
        "source_version": SourceVersionRepo(),
        "document": DocumentRepo(),
    }


def test_create_workspace_and_source(db_config, db_with_tables, repos):
    init_db(db_config)
    with session_scope() as session:
        w = repos["workspace"].create(session, "test-ws")
        assert w.id
        assert w.name == "test-ws"
        s = repos["source"].create(
            session,
            workspace_id=w.id,
            source_type="file",
            external_ref="file:///doc.pdf",
            title="Doc",
        )
        assert s.id
        assert s.workspace_id == w.id
        assert s.source_type == "file"


def test_source_version_dedupe_by_content_sha256(db_config, db_with_tables, repos):
    init_db(db_config)
    with session_scope() as session:
        w = repos["workspace"].create(session, "ws1")
        s1 = repos["source"].create(session, w.id, "file", title="A")
        s2 = repos["source"].create(session, w.id, "file", title="B")
        hash1 = "a" * 64
        uri = "storage:///bucket/x"
        now = datetime.now(timezone.utc)
        v1 = repos["source_version"].create_or_get(
            session, s1.id, hash1, uri, now
        )
        v2 = repos["source_version"].create_or_get(
            session, s2.id, hash1, uri, now
        )
        assert v1.id == v2.id
        assert v1.content_sha256 == hash1


def test_document_uniqueness_by_version_extractor(db_config, db_with_tables, repos):
    init_db(db_config)
    with session_scope() as session:
        w = repos["workspace"].create(session, "ws1")
        s = repos["source"].create(session, w.id, "file")
        now = datetime.now(timezone.utc)
        v = repos["source_version"].create_or_get(
            session, s.id, "b" * 64, "uri", now
        )
        d1 = repos["document"].create_or_get(
            session,
            v.id,
            "docling",
            "1.0",
            "s3://struct.json",
        )
        d2 = repos["document"].create_or_get(
            session,
            v.id,
            "docling",
            "1.0",
            "s3://struct.json",
        )
        assert d1.id == d2.id
        docs = repos["document"].list_by_source_version(session, v.id)
        assert len(docs) == 1
