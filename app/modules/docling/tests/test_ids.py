"""Unit tests for ids: chunk_hash, chunker_version determinism."""
import pytest
from app.modules.docling.ids import chunk_hash, chunker_version_hash


def test_chunk_hash_deterministic():
    a = chunk_hash("v1", 0, "hello world")
    b = chunk_hash("v1", 0, "hello world")
    assert a == b


def test_chunk_hash_different_inputs():
    a = chunk_hash("v1", 0, "hello")
    b = chunk_hash("v1", 1, "hello")
    c = chunk_hash("v1", 0, "world")
    assert a != b != c


def test_chunker_version_hash_deterministic():
    settings = {"chunker": "hybrid", "max_tokens": 1000}
    a = chunker_version_hash(settings)
    b = chunker_version_hash(settings)
    assert a == b


def test_chunker_version_hash_order_independent():
    a = chunker_version_hash({"a": 1, "b": 2})
    b = chunker_version_hash({"b": 2, "a": 1})
    assert a == b
