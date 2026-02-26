"""Typed request/response and constraint models for the LLM module (Pydantic v2)."""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OLLAMA = "ollama"
    GEMINI = "gemini"


class LLMProfile(str, Enum):
    """Routing profile: local-fast, cloud-quality, or auto."""

    LOCAL_FAST = "local_fast"
    CLOUD_QUALITY = "cloud_quality"
    AUTO = "auto"


class LLMMessage(BaseModel):
    """Single message in OpenAI-style format."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str


class LLMRequest(BaseModel):
    """Request for a single chat completion. model_dump() is stable for hashing/idempotency."""

    messages: list[LLMMessage]
    profile: LLMProfile = LLMProfile.AUTO
    temperature: float | None = None
    max_output_tokens: int | None = None
    tools: list[dict[str, Any]] | None = None
    response_format: dict[str, Any] | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    idempotency_key: str | None = None
    timeout_s: float | None = None
    cache_system_prompt: bool = False


class LLMUsage(BaseModel):
    """Token usage and optional cost."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float | None = None


class LLMResponse(BaseModel):
    """Normalized response from any provider."""

    text: str
    raw: dict[str, Any] | None = None
    usage: LLMUsage | None = None
    provider: LLMProvider
    model: str
    latency_ms: int
    finish_reason: str | None = None


class LLMConstraints(BaseModel):
    """Router-friendly constraints for provider selection."""

    max_input_tokens: int | None = None
    max_context_tokens: int | None = None
    requires_tools: bool = False
    requires_json: bool = False
    allow_fallbacks: bool = True
