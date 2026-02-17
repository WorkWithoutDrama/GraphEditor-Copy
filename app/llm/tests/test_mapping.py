"""Request/response normalization and exception mapping tests. Map by class name."""
from app.llm.client_litellm import _map_exception
from app.llm.types import LLMProvider


def test_map_timeout() -> None:
    """APITimeoutError / Timeout -> LLMTimeout (mapping uses type name)."""
    class APITimeoutError(Exception):
        pass
    e = APITimeoutError("timeout")
    out = _map_exception(e, LLMProvider.GEMINI)
    assert type(out).__name__ == "LLMTimeout"
    assert out.retryable is True
    assert out.provider == LLMProvider.GEMINI
    assert "APITimeoutError" in (out.details or "")


def test_map_rate_limit() -> None:
    """RateLimitError -> LLMRateLimited."""
    class RateLimitError(Exception):
        pass
    e = RateLimitError("429")
    out = _map_exception(e, LLMProvider.GEMINI)
    assert type(out).__name__ == "LLMRateLimited"
    assert out.retryable is True


def test_map_auth_error() -> None:
    """AuthenticationError -> LLMAuthError."""
    class AuthenticationError(Exception):
        pass
    e = AuthenticationError("invalid key")
    out = _map_exception(e, LLMProvider.GEMINI)
    assert type(out).__name__ == "LLMAuthError"
    assert out.retryable is False


def test_map_bad_request() -> None:
    """BadRequestError -> LLMBadRequest."""
    class BadRequestError(Exception):
        pass
    e = BadRequestError("bad params")
    out = _map_exception(e, LLMProvider.OLLAMA)
    assert type(out).__name__ == "LLMBadRequest"
    assert out.retryable is False


def test_map_unknown_exception() -> None:
    e = ValueError("something else")
    out = _map_exception(e, LLMProvider.GEMINI)
    assert out.provider == LLMProvider.GEMINI
    assert "ValueError" in (out.details or "")
    assert out.code in ("UNKNOWN", "UNAVAILABLE") or type(out).__name__ == "LLMUnavailable"
