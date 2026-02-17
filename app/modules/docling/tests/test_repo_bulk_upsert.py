"""Unit test: bulk upsert uses conflict handling, no IntegrityError loops (plan H1)."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Workspace, Source, SourceVersion, Document, Chunk
from app.db.repositories.chunk_repo import ChunkRepo, ChunkPayload


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    w = Workspace(id="w1", name="test_ws_docling")
    sess.add(w)
    s = Source(id="s1", workspace_id="w1", source_type="file")
    sess.add(s)
    v = SourceVersion(
        id="v1",
        source_id="s1",
        content_sha256="a" * 64,
        storage_uri="file:///tmp/x",
        ingested_at=datetime.now(timezone.utc),
    )
    sess.add(v)
    d = Document(
        id="doc1",
        source_version_id="v1",
        extractor="docling",
        extractor_version="1",
        structure_json_uri="file:///x",
    )
    sess.add(d)
    sess.commit()
    yield sess
    sess.close()


def test_bulk_upsert_conflict_handling(session):
    """Insert same chunks twice: second call does not raise, inserted count 0 or idempotent."""
    repo = ChunkRepo()
    doc_id = "doc1"
    payloads = [
        ChunkPayload(chunk_hash="h1", chunk_index=0, text="hello"),
        ChunkPayload(chunk_hash="h2", chunk_index=1, text="world"),
    ]
    n1 = repo.bulk_upsert_chunks(session, doc_id, payloads, batch_rows=10)
    session.commit()
    assert n1 == 2
    n2 = repo.bulk_upsert_chunks(session, doc_id, payloads, batch_rows=10)
    session.commit()
    assert n2 == 0
    session.close()
