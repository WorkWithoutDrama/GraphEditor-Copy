"""Unit tests for vector store filter compiler."""
from datetime import datetime, timezone

import pytest
from qdrant_client import models as qdrant_models

from app.vectorstore.filters import VectorFilter, compile_filter


def test_compile_filter_workspace_only() -> None:
    vf = VectorFilter(workspace_id="ws-1")
    qf = compile_filter(vf)
    assert isinstance(qf, qdrant_models.Filter)
    assert len(qf.must) == 1
    assert qf.must[0].key == "workspace_id"
    assert qf.must[0].match.value == "ws-1"


def test_compile_filter_with_document() -> None:
    vf = VectorFilter(workspace_id="ws-1", document_id="doc-abc")
    qf = compile_filter(vf)
    assert len(qf.must) == 2
    keys = {c.key for c in qf.must}
    assert keys == {"workspace_id", "document_id"}
    doc_cond = next(c for c in qf.must if c.key == "document_id")
    assert doc_cond.match.value == "doc-abc"


def test_compile_filter_with_time_range() -> None:
    after = datetime(2025, 1, 1, tzinfo=timezone.utc)
    before = datetime(2025, 12, 31, tzinfo=timezone.utc)
    vf = VectorFilter(workspace_id="ws-1", created_after=after, created_before=before)
    qf = compile_filter(vf)
    assert len(qf.must) == 3  # workspace_id + 2 embedded_at conditions
    embedded_conds = [c for c in qf.must if c.key == "embedded_at"]
    assert len(embedded_conds) == 2


def test_compile_filter_with_tags() -> None:
    vf = VectorFilter(workspace_id="ws-1", tags=["a", "b"])
    qf = compile_filter(vf)
    assert len(qf.must) == 2
    tags_cond = next(c for c in qf.must if c.key == "tags")
    assert tags_cond.match.any == ["a", "b"]


def test_compile_filter_workspace_enforced() -> None:
    """workspace_id is always required (no default)."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        VectorFilter()  # type: ignore[call-arg]
    vf = VectorFilter(workspace_id="x")
    assert vf.workspace_id == "x"
