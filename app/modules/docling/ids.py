"""Deterministic IDs: chunk_hash, chunker_version, idempotency_key (plan A4, Appendix A)."""
import hashlib
import json


def idempotency_key(
    workspace_id: str,
    source_version_id: str,
    job_type: str,
    extractor: str,
    extractor_version: str,
) -> str:
    """idempotency_key = sha256(workspace_id:source_version_id:type:extractor:extractor_version)."""
    payload = f"{workspace_id}:{source_version_id}:{job_type}:{extractor}:{extractor_version}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def chunk_hash(chunker_version: str, chunk_index: int, text_for_embedding: str) -> str:
    """Collision-safe hash for chunk uniqueness.

    chunk_hash = sha256(f"{chunker_version}:{chunk_index}:{text_for_embedding}").
    """
    payload = f"{chunker_version}:{chunk_index}:{text_for_embedding}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def chunker_version_hash(chunk_settings: dict) -> str:
    """Stable hash of chunk settings for chunker_version.

    chunker_version = sha256(json.dumps(chunk_settings, sort_keys=True)).
    """
    canonical = json.dumps(chunk_settings, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
