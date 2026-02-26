"""Stage 1 v4: card text, embedding text, and dedupe_key for Qdrant claim indexing."""
from __future__ import annotations

import re

EVIDENCE_SNIPPET_MAX_LENGTH = 300


def _normalize(s: str) -> str:
    """Normalize for dedupe_key: strip, collapse internal spaces to one, lowercase (RU-safe)."""
    if not s or not isinstance(s, str):
        return ""
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s.lower()


def build_card_text(claim_type: str, value: dict) -> str:
    """
    Build display card text for v4 claims (stored in Qdrant payload).
    ACTOR | <name>; OBJECT | <name>; ACTION | <actor> <verb> <object> [| q=...];
    STATE | <object_name> | <state>; DENY | <actor> !<verb> <object>.
    """
    if not value:
        return f"{claim_type} |"
    if claim_type == "ACTOR":
        return f"ACTOR | {value.get('name', '').strip()}"
    if claim_type == "OBJECT":
        return f"OBJECT | {value.get('name', '').strip()}"
    if claim_type == "ACTION":
        actor = value.get("actor", "").strip()
        verb = value.get("verb", "").strip()
        obj = value.get("object", "").strip()
        card = f"ACTION | {actor} {verb} {obj}"
        qualifiers = value.get("qualifiers")
        if isinstance(qualifiers, list) and qualifiers:
            q_str = ",".join(str(q).strip() for q in qualifiers[:5])
            if q_str:
                card += f" | q={q_str}"
        return card
    if claim_type == "STATE":
        obj_name = value.get("object_name", "").strip()
        state = value.get("state", "").strip()
        return f"STATE | {obj_name} | {state}"
    if claim_type == "DENY":
        actor = value.get("actor", "").strip()
        verb = value.get("verb", "").strip()
        obj = value.get("object", "").strip()
        return f"DENY | {actor} !{verb} {obj}"
    return f"{claim_type} | {value}"


def build_embedding_text(claim_type: str, value: dict, evidence_snippet: str) -> str:
    """
    Build text to embed: card-style line plus evidence. Used for vector embedding.
    Snippet truncated to EVIDENCE_SNIPPET_MAX_LENGTH.
    """
    card = build_card_text(claim_type, value)
    snippet = (evidence_snippet or "").strip()
    if len(snippet) > EVIDENCE_SNIPPET_MAX_LENGTH:
        snippet = snippet[: EVIDENCE_SNIPPET_MAX_LENGTH]
    if not snippet:
        return card
    # Plan §4.1: "ACTOR: <ActorName>. Evidence: <snippet>", etc.
    if claim_type == "ACTOR":
        name = value.get("name", "").strip() if value else ""
        return f"ACTOR: {name}. Evidence: {snippet}"
    if claim_type == "OBJECT":
        name = value.get("name", "").strip() if value else ""
        return f"OBJECT: {name}. Evidence: {snippet}"
    if claim_type == "ACTION":
        actor = value.get("actor", "").strip() if value else ""
        verb = value.get("verb", "").strip() if value else ""
        obj = value.get("object", "").strip() if value else ""
        return f"ACTION: {actor} {verb} {obj}. Evidence: {snippet}"
    if claim_type == "STATE":
        obj_name = value.get("object_name", "").strip() if value else ""
        state = value.get("state", "").strip() if value else ""
        return f"STATE: {obj_name} is {state}. Evidence: {snippet}"
    if claim_type == "DENY":
        actor = value.get("actor", "").strip() if value else ""
        verb = value.get("verb", "").strip() if value else ""
        obj = value.get("object", "").strip() if value else ""
        return f"DENY: {actor} cannot {verb} {obj}. Evidence: {snippet}"
    return f"{card}. Evidence: {snippet}"


def build_dedupe_key(claim_type: str, value: dict) -> str:
    """
    Deterministic key for Stage-2 result grouping. Uses normalized value fields.
    """
    if not value:
        return f"{claim_type.lower()}::"
    if claim_type == "ACTOR":
        n = _normalize(str(value.get("name", "")))
        return f"actor::{n}"
    if claim_type == "OBJECT":
        n = _normalize(str(value.get("name", "")))
        return f"object::{n}"
    if claim_type == "ACTION":
        a = _normalize(str(value.get("actor", "")))
        v = _normalize(str(value.get("verb", "")))
        o = _normalize(str(value.get("object", "")))
        return f"action::{a}::{v}::{o}"
    if claim_type == "STATE":
        o = _normalize(str(value.get("object_name", "")))
        s = _normalize(str(value.get("state", "")))
        return f"state::{o}::{s}"
    if claim_type == "DENY":
        a = _normalize(str(value.get("actor", "")))
        v = _normalize(str(value.get("verb", "")))
        o = _normalize(str(value.get("object", "")))
        return f"deny::{a}::{v}::{o}"
    return f"{claim_type.lower()}::"


def evidence_snippet_for_payload(snippet: str) -> str:
    """Truncate evidence snippet for Qdrant payload (<=300 chars)."""
    s = (snippet or "").strip()
    if len(s) > EVIDENCE_SNIPPET_MAX_LENGTH:
        return s[: EVIDENCE_SNIPPET_MAX_LENGTH]
    return s
