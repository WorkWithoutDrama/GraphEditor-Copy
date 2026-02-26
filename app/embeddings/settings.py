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
    ollama_keep_alive: str = Field(
        default="30m",
        description="Ollama keep_alive for embed model (e.g. 30m, 1h, -1 for indefinite); prevents model unload between requests",
    )
    embed_timeout: float = Field(
        default=180.0,
        ge=1.0,
        description="Timeout in seconds for each embed request (cold model load can exceed 60s)",
    )
    dims: int = Field(default=768, ge=1, description="Expected embedding dimensions (nomic-embed-text=768)")
