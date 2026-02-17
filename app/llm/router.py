"""LLMRouter: injectable router with capability matrix and deterministic fallback."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.llm.settings import LLMSettings
from app.llm.types import LLMConstraints, LLMProfile, LLMProvider, LLMRequest


@dataclass
class ProviderCaps:
    """Per-provider capabilities for routing."""

    supports_tools: bool
    supports_json: bool
    max_context_tokens: int | None = None


# Capability matrix: used by LLMRouter for selection
PROVIDER_CAPABILITIES: dict[LLMProvider, ProviderCaps] = {
    LLMProvider.OLLAMA: ProviderCaps(
        supports_tools=False,
        supports_json=True,
        max_context_tokens=4096,
    ),
    LLMProvider.GEMINI: ProviderCaps(
        supports_tools=True,
        supports_json=True,
        max_context_tokens=1_000_000,
    ),
}


class LLMRouter:
    """Select provider from profile and constraints; supports fallback on retryable errors."""

    def __init__(self, settings: LLMSettings) -> None:
        self._settings = settings
        self._caps = PROVIDER_CAPABILITIES

    def select_provider(self, req: LLMRequest, constraints: LLMConstraints) -> LLMProvider:
        """Choose the provider for this request. Does not perform the call."""
        if constraints.requires_tools and self._settings.force_cloud_for_tools:
            if self._settings.gemini_enabled:
                return LLMProvider.GEMINI
        if constraints.requires_json and self._settings.force_cloud_for_json:
            if self._settings.gemini_enabled:
                return LLMProvider.GEMINI
        profile = req.profile
        if profile == LLMProfile.AUTO:
            profile = self._settings.default_profile
        policy = self._settings.router_policy
        if policy == "prefer_local" or profile == LLMProfile.LOCAL_FAST:
            if self._settings.ollama_enabled:
                return LLMProvider.OLLAMA
            if self._settings.gemini_enabled:
                return LLMProvider.GEMINI
        if policy == "prefer_cloud" or profile == LLMProfile.CLOUD_QUALITY:
            if self._settings.gemini_enabled:
                return LLMProvider.GEMINI
            if self._settings.ollama_enabled:
                return LLMProvider.OLLAMA
        # auto: prefer local then cloud
        if self._settings.ollama_enabled:
            return LLMProvider.OLLAMA
        if self._settings.gemini_enabled:
            return LLMProvider.GEMINI
        raise ValueError("No LLM provider enabled (ollama_enabled and gemini_enabled are false)")

    def get_model_for_provider(self, provider: LLMProvider) -> str:
        """Return the model string for the given provider."""
        if provider == LLMProvider.OLLAMA:
            return self._settings.ollama_model
        if provider == LLMProvider.GEMINI:
            return self._settings.gemini_model
        raise ValueError(f"Unknown provider: {provider}")

    def get_fallback_order(self) -> list[LLMProvider]:
        """Return provider list for fallback (only enabled ones)."""
        order: list[LLMProvider] = []
        for p in self._settings.fallback_order:
            if p == LLMProvider.OLLAMA and self._settings.ollama_enabled:
                order.append(p)
            if p == LLMProvider.GEMINI and self._settings.gemini_enabled:
                order.append(p)
        return order
