"""Gemini smoke test. Skipped if no API key."""
import os

import pytest

from app.llm.settings import LLMSettings
from app.llm.types import LLMMessage, LLMRequest
from app.llm.service import LLMService


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("LLM_GEMINI_API_KEY"),
    reason="LLM_GEMINI_API_KEY not set",
)
@pytest.mark.asyncio
async def test_gemini_smoke() -> None:
    settings = LLMSettings(ollama_enabled=False, gemini_enabled=True, persist_runs=False)
    service = LLMService(settings)
    req = LLMRequest(
        messages=[LLMMessage(role="user", content="Reply with one word: OK")],
        metadata={"workspace_id": "test-ws"},
    )
    resp = await service.chat(req)
    assert resp.text
    assert resp.latency_ms >= 0
    assert resp.provider.value == "gemini"
