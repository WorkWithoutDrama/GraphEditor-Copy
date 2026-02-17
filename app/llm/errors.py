"""Error taxonomy for LLM module. All map to stable codes for SQL and pipeline decisions."""
from __future__ import annotations

from app.llm.types import LLMProvider


class LLMError(Exception):
    """Base for all LLM errors. code is stable for persistence; details must not leak secrets."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "UNKNOWN",
        retryable: bool = False,
        provider: LLMProvider | None = None,
        details: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.provider = provider
        self.details = details or ""


class LLMTimeout(LLMError):
    """Request timed out."""

    def __init__(self, message: str = "LLM request timed out", **kwargs: object) -> None:
        super().__init__(message, code="TIMEOUT", retryable=True, **kwargs)


class LLMRateLimited(LLMError):
    """Rate limit (429) or quota exceeded."""

    def __init__(self, message: str = "LLM rate limited", **kwargs: object) -> None:
        super().__init__(message, code="RATE_LIMITED", retryable=True, **kwargs)


class LLMBadRequest(LLMError):
    """Invalid request (e.g. schema, params)."""

    def __init__(self, message: str = "LLM bad request", **kwargs: object) -> None:
        super().__init__(message, code="BAD_REQUEST", retryable=False, **kwargs)


class LLMAuthError(LLMError):
    """Authentication or authorization failure."""

    def __init__(self, message: str = "LLM auth error", **kwargs: object) -> None:
        super().__init__(message, code="AUTH_ERROR", retryable=False, **kwargs)


class LLMUnavailable(LLMError):
    """Service unavailable (5xx, connection, etc.)."""

    def __init__(self, message: str = "LLM unavailable", **kwargs: object) -> None:
        super().__init__(message, code="UNAVAILABLE", retryable=True, **kwargs)


class LLMResponseInvalid(LLMError):
    """Response failed validation (e.g. JSON schema mismatch)."""

    def __init__(self, message: str = "LLM response invalid", **kwargs: object) -> None:
        super().__init__(message, code="RESPONSE_INVALID", retryable=False, **kwargs)


class LLMInProgressError(LLMError):
    """Idempotency: a run with the same key is already STARTED (v1: no wait)."""

    def __init__(self, message: str = "LLM run already in progress", **kwargs: object) -> None:
        super().__init__(message, code="IN_PROGRESS", retryable=False, **kwargs)


class LLMWorkspaceRequiredError(LLMError):
    """workspace_id required when persistence is enabled but missing."""

    def __init__(self, message: str = "workspace_id required when persist_runs is True", **kwargs: object) -> None:
        super().__init__(message, code="WORKSPACE_REQUIRED", retryable=False, **kwargs)
