"""Stage 1 v4: build compact embedding (card) text for Qdrant from claim type + value_json."""
from __future__ import annotations


def claim_to_embedding_text_v4(claim_type: str, value: dict) -> str:
    """
    Build canonical card text for v4 claims for embedding and Qdrant payload.
    Formats: ACTOR | <name>; OBJECT | <name>; ACTION | <actor> | <verb> | <object> | <qualifiers>;
    STATE | <object_name> | <state>; DENY | <actor> | <verb> | <object>.
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
        qualifiers = value.get("qualifiers") or []
        qual_str = " ".join(str(q).strip() for q in qualifiers if q)
        if qual_str:
            return f"ACTION | {actor} | {verb} | {obj} | {qual_str}"
        return f"ACTION | {actor} | {verb} | {obj}"
    if claim_type == "STATE":
        obj_name = value.get("object_name", "").strip()
        state = value.get("state", "").strip()
        return f"STATE | {obj_name} | {state}"
    if claim_type == "DENY":
        actor = value.get("actor", "").strip()
        verb = value.get("verb", "").strip()
        obj = value.get("object", "").strip()
        return f"DENY | {actor} | {verb} | {obj}"
    return f"{claim_type} | {value}"
