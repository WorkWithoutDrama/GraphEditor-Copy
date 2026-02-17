"""
PydanticAI Model adapter: delegates to LLMService.chat(). v1: non-streaming only.
Tool calls: v1 adapter passes tools through LLMRequest; router routes to supporting provider.
"""
from __future__ import annotations

from typing import Any

from app.llm.service import LLMService
from app.llm.settings import LLMSettings
from app.llm.types import LLMMessage, LLMProfile, LLMRequest


class PydanticAiLiteLLMModel:
    """
    Adapter so PydanticAI agents can use LLMService. Non-streaming only in v1.
    Inject LLMService and optional LLMSettings; request profile can be overridden.
    """

    def __init__(
        self,
        service: LLMService,
        *,
        default_profile: LLMProfile = LLMProfile.LOCAL_FAST,
        workspace_id: str | None = None,
    ) -> None:
        self._service = service
        self._default_profile = default_profile
        self._workspace_id = workspace_id

    async def request(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Single non-streaming request. Converts to LLMRequest and returns a dict with
        'text', 'usage', 'model', 'provider', 'latency_ms' for PydanticAI compatibility.
        """
        llm_messages = [
            LLMMessage(role=m["role"], content=m.get("content", ""))
            for m in messages
            if m.get("role") in ("system", "user", "assistant", "tool")
        ]
        req = LLMRequest(
            messages=llm_messages,
            profile=self._default_profile,
            temperature=temperature,
            max_output_tokens=max_tokens,
            tools=tools,
            response_format=response_format,
            metadata=metadata or {},
        )
        ws = self._workspace_id or (metadata or {}).get("workspace_id")
        resp = await self._service.chat(req, workspace_id=ws)
        out: dict[str, Any] = {
            "text": resp.text,
            "model": resp.model,
            "provider": resp.provider.value,
            "latency_ms": resp.latency_ms,
        }
        if resp.usage:
            out["usage"] = {
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
                "total_tokens": resp.usage.total_tokens,
            }
        return out
