"""Embedding client configuration. Env prefix: EMBED_."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbedSettings(BaseSettings):
    """Settings for Ollama embedding client."""

    model_config = SettingsConfigDict(
        env_prefix="EMBED_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_api_base: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL (embed endpoint)",
    )
    ollama_model: str = Field(
        default="nomic-embed-text",
        description="Ollama embedding model (e.g. nomic-embed-text, mxbai-embed-large)",
    )
    dims: int = Field(default=768, ge=1, description="Expected embedding dimensions (nomic-embed-text=768)")
