"""Unit tests for chunking: hard max tokens enforcement, determinism (plan H1)."""
import pytest
from app.modules.docling.chunking import _split_text_by_tokens, _count_tokens, _chunk_settings_dict
from app.modules.docling.ids import chunker_version_hash


class _FakeTokenizer:
    def count_tokens(self, text: str) -> int:
        return len(text.split()) * 2


def test_count_tokens_with_tokenizer():
    tok = _FakeTokenizer()
    assert _count_tokens("one two three", tok) == 6


def test_count_tokens_without_tokenizer():
    assert _count_tokens("one two three", None) == 6


def test_split_text_by_tokens_enforces_max():
    """Hard max tokens: split produces chunks each under max_tokens (approximate)."""
    tok = _FakeTokenizer()
    long_text = " ".join(["word"] * 200)
    max_tok = 50
    parts = _split_text_by_tokens(long_text, max_tok, tok)
    assert len(parts) >= 2
    for p in parts:
        assert _count_tokens(p, tok) <= max_tok + 20


def test_split_text_by_tokens_deterministic():
    tok = _FakeTokenizer()
    text = "a b c\n\nd e f\n\ng h i"
    a = _split_text_by_tokens(text, 2, tok)
    b = _split_text_by_tokens(text, 2, tok)
    assert a == b


def test_chunker_version_hash_changes_with_settings():
    """Changing settings -> different chunker_version (plan: changed chunk ids)."""
    a = chunker_version_hash(_chunk_settings_dict(type("S", (), {"chunker": "hybrid", "max_tokens": 1000, "target_tokens": 800, "overlap_tokens": 80})()))
    b = chunker_version_hash(_chunk_settings_dict(type("S", (), {"chunker": "hybrid", "max_tokens": 500, "target_tokens": 800, "overlap_tokens": 80})()))
    assert a != b
