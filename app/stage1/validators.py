"""Stage 1 v4 post-parse validators: evidence substring (hard fail), bullet coverage (warnings)."""
from __future__ import annotations

import re

from app.stage1.schema_v4 import Stage1ResultV4


def _normalize_newlines(text: str) -> str:
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")


def validate_evidence_substrings(result: Stage1ResultV4, chunk_text: str) -> None:
    """
    Ensure every claim has at least one evidence and every snippet is a verbatim substring of the chunk.
    Normalizes newlines in both. Raises ValueError if any claim has no evidence or snippet not in chunk.
    """
    chunk_norm = _normalize_newlines(chunk_text)
    for i, claim in enumerate(result.claims):
        if not claim.evidence:
            raise ValueError(
                f"Claim {i} (type={getattr(claim, 'type', '?')}) must have at least one evidence item"
            )
    for claim in result.claims:
        for ev in claim.evidence:
            snippet_norm = _normalize_newlines(ev.snippet)
            if snippet_norm not in chunk_norm:
                raise ValueError(
                    f"Evidence snippet is not a substring of chunk: {ev.snippet[:80]!r}..."
                )


def validate_bullet_coverage(result: Stage1ResultV4, chunk_text: str) -> list[str]:
    """
    If chunk has bullet lines (^-\\s*-\\s*), check each bullet is covered by at least
    one ACTION claim's evidence snippet (snippet equals or is substring of bullet line).
    Returns list of warning strings: "Uncovered bullet: <line>". Does not raise.
    """
    chunk_norm = _normalize_newlines(chunk_text)
    bullet_pattern = re.compile(r"^\s*-\s+.+$", re.MULTILINE)
    bullets = [line.strip() for line in bullet_pattern.findall(chunk_norm)]
    if not bullets:
        return []

    # All evidence snippets from ACTION claims (normalized)
    action_snippets: set[str] = set()
    for claim in result.claims:
        if getattr(claim, "type", None) == "ACTION":
            for ev in claim.evidence:
                action_snippets.add(_normalize_newlines(ev.snippet.strip()))

    uncovered: list[str] = []
    for bullet in bullets:
        bullet_norm = _normalize_newlines(bullet)
        if not bullet_norm:
            continue
        covered = any(
            snip == bullet_norm or snip in bullet_norm or bullet_norm in snip
            for snip in action_snippets
        )
        if not covered:
            uncovered.append(f"Uncovered bullet: {bullet}")
    return uncovered


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
