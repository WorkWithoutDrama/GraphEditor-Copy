"""Router selection and fallback policy tests (no network)."""
import pytest

from app.llm.settings import LLMSettings
from app.llm.types import LLMConstraints, LLMProfile, LLMProvider, LLMRequest, LLMMessage
from app.llm.router import LLMRouter


def _req(profile: LLMProfile = LLMProfile.AUTO, tools: list | None = None, response_format: dict | None = None) -> LLMRequest:
    return LLMRequest(
        messages=[LLMMessage(role="user", content="Hi")],
        profile=profile,
        tools=tools,
        response_format=response_format,
    )


def test_router_selects_ollama_by_default_when_enabled() -> None:
    settings = LLMSettings(ollama_enabled=True, gemini_enabled=False)
    router = LLMRouter(settings)
    provider = router.select_provider(_req(), LLMConstraints())
    assert provider == LLMProvider.OLLAMA


def test_router_selects_gemini_when_ollama_disabled() -> None:
    settings = LLMSettings(ollama_enabled=False, gemini_enabled=True, gemini_api_key="test-key")
    router = LLMRouter(settings)
    provider = router.select_provider(_req(), LLMConstraints())
    assert provider == LLMProvider.GEMINI


def test_router_forces_cloud_when_requires_json_and_flag_set() -> None:
    settings = LLMSettings(
        ollama_enabled=True,
        gemini_enabled=True,
        gemini_api_key="key",
        force_cloud_for_json=True,
    )
    router = LLMRouter(settings)
    constraints = LLMConstraints(requires_json=True)
    provider = router.select_provider(_req(response_format={"type": "json_object"}), constraints)
    assert provider == LLMProvider.GEMINI


def test_router_forces_cloud_when_requires_tools_and_flag_set() -> None:
    settings = LLMSettings(
        ollama_enabled=True,
        gemini_enabled=True,
        gemini_api_key="key",
        force_cloud_for_tools=True,
    )
    router = LLMRouter(settings)
    constraints = LLMConstraints(requires_tools=True)
    provider = router.select_provider(_req(tools=[{"type": "function", "function": {}}]), constraints)
    assert provider == LLMProvider.GEMINI


def test_router_prefer_local() -> None:
    settings = LLMSettings(
        ollama_enabled=True,
        gemini_enabled=True,
        gemini_api_key="key",
        router_policy="prefer_local",
    )
    router = LLMRouter(settings)
    provider = router.select_provider(_req(), LLMConstraints())
    assert provider == LLMProvider.OLLAMA


def test_router_prefer_cloud() -> None:
    settings = LLMSettings(
        ollama_enabled=True,
        gemini_enabled=True,
        gemini_api_key="key",
        router_policy="prefer_cloud",
    )
    router = LLMRouter(settings)
    provider = router.select_provider(_req(), LLMConstraints())
    assert provider == LLMProvider.GEMINI


def test_get_model_for_provider() -> None:
    settings = LLMSettings(ollama_model="ollama/llama3", gemini_model="gemini/gemini-2.0-flash", gemini_api_key="k")
    router = LLMRouter(settings)
    assert router.get_model_for_provider(LLMProvider.OLLAMA) == "ollama/llama3"
    assert router.get_model_for_provider(LLMProvider.GEMINI) == "gemini/gemini-2.0-flash"


def test_get_fallback_order() -> None:
    settings = LLMSettings(ollama_enabled=True, gemini_enabled=True, gemini_api_key="k")
    router = LLMRouter(settings)
    order = router.get_fallback_order()
    assert LLMProvider.OLLAMA in order
    assert LLMProvider.GEMINI in order
