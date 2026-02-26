"""Chunk text normalization and signature hashing for Stage 1 cache key."""
from __future__ import annotations

import hashlib
import re
import unicodedata


def normalize_chunk_text(text: str) -> str:
    """
    Locked normalization for chunk_content_hash (addressed doc §1.3).
    Any change requires bumping extractor_version.
    """
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in t.split("\n")]
    t = "\n".join(lines).strip()
    # Collapse runs of >2 blank lines to exactly 2 blank lines
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t


def chunk_content_hash(text: str) -> str:
    """SHA-256 hex of normalized chunk text (UTF-8 bytes)."""
    normalized = normalize_chunk_text(text or "")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def signature_hash(
    chunk_content_hash_val: str,
    prompt_version: str,
    extractor_version: str,
    model_id: str,
    params_fingerprint: str,
    force_nonce: str | None = None,
) -> str:
    """
    Cache signature: same inputs → same hash.
    Include force_nonce when --force so this run bypasses cache.
    """
    parts = [
        chunk_content_hash_val,
        prompt_version,
        extractor_version,
        model_id,
        params_fingerprint,
    ]
    if force_nonce:
        parts.append(force_nonce)
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def params_fingerprint(temperature: float, max_tokens: int) -> str:
    """Stable string for temperature + max_tokens (and other critical params)."""
    return f"T{temperature}_M{max_tokens}"
