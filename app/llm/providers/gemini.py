"""Gemini (Google AI Studio) provider: build LiteLLM kwargs. API key passed explicitly."""
from __future__ import annotations

from typing import Any

from app.llm.settings import LLMSettings


def gemini_kwargs(settings: LLMSettings) -> dict[str, Any]:
    """Build provider kwargs for Gemini. Pass api_key explicitly (no os.environ in adapter)."""
    out: dict[str, Any] = {
        "model": settings.gemini_model,
    }
    if settings.gemini_api_key:
        out["api_key"] = settings.gemini_api_key
    if settings.gemini_safety_settings is not None:
        out["safety_settings"] = settings.gemini_safety_settings
    return out
