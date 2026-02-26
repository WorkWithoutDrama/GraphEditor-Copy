"""Docling module configuration (Pydantic settings)."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DoclingSettings(BaseSettings):
    """Docling pipeline settings. Env prefix DOCLING_."""

    model_config = SettingsConfigDict(
        env_prefix="DOCLING_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Input limits
    allowed_formats: list[str] = Field(
        default=["PDF", "DOCX", "PPTX", "HTML", "MARKDOWN", "IMAGE"],
        description="Formats passed to DocumentConverter",
    )
    max_file_size_bytes: int = Field(default=20_000_000, description="Max file size (e.g. 20 MB)")
    max_num_pages: int = Field(default=200, description="Max pages per document")

    # Execution
    parse_concurrency: int = Field(default=2, description="Semaphore for parallel conversions")
    use_process_pool: bool = Field(default=True, description="Use process pool for CPU-heavy parsing")
    process_pool_workers: int = Field(default=2, description="Process pool size")

    # Artifacts
    store_docling_json: bool = Field(default=True, description="Store structure JSON (required for re-chunk)")
    store_docling_md: bool = Field(default=False, description="Store markdown export")
    artifact_text_inline_max_chars: int = Field(
        default=200_000,
        description="Threshold for storing text in SQL vs file store",
    )

    # Chunking
    chunker: str = Field(default="hybrid", description="hybrid or hierarchical")
    target_tokens: int = Field(default=800, description="Target chunk size in tokens")
    max_tokens: int = Field(default=1000, description="Hard max tokens per chunk")
    overlap_tokens: int = Field(default=80, description="Overlap between chunks")
    enforce_max_tokens_hard: bool = Field(
        default=True,
        description="Enforce max_tokens with fallback splitter",
    )

    # Idempotency
    dedupe_strategy: str = Field(default="sha256", description="Dedupe strategy")
    rehydrate_from_artifact_json: bool = Field(
        default=True,
        description="Re-chunk from stored JSON without re-parse",
    )

    # Re-parse policy
    allow_reparse_if_failed: bool = Field(default=True, description="Retry conversion if run is FAILED")
    force_reparse: bool = Field(default=False, description="Admin-only: re-parse even if PARSED or later")

    # Performance guardrails
    max_chunks_per_document: int = Field(default=10_000, description="Hard cap on chunks per document")
    parse_timeout_seconds: float = Field(default=300.0, description="Timeout for parse stage")
    chunk_timeout_seconds: float = Field(default=120.0, description="Timeout for chunk stage")

    # Batch persistence
    chunk_batch_rows: int = Field(default=200, description="Chunk insert batch size")
    chunk_batch_max_bytes: int = Field(default=5 * 1024 * 1024, description="Max bytes per chunk batch (5 MB)")
