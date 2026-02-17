"""Ollama smoke test. Skipped if Ollama not enabled or not running."""
import os

import pytest

from app.llm.settings import LLMSettings
from app.llm.types import LLMMessage, LLMRequest
from app.llm.service import LLMService


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("LLM_OLLAMA_ENABLED", "true").lower() == "false",
    reason="OLLAMA_ENABLED=false",
)
@pytest.mark.asyncio
async def test_ollama_smoke() -> None:
    settings = LLMSettings(ollama_enabled=True, gemini_enabled=False, persist_runs=False)
    service = LLMService(settings)
    req = LLMRequest(
        messages=[LLMMessage(role="user", content="Reply with one word: OK")],
        metadata={"workspace_id": "test-ws"},
    )
    try:
        resp = await service.chat(req)
    except Exception as e:
        pytest.skip(f"Ollama not available: {e}")
    assert resp.text
    assert resp.latency_ms >= 0
    assert resp.provider.value == "ollama"
