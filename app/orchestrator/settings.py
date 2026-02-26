"""MVP orchestrator configuration. Env prefix: ORCH_."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MVPOrchestratorSettings(BaseSettings):
    """Settings for MVP orchestrator pipeline."""

    model_config = SettingsConfigDict(
        env_prefix="ORCH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    max_concurrency: int = Field(default=4, ge=1, description="Max concurrent chunk processing")
    stage1_model_id: str = Field(
        default="ollama/llama3.2",
        description="LLM model for Stage 1 extraction (e.g. ollama/llama3.2)",
    )
    prompt_name: str = Field(default="chunk_extract_v1", description="Legacy prompt name (unused with Stage 1)")
    max_chunk_attempts: int = Field(default=2, ge=1, description="Max retries per chunk on error")
    stop_on_first_error: bool = Field(default=False, description="Abort pipeline on first chunk error")
    force_reprocess: bool = Field(default=False, description="Reprocess all chunks even if already done")
    store_chunk_text_in_sql: bool = Field(default=True, description="Store chunk text in SQL (MVP convenience)")
    default_embedding_set_name: str = Field(
        default="default",
        description="Embedding set name for vector upsert",
    )
