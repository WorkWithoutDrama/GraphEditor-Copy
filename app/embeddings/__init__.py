"""Embeddings module: Ollama embed client for vector generation."""
from app.embeddings.ollama import OllamaEmbedClient
from app.embeddings.settings import EmbedSettings

__all__ = ["EmbedSettings", "OllamaEmbedClient"]
