"""Vector store (Qdrant) configuration."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class VectorStoreSettings(BaseSettings):
    """Qdrant client and repository settings."""

    model_config = SettingsConfigDict(
        env_prefix="QDRANT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = Field(default="http://localhost:6333", description="Qdrant server URL")
    api_key: str | None = Field(default=None, description="Qdrant API key (optional)")
    prefer_grpc: bool = Field(default=False, description="Use gRPC instead of REST")
    timeout_s: float = Field(default=10.0, description="Request timeout in seconds")
    retries: int = Field(default=3, description="Max retries for transient errors")
    retry_backoff_base_s: float = Field(default=0.5, description="Base delay for exponential backoff")
    schema_version: int = Field(default=1, description="Schema version for collection naming")
    workspace_enforced: bool = Field(default=True, description="Require workspace_id in all operations")
    upsert_batch_size: int = Field(default=256, description="Default batch size for upserts")
