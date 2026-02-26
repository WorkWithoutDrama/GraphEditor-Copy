"""Stage 1 v4: validators, schema strictness, golden chunk."""
from __future__ import annotations

import json
import pytest
from pydantic import ValidationError

from app.stage1.schema_v4 import (
    Stage1ResultV4,
    parse_stage1_v4,
    PROMPT_VERSION_V4,
    ActorClaimV4,
    EvidenceV4,
    ChunkRefV4,
)
from app.stage1.validators import validate_evidence_substrings
from app.stage1.cards import (
    build_card_text,
    build_dedupe_key,
    build_embedding_text,
    evidence_snippet_for_payload,
)


# ---- Evidence substring ----
def test_validate_evidence_substrings_pass():
    """When all snippets are in chunk, no claims dropped, returns no warnings."""
    result = Stage1ResultV4(
        chunk_id="c1",
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
    warnings = validate_evidence_substrings(result, chunk)
    assert len(result.claims) == 1
    assert warnings == []


def test_validate_evidence_substrings_drops_only_bad_claim():
    """When a snippet is not in chunk, drop only that claim and return warning (no raise)."""
    result = Stage1ResultV4(
        chunk_id="c1",
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
    warnings = validate_evidence_substrings(result, chunk)
    assert len(result.claims) == 0
    assert any("not a substring" in w for w in warnings)


def test_validate_evidence_substrings_drops_only_invalid_keeps_valid():
    """When one claim has bad evidence and another is valid, only the bad claim is dropped."""
    result = Stage1ResultV4(
        chunk_id="c1",
        claims=[
            ActorClaimV4(
                type="ACTOR",
                value={"name": "Bad"},
                evidence=[EvidenceV4(snippet="not in chunk", chunk_ref=ChunkRefV4(chunk_id="c1"))],
            ),
            ActorClaimV4(
                type="ACTOR",
                value={"name": "Пользователь"},
                evidence=[
                    EvidenceV4(snippet="Пользователь удаляет", chunk_ref=ChunkRefV4(chunk_id="c1"))
                ],
            ),
        ],
    )
    chunk = "Пользователь удаляет проект"
    warnings = validate_evidence_substrings(result, chunk)
    assert len(result.claims) == 1
    assert result.claims[0].value.name == "Пользователь"
    assert any("not a substring" in w for w in warnings)


def test_validate_evidence_substrings_normalizes_newlines():
    """CRLF in chunk and snippet still matches after normalize."""
    result = Stage1ResultV4(
        chunk_id="c1",
        claims=[
            ActorClaimV4(
                type="ACTOR",
                value={"name": "A"},
                evidence=[EvidenceV4(snippet="line one\nline two", chunk_ref=ChunkRefV4(chunk_id="c1"))],
            ),
        ],
    )
    chunk = "line one\r\nline two"
    warnings = validate_evidence_substrings(result, chunk)
    assert len(result.claims) == 1
    assert warnings == []


# ---- Empty evidence (dropped on parse) ----
def test_empty_evidence_claim_dropped_on_parse():
    """Claim with empty evidence is dropped during parse; result has 0 claims, validator does not raise."""
    raw = {
        "prompt_version": PROMPT_VERSION_V4,
        "chunk_id": "c1",
        "claims": [
            {
                "type": "ACTOR",
                "epistemic_tag": "EXPLICIT",
                "value": {"name": "A"},
                "evidence": [],
            }
        ],
        "warnings": [],
    }
    result = parse_stage1_v4(raw, "c1")
    assert len(result.claims) == 0
    chunk = "A does something"
    warnings = validate_evidence_substrings(result, chunk)
    assert warnings == []


# ---- Snippet length > 300 (normalizer truncates) ----
def test_snippet_over_300_truncated_with_warning():
    """Evidence snippet > 300 chars is truncated by normalizer and warning is added."""
    long_snippet = "x" * 350
    raw = {
        "prompt_version": PROMPT_VERSION_V4,
        "chunk_id": "c1",
        "claims": [
            {
                "type": "OBJECT",
                "epistemic_tag": "EXPLICIT",
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


# ---- Evidence as string array (canonical format) ----
def test_evidence_as_string_array_parsed_and_normalized():
    """Evidence as array of strings is normalized to EvidenceV4 with snippet and chunk_ref."""
    raw = [
        {
            "type": "ACTOR",
            "value": {"name": "Пользователь"},
            "evidence": ["пользователь создает документ", "пользователь удаляет документ"],
        },
        {
            "type": "ACTION",
            "value": {"actor": "Пользователь", "verb": "Удаляет", "object": "Документ"},
            "evidence": ["пользователь удаляет документ"],
        },
    ]
    result = parse_stage1_v4(raw, "chunk-1")
    assert len(result.claims) == 2
    # ACTOR: two evidence items
    assert result.claims[0].type == "ACTOR"
    assert len(result.claims[0].evidence) == 2
    assert result.claims[0].evidence[0].snippet == "пользователь создает документ"
    assert result.claims[0].evidence[1].snippet == "пользователь удаляет документ"
    for ev in result.claims[0].evidence:
        assert ev.chunk_ref is not None
        assert ev.chunk_ref.chunk_id == "chunk-1"
    # ACTION: one evidence item
    assert result.claims[1].type == "ACTION"
    assert len(result.claims[1].evidence) == 1
    assert result.claims[1].evidence[0].snippet == "пользователь удаляет документ"
    assert result.claims[1].evidence[0].chunk_ref.chunk_id == "chunk-1"


def test_evidence_as_object_array_still_parsed():
    """Backward compatibility: evidence as [ { \"snippet\": \"...\" } ] still parses and normalizes."""
    raw = {
        "prompt_version": PROMPT_VERSION_V4,
        "chunk_id": "c1",
        "claims": [
            {
                "type": "ACTOR",
                "epistemic_tag": "EXPLICIT",
                "value": {"name": "A"},
                "evidence": [{"snippet": "Actor A"}, {"snippet": "A does something"}],
            }
        ],
        "warnings": [],
    }
    result = parse_stage1_v4(raw, "c1")
    assert len(result.claims) == 1
    assert len(result.claims[0].evidence) == 2
    assert result.claims[0].evidence[0].snippet == "Actor A"
    assert result.claims[0].evidence[1].snippet == "A does something"
    for ev in result.claims[0].evidence:
        assert ev.chunk_ref is not None and ev.chunk_ref.chunk_id == "c1"


# ---- chunk_ref normalization (backward compat: object form) ----
def test_chunk_ref_missing_or_invalid_normalized():
    """Evidence with missing or invalid chunk_ref gets chunk_id from normalizer; parse succeeds."""
    raw = {
        "prompt_version": PROMPT_VERSION_V4,
        "chunk_id": "chunk-42",
        "claims": [
            {
                "type": "ACTOR",
                "epistemic_tag": "EXPLICIT",
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
                "claims": [
                    {
                        "type": "STATE",
                        "epistemic_tag": "EXPLICIT",
                        "value": {"object_name": "O", "state": "S", "description": "forbidden"},
                        "evidence": [{"snippet": "O S", "chunk_ref": {"chunk_id": "c1"}}],
                    }
                ],
                "warnings": [],
            },
            "c1",
        )


def test_state_value_missing_state_normalized():
    """STATE claim with value missing 'state' gets state='(unspecified)' and warning; parse succeeds."""
    raw = {
        "type": "STATE",
        "value": {"object_name": "Система"},
        "evidence": ["Мониторинг состояния системы 24/7"],
    }
    result = parse_stage1_v4(raw, "chunk-1")
    assert len(result.claims) == 1
    assert result.claims[0].type == "STATE"
    assert result.claims[0].value.object_name == "Система"
    assert result.claims[0].value.state == "(unspecified)"
    assert any("STATE" in w and "state" in w for w in result.warnings)


def test_deny_with_empty_value_fields_dropped_on_parse():
    """DENY claim with empty actor/verb/object is dropped during parse; warning added."""
    raw = {
        "prompt_version": PROMPT_VERSION_V4,
        "chunk_id": "c1",
        "claims": [
            {"type": "ACTOR", "epistemic_tag": "EXPLICIT", "value": {"name": "A"}, "evidence": ["Actor A"]},
            {
                "type": "DENY",
                "epistemic_tag": "EXPLICIT",
                "value": {"actor": "", "verb": "", "object": "", "reason": ""},
                "evidence": ["cannot do something"],  # has evidence so dropped by value check, not evidence check
            },
        ],
        "warnings": [],
    }
    result = parse_stage1_v4(raw, "c1")
    assert len(result.claims) == 1
    assert result.claims[0].type == "ACTOR"
    assert any("DENY" in w and "empty" in w for w in result.warnings)


def test_schema_action_missing_verb_rejected():
    """ACTION value without verb -> ValidationError."""
    with pytest.raises(ValidationError):
        parse_stage1_v4(
            {
                "prompt_version": PROMPT_VERSION_V4,
                "chunk_id": "c1",
                "claims": [
                    {
                        "type": "ACTION",
                        "epistemic_tag": "EXPLICIT",
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
    """Parse golden chunk JSON (as if from LLM) and assert shapes + substring. Uses canonical evidence-as-string-array format."""
    # Simulate v4 LLM output (evidence as array of verbatim quote strings)
    raw = {
        "prompt_version": PROMPT_VERSION_V4,
        "chunk_id": "golden-1",
        "claims": [
            {"type": "ACTOR", "epistemic_tag": "EXPLICIT", "value": {"name": "Пользователь"}, "evidence": ["Пользователь удаляет", "Пользователь архивирует"]},
            {"type": "ACTOR", "epistemic_tag": "EXPLICIT", "value": {"name": "Система"}, "evidence": ["Система сохраняет историю проекта"]},
            {"type": "OBJECT", "epistemic_tag": "EXPLICIT", "value": {"name": "Проект"}, "evidence": ["проект", "завершенный проект"]},
            {"type": "ACTION", "epistemic_tag": "EXPLICIT", "value": {"actor": "Пользователь", "verb": "удаляет", "object": "Проект"}, "evidence": ["Пользователь удаляет завершенный проект"]},
            {"type": "ACTION", "epistemic_tag": "EXPLICIT", "value": {"actor": "Пользователь", "verb": "архивирует", "object": "Проект"}, "evidence": ["Пользователь архивирует проект"]},
            {"type": "ACTION", "epistemic_tag": "EXPLICIT", "value": {"actor": "Система", "verb": "сохраняет", "object": "историю проекта"}, "evidence": ["Система сохраняет историю проекта"]},
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


def test_parse_array_root_and_output_schema_shape():
    """Parse root as array of claims (OUTPUT SCHEMA); claims with type, value, evidence (string array or object) validate."""
    # Root = array of claims (no "claims" wrapper); evidence as string array (canonical)
    raw_array = [
        {"type": "ACTOR", "value": {"name": "Система"}, "evidence": ["Система управления"]},
        {"type": "OBJECT", "value": {"name": "Проект"}, "evidence": ["проект"]},
    ]
    result = parse_stage1_v4(raw_array, "chunk-1")
    assert len(result.claims) == 2
    assert result.claims[0].type == "ACTOR"
    assert result.claims[0].value.name == "Система"
    assert result.claims[1].type == "OBJECT"
    assert result.claims[1].value.name == "Проект"
    # evidence gets chunk_ref filled by normalizer
    assert result.claims[0].evidence[0].chunk_ref is not None
    assert result.claims[0].evidence[0].chunk_ref.chunk_id == "chunk-1"


# ---- Card text, embedding text, dedupe_key ----
def test_build_card_text():
    """Card text per claim type (display + payload)."""
    assert build_card_text("ACTOR", {"name": "Пользователь"}) == "ACTOR | Пользователь"
    assert build_card_text("OBJECT", {"name": "Проект"}) == "OBJECT | Проект"
    assert build_card_text(
        "ACTION",
        {"actor": "Пользователь", "verb": "удаляет", "object": "Проект"},
    ) == "ACTION | Пользователь удаляет Проект"
    assert build_card_text("STATE", {"object_name": "Задача", "state": "Новая"}) == "STATE | Задача | Новая"
    assert build_card_text("DENY", {"actor": "A", "verb": "v", "object": "O"}) == "DENY | A !v O"


def test_build_embedding_text():
    """Embedding text includes evidence snippet."""
    assert build_embedding_text("ACTOR", {"name": "Пользователь"}, "") == "ACTOR | Пользователь"
    assert build_embedding_text("ACTOR", {"name": "Пользователь"}, "snippet") == "ACTOR: Пользователь. Evidence: snippet"
    assert build_embedding_text(
        "ACTION",
        {"actor": "A", "verb": "v", "object": "O"},
        "evidence",
    ) == "ACTION: A v O. Evidence: evidence"


def test_build_dedupe_key():
    """Dedupe key is normalized and stable per type."""
    assert build_dedupe_key("ACTOR", {"name": "Пользователь"}) == "actor::пользователь"
    assert build_dedupe_key("ACTOR", {"name": "  A  B  "}) == "actor::a b"
    assert build_dedupe_key("OBJECT", {"name": "Проект"}) == "object::проект"
    assert build_dedupe_key(
        "ACTION",
        {"actor": "A", "verb": "v", "object": "O"},
    ) == "action::a::v::o"
    assert build_dedupe_key("STATE", {"object_name": "X", "state": "Y"}) == "state::x::y"
    assert build_dedupe_key("DENY", {"actor": "A", "verb": "v", "object": "O"}) == "deny::a::v::o"


def test_evidence_snippet_for_payload():
    """Evidence snippet truncated to 300 chars for payload."""
    assert evidence_snippet_for_payload("short") == "short"
    assert len(evidence_snippet_for_payload("x" * 400)) == 300
