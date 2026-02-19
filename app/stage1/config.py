"""Stage 1 configuration (prompt version, model, caching, limits)."""
from __future__ import annotations

from pydantic import BaseModel, Field


# Bump when schema, normalization, or prompt contract changes.
STAGE1_EXTRACTOR_VERSION = "3.0.0"

# Claim count limits (addressed doc D0.4)
CLAIMS_SOFT_WARNING = 50
CLAIMS_HARD_LIMIT = 200

# Repair prompt: max chars of raw output to send (addressed doc §2.3)
REPAIR_RAW_MAX_CHARS = 12_000
REPAIR_RAW_HEAD_CHARS = 2_000
REPAIR_RAW_TAIL_CHARS = 10_000


class Stage1Config(BaseModel):
    """Configuration for one Stage 1 run. Stored in run config_json for reproducibility."""

    prompt_version: str = Field(default="chunk_claims_extract_v4_minimal_explicit", description="Semantic prompt version")
    extractor_version: str = Field(default_factory=lambda: STAGE1_EXTRACTOR_VERSION)
    model_id: str = Field(..., description="Provider/model e.g. ollama/llama3.2")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=256, le=32768)
    concurrency: int = Field(default=4, ge=1, le=32)
    repair_attempts: int = Field(default=1, ge=0, le=3)
    timeout_s: float = Field(default=240.0, gt=0, description="Timeout in seconds for LLM extraction and repair calls")
    embed_claims: bool = Field(default=True)
    qdrant_collection: str = Field(default="claims_v1")
    embedding_model_id: str | None = Field(default=None, description="Default: use app embedding model")
    # Limits
    claims_soft_warning: int = Field(default=CLAIMS_SOFT_WARNING)
    claims_hard_limit: int = Field(default=CLAIMS_HARD_LIMIT)
    repair_raw_max_chars: int = Field(default=REPAIR_RAW_MAX_CHARS)
    # Force reprocess (bypass cache) by adding nonce to signature
    force_nonce: str | None = Field(default=None)
