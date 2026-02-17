"""Ollama provider: build LiteLLM kwargs from settings. Best-effort local."""
from __future__ import annotations

from typing import Any

from app.llm.settings import LLMSettings


def ollama_kwargs(settings: LLMSettings) -> dict[str, Any]:
    """Build provider kwargs for Ollama. model and api_base from settings."""
    return {
        "model": settings.ollama_model,
        "api_base": settings.ollama_api_base,
    }
