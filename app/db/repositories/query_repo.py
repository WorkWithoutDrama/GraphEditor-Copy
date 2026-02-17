"""Query and QueryResult repository (optional query logging)."""
from datetime import datetime, timezone
from typing import Any
import json

from sqlalchemy.orm import Session

from app.db.models.query import Query, QueryResult


def _json_dump(d: dict[str, Any] | None) -> str | None:
    if d is None:
        return None
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


class QueryRepo:
    def create_query(
        self,
        session: Session,
        workspace_id: str,
        query_text: str,
        top_k: int,
        embedding_set_id: str | None = None,
        filters_json: str | None = None,
        latency_ms: int | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Query:
        q = Query(
            workspace_id=workspace_id,
            ts=datetime.now(timezone.utc),
            query_text=query_text,
            embedding_set_id=embedding_set_id,
            top_k=top_k,
            filters_json=filters_json,
            latency_ms=latency_ms,
            meta_json=_json_dump(meta),
        )
        session.add(q)
        session.flush()
        return q

    def add_results(
        self,
        session: Session,
        query_id: str,
        results: list[tuple[str, float, float | None]],
    ) -> None:
        """results: list of (chunk_id, score, rerank_score). rank = 0, 1, 2, ..."""
        for rank, (chunk_id, score, rerank_score) in enumerate(results):
            r = QueryResult(
                query_id=query_id,
                rank=rank,
                chunk_id=chunk_id,
                score=score,
                rerank_score=rerank_score,
            )
            session.add(r)
        session.flush()
