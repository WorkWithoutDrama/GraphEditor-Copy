"""Stage 1 v4 post-parse validators: evidence substring (drop invalid claims only)."""
from __future__ import annotations

from app.stage1.schema_v4 import Stage1ResultV4


def _normalize_newlines(text: str) -> str:
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")


def validate_evidence_substrings(result: Stage1ResultV4, chunk_text: str) -> list[str]:
    """
    Drop claims whose evidence is invalid: no evidence, or any snippet not a verbatim substring of the chunk.
    Mutates result.claims in place. Returns list of warning strings for dropped claims.
    Does not drop the entire chunk extraction.
    """
    chunk_norm = _normalize_newlines(chunk_text)
    warnings: list[str] = []
    kept: list = []
    for i, claim in enumerate(result.claims):
        if not claim.evidence:
            warnings.append(
                f"Dropped claim {i} (type={getattr(claim, 'type', '?')}): no evidence"
            )
            continue
        bad = False
        for ev in claim.evidence:
            snippet_norm = _normalize_newlines(ev.snippet)
            if snippet_norm not in chunk_norm:
                bad = True
                break
        if bad:
            warnings.append(
                f"Dropped claim {i} (type={getattr(claim, 'type', '?')}): evidence not a substring of chunk"
            )
            continue
        kept.append(claim)
    result.claims = kept
    return warnings


def validate_name_backed_by_evidence(result: Stage1ResultV4) -> list[str]:
    """
    Optional: for each Actor/Object name, ensure at least one evidence snippet
    contains that name (case-insensitive). Returns list of warning strings for violations.
    """
    warnings: list[str] = []
    for claim in result.claims:
        ctype = getattr(claim, "type", None)
        if ctype not in ("ACTOR", "OBJECT"):
            continue
        name = getattr(claim.value, "name", None)
        if not name:
            continue
        name_lower = name.lower()
        snippets = " ".join(
            _normalize_newlines(ev.snippet) for ev in claim.evidence
        ).lower()
        if name_lower not in snippets:
            warnings.append(f"Name {name!r} not found in evidence snippets")
    return warnings
