"""Stage 1 v4: validators, schema strictness, golden chunk."""
from __future__ import annotations

import json
import pytest
from pydantic import ValidationError

from app.stage1.schema_v4 import (
    Stage1ResultV4,
    parse_stage1_v4,
    PROMPT_VERSION_V4,
    ActionClaimV4,
    ActorClaimV4,
    ObjectClaimV4,
    EvidenceV4,
    ChunkRefV4,
)
from app.stage1.validators import (
    validate_evidence_substrings,
    validate_bullet_coverage,
)
from app.stage1.cards import claim_to_embedding_text_v4


# ---- Evidence substring ----
def test_validate_evidence_substrings_pass():
    """When all snippets are in chunk, no raise."""
    result = Stage1ResultV4(
        chunk_id="c1",
        summary="x",
        claims=[
            ActorClaimV4(
                type="ACTOR",
                value={"name": "Пользователь"},
                evidence=[
                    EvidenceV4(snippet="Пользователь удаляет", chunk_ref=ChunkRefV4(chunk_id="c1"))
                ],
            ),
        ],
    )
    chunk = "Пользователь удаляет завершенный проект"
    validate_evidence_substrings(result, chunk)


def test_validate_evidence_substrings_fail():
    """When a snippet is not in chunk, raises ValueError."""
    result = Stage1ResultV4(
        chunk_id="c1",
        summary="x",
        claims=[
            ActorClaimV4(
                type="ACTOR",
                value={"name": "Пользователь"},
                evidence=[
                    EvidenceV4(snippet="задача комментарий", chunk_ref=ChunkRefV4(chunk_id="c1"))
                ],
            ),
        ],
    )
    chunk = "Пользователь удаляет проект"
    with pytest.raises(ValueError, match="not a substring"):
        validate_evidence_substrings(result, chunk)


def test_validate_evidence_substrings_normalizes_newlines():
    """CRLF in chunk and snippet still matches after normalize."""
    result = Stage1ResultV4(
        chunk_id="c1",
        summary="x",
        claims=[
            ActorClaimV4(
                type="ACTOR",
                value={"name": "A"},
                evidence=[EvidenceV4(snippet="line one\nline two", chunk_ref=ChunkRefV4(chunk_id="c1"))],
            ),
        ],
    )
    chunk = "line one\r\nline two"
    validate_evidence_substrings(result, chunk)


# ---- Bullet coverage ----
def test_validate_bullet_coverage_all_covered():
    """Three bullets, three ACTION claims with matching evidence -> no warnings."""
    chunk = """3.1.3 Удаление проекта
- Пользователь удаляет завершенный проект
- Пользователь архивирует проект
- Система сохраняет историю проекта
"""
    result = Stage1ResultV4(
        chunk_id="c1",
        summary="x",
        claims=[
            ActionClaimV4(
                type="ACTION",
                value={"actor": "Пользователь", "verb": "удаляет", "object": "Проект", "qualifiers": ["завершенный"]},
                evidence=[EvidenceV4(snippet="Пользователь удаляет завершенный проект", chunk_ref=ChunkRefV4(chunk_id="c1"))],
            ),
            ActionClaimV4(
                type="ACTION",
                value={"actor": "Пользователь", "verb": "архивирует", "object": "Проект", "qualifiers": []},
                evidence=[EvidenceV4(snippet="Пользователь архивирует проект", chunk_ref=ChunkRefV4(chunk_id="c1"))],
            ),
            ActionClaimV4(
                type="ACTION",
                value={"actor": "Система", "verb": "сохраняет", "object": "историю проекта", "qualifiers": []},
                evidence=[EvidenceV4(snippet="Система сохраняет историю проекта", chunk_ref=ChunkRefV4(chunk_id="c1"))],
            ),
        ],
    )
    uncovered = validate_bullet_coverage(result, chunk)
    assert uncovered == []


def test_validate_bullet_coverage_missing_bullet():
    """Two bullets, one ACTION -> one uncovered warning."""
    chunk = """- First bullet
- Second bullet
"""
    result = Stage1ResultV4(
        chunk_id="c1",
        summary="x",
        claims=[
            ActionClaimV4(
                type="ACTION",
                value={"actor": "A", "verb": "v", "object": "O", "qualifiers": []},
                evidence=[EvidenceV4(snippet="First bullet", chunk_ref=ChunkRefV4(chunk_id="c1"))],
            ),
        ],
    )
    uncovered = validate_bullet_coverage(result, chunk)
    assert len(uncovered) == 1
    assert "Second bullet" in uncovered[0]


def test_validate_bullet_coverage_no_bullets():
    """Chunk with no bullet lines -> empty warnings."""
    result = Stage1ResultV4(chunk_id="c1", summary="x", claims=[])
    uncovered = validate_bullet_coverage(result, "Plain paragraph text.")
    assert uncovered == []


# ---- Empty evidence (post-parse validator) ----
def test_empty_evidence_substring_validator_raises():
    """Claim with empty evidence passes Pydantic; validate_evidence_substrings raises with 'at least one evidence'."""
    raw = {
        "prompt_version": PROMPT_VERSION_V4,
        "chunk_id": "c1",
        "summary": "s",
        "claims": [
            {
                "type": "ACTOR",
                "epistemic_tag": "EXPLICIT",
                "confidence": None,
                "value": {"name": "A"},
                "evidence": [],
            }
        ],
        "warnings": [],
    }
    result = parse_stage1_v4(raw, "c1")
    chunk = "A does something"
    with pytest.raises(ValueError, match="at least one evidence"):
        validate_evidence_substrings(result, chunk)


# ---- Snippet length > 300 (normalizer truncates) ----
def test_snippet_over_300_truncated_with_warning():
    """Evidence snippet > 300 chars is truncated by normalizer and warning is added."""
    long_snippet = "x" * 350
    raw = {
        "prompt_version": PROMPT_VERSION_V4,
        "chunk_id": "c1",
        "summary": "s",
        "claims": [
            {
                "type": "OBJECT",
                "epistemic_tag": "EXPLICIT",
                "confidence": None,
                "value": {"name": "O"},
                "evidence": [{"snippet": long_snippet, "chunk_ref": {"chunk_id": "c1"}}],
            }
        ],
        "warnings": [],
    }
    result = parse_stage1_v4(raw, "c1")
    assert len(result.claims) == 1
    assert len(result.claims[0].evidence) == 1
    assert len(result.claims[0].evidence[0].snippet) == 300
    assert any("Truncated evidence" in w for w in result.warnings)


# ---- chunk_ref normalization ----
def test_chunk_ref_missing_or_invalid_normalized():
    """Evidence with missing or invalid chunk_ref gets chunk_id from normalizer; parse succeeds."""
    raw = {
        "prompt_version": PROMPT_VERSION_V4,
        "chunk_id": "chunk-42",
        "summary": "s",
        "claims": [
            {
                "type": "ACTOR",
                "epistemic_tag": "EXPLICIT",
                "confidence": None,
                "value": {"name": "A"},
                "evidence": [
                    {"snippet": "A", "chunk_ref": {}},
                    {"snippet": "Actor A", "chunk_ref": {"char_start": 0}},
                ],
            }
        ],
        "warnings": [],
    }
    result = parse_stage1_v4(raw, "chunk-42")
    assert len(result.claims) == 1
    assert len(result.claims[0].evidence) == 2
    for ev in result.claims[0].evidence:
        assert ev.chunk_ref is not None
        assert ev.chunk_ref.chunk_id == "chunk-42"


# ---- Schema strictness ----
def test_schema_extra_keys_rejected():
    """STATE value with extra key -> ValidationError (extra=forbid)."""
    with pytest.raises(ValidationError):
        parse_stage1_v4(
            {
                "prompt_version": PROMPT_VERSION_V4,
                "chunk_id": "c1",
                "summary": "s",
                "claims": [
                    {
                        "type": "STATE",
                        "epistemic_tag": "EXPLICIT",
                        "confidence": None,
                        "value": {"object_name": "O", "state": "S", "description": "forbidden"},
                        "evidence": [{"snippet": "O S", "chunk_ref": {"chunk_id": "c1"}}],
                    }
                ],
                "warnings": [],
            },
            "c1",
        )


def test_schema_action_missing_verb_rejected():
    """ACTION value without verb -> ValidationError."""
    with pytest.raises(ValidationError):
        parse_stage1_v4(
            {
                "prompt_version": PROMPT_VERSION_V4,
                "chunk_id": "c1",
                "summary": "s",
                "claims": [
                    {
                        "type": "ACTION",
                        "epistemic_tag": "EXPLICIT",
                        "confidence": None,
                        "value": {"actor": "A", "object": "O"},
                        "evidence": [{"snippet": "A does O", "chunk_ref": {"chunk_id": "c1"}}],
                    }
                ],
                "warnings": [],
            },
            "c1",
        )


# ---- Golden chunk ----
GOLDEN_CHUNK = """3.1.3 Удаление проекта
- Пользователь удаляет завершенный проект
- Пользователь архивирует проект
- Система сохраняет историю проекта
"""


def test_golden_chunk_parse_and_validate():
    """Parse golden chunk JSON (as if from LLM) and assert shapes + substring."""
    # Simulate v4 LLM output
    raw = {
        "prompt_version": PROMPT_VERSION_V4,
        "chunk_id": "golden-1",
        "summary": "Удаление и архивирование проекта пользователем, сохранение истории системой.",
        "claims": [
            {"type": "ACTOR", "epistemic_tag": "EXPLICIT", "confidence": None, "value": {"name": "Пользователь"}, "evidence": [{"snippet": "Пользователь удаляет", "chunk_ref": {"chunk_id": "golden-1"}}]},
            {"type": "ACTOR", "epistemic_tag": "EXPLICIT", "confidence": None, "value": {"name": "Система"}, "evidence": [{"snippet": "Система сохраняет", "chunk_ref": {"chunk_id": "golden-1"}}]},
            {"type": "OBJECT", "epistemic_tag": "EXPLICIT", "confidence": None, "value": {"name": "Проект"}, "evidence": [{"snippet": "проект", "chunk_ref": {"chunk_id": "golden-1"}}]},
            {"type": "ACTION", "epistemic_tag": "EXPLICIT", "confidence": None, "value": {"actor": "Пользователь", "verb": "удаляет", "object": "Проект", "qualifiers": ["завершенный"]}, "evidence": [{"snippet": "Пользователь удаляет завершенный проект", "chunk_ref": {"chunk_id": "golden-1"}}]},
            {"type": "ACTION", "epistemic_tag": "EXPLICIT", "confidence": None, "value": {"actor": "Пользователь", "verb": "архивирует", "object": "Проект", "qualifiers": []}, "evidence": [{"snippet": "Пользователь архивирует проект", "chunk_ref": {"chunk_id": "golden-1"}}]},
            {"type": "ACTION", "epistemic_tag": "EXPLICIT", "confidence": None, "value": {"actor": "Система", "verb": "сохраняет", "object": "историю проекта", "qualifiers": []}, "evidence": [{"snippet": "Система сохраняет историю проекта", "chunk_ref": {"chunk_id": "golden-1"}}]},
        ],
        "warnings": [],
    }
    result = parse_stage1_v4(raw, "golden-1")
    actor_names = [c.value.name for c in result.claims if c.type == "ACTOR"]
    object_names = [c.value.name for c in result.claims if c.type == "OBJECT"]
    action_claims = [c for c in result.claims if c.type == "ACTION"]
    state_claims = [c for c in result.claims if c.type == "STATE"]
    deny_claims = [c for c in result.claims if c.type == "DENY"]

    assert "Пользователь" in actor_names
    assert "Система" in actor_names
    assert "Проект" in object_names
    assert len(action_claims) == 3
    assert len(state_claims) == 0
    assert len(deny_claims) == 0

    validate_evidence_substrings(result, GOLDEN_CHUNK)
    uncovered = validate_bullet_coverage(result, GOLDEN_CHUNK)
    assert uncovered == []


# ---- Card text ----
def test_claim_to_embedding_text_v4():
    assert claim_to_embedding_text_v4("ACTOR", {"name": "Пользователь"}) == "ACTOR | Пользователь"
    assert claim_to_embedding_text_v4("OBJECT", {"name": "Проект"}) == "OBJECT | Проект"
    assert claim_to_embedding_text_v4(
        "ACTION",
        {"actor": "Пользователь", "verb": "удаляет", "object": "Проект", "qualifiers": ["завершенный"]},
    ) == "ACTION | Пользователь | удаляет | Проект | завершенный"
    assert claim_to_embedding_text_v4("STATE", {"object_name": "Задача", "state": "Новая"}) == "STATE | Задача | Новая"
    assert claim_to_embedding_text_v4("DENY", {"actor": "A", "verb": "v", "object": "O"}) == "DENY | A | v | O"
