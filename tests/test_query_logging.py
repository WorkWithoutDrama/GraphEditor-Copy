"""Phase E: Query logging — store query + results, uniqueness on rank."""
import pytest

from app.db.config import DBConfig
from app.db.session import init_db, session_scope
from app.db.repositories.workspace_repo import WorkspaceRepo
from app.db.repositories.source_repo import SourceRepo, SourceVersionRepo
from app.db.repositories.document_repo import DocumentRepo
from app.db.repositories.chunk_repo import ChunkRepo, ChunkPayload
from app.db.repositories.query_repo import QueryRepo


@pytest.fixture
def workspace_and_chunks(db_config, db_with_tables):
    init_db(db_config)
    with session_scope() as session:
        w = WorkspaceRepo().create(session, "ws1")
        s = SourceRepo().create(session, w.id, "file")
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        v = SourceVersionRepo().create_or_get(session, s.id, "a" * 64, "uri", now)
        d = DocumentRepo().create_or_get(session, v.id, "docling", "1.0", "s3://struct.json")
        chunk_map = ChunkRepo().bulk_create_or_get(
            session, d.id,
            [ChunkPayload(chunk_hash="h1", chunk_index=0), ChunkPayload(chunk_hash="h2", chunk_index=1)],
        )
    return {"workspace_id": w.id, "chunk_ids": list(chunk_map.values())}


def test_store_query_and_results(db_config, db_with_tables, workspace_and_chunks):
    init_db(db_config)
    repo = QueryRepo()
    chunk_ids = workspace_and_chunks["chunk_ids"]
    with session_scope() as session:
        q = repo.create_query(
            session,
            workspace_and_chunks["workspace_id"],
            "test query",
            top_k=2,
            latency_ms=10,
        )
        query_id = q.id
        repo.add_results(
            session,
            query_id,
            [(chunk_ids[0], 0.9, None), (chunk_ids[1], 0.8, 0.85)],
        )
    with session_scope() as session:
        from app.db.models.query import QueryResult
        from sqlalchemy import select
        results = session.execute(
            select(QueryResult).where(QueryResult.query_id == query_id).order_by(QueryResult.rank)
        ).scalars().all()
        assert len(results) == 2
        assert results[0].rank == 0 and results[1].rank == 1
        assert results[0].chunk_id == chunk_ids[0]
        assert results[1].rerank_score == 0.85
