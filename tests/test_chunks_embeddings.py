"""Phase C: Chunks and embedding pointers — idempotency."""
from datetime import datetime, timezone

import pytest

from app.db.config import DBConfig
from app.db.session import init_db, session_scope
from app.db.repositories.workspace_repo import WorkspaceRepo
from app.db.repositories.source_repo import SourceRepo, SourceVersionRepo
from app.db.repositories.document_repo import DocumentRepo
from app.db.repositories.chunk_repo import ChunkRepo, ChunkPayload
from app.db.repositories.embedding_repo import EmbeddingSetRepo, ChunkEmbeddingRepo
from app.db.services.chunk_persist import ChunkPersistService
from app.db.services.embedding_persist import EmbeddingPersistService


@pytest.fixture
def lineage_data(db_config, db_with_tables):
    init_db(db_config)
    with session_scope() as session:
        w = WorkspaceRepo().create(session, "ws1")
        s = SourceRepo().create(session, w.id, "file")
        now = datetime.now(timezone.utc)
        v = SourceVersionRepo().create_or_get(session, s.id, "a" * 64, "uri", now)
        d = DocumentRepo().create_or_get(
            session, v.id, "docling", "1.0", "s3://struct.json"
        )
        session.commit()
    return {"workspace_id": w.id, "document_id": d.id}


def test_chunk_persist_idempotent(db_config, db_with_tables, lineage_data):
    init_db(db_config)
    doc_id = lineage_data["document_id"]
    payloads = [
        ChunkPayload(chunk_hash="h1", chunk_index=0, text="Hello"),
        ChunkPayload(chunk_hash="h2", chunk_index=1, text="World"),
    ]
    svc = ChunkPersistService()
    with session_scope() as session:
        m1 = svc.persist_chunks(session, doc_id, payloads)
    assert len(m1) == 2
    assert m1["h1"] and m1["h2"]
    with session_scope() as session:
        m2 = svc.persist_chunks(session, doc_id, payloads)
    assert m1["h1"] == m2["h1"] and m1["h2"] == m2["h2"]


def test_embedding_pointers_idempotent(db_config, db_with_tables, lineage_data):
    init_db(db_config)
    # Create chunks first (FK from chunk_embeddings to chunks)
    doc_id = lineage_data["document_id"]
    with session_scope() as session:
        chunk_map = ChunkRepo().bulk_create_or_get(
            session,
            doc_id,
            [
                ChunkPayload(chunk_hash="h1", chunk_index=0),
                ChunkPayload(chunk_hash="h2", chunk_index=1),
            ],
        )
        c1, c2 = chunk_map["h1"], chunk_map["h2"]
        es = EmbeddingSetRepo().create_or_get(
            session,
            lineage_data["workspace_id"],
            "default",
            "text-embedding-3",
            1536,
            "cosine",
            "col1",
        )
        embedding_set_id = es.id
    mapping = {c1: "pt-1", c2: "pt-2"}
    svc = EmbeddingPersistService()
    with session_scope() as session:
        svc.persist_qdrant_refs(session, embedding_set_id, mapping)
    with session_scope() as session:
        svc.persist_qdrant_refs(session, embedding_set_id, mapping)
    with session_scope() as session:
        from app.db.models.embedding import ChunkEmbedding
        from sqlalchemy import select, func
        count = session.execute(
            select(func.count()).select_from(ChunkEmbedding).where(
                ChunkEmbedding.embedding_set_id == embedding_set_id
            )
        ).scalar()
    assert count == 2
