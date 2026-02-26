"""
LLM module: single typed async interface for all LLM calls.
Public API: LLMService, LLMRequest, LLMResponse, LLMProfile, LLMProvider.
Other modules must not call LiteLLM or provider SDKs directly.
"""
from app.llm.errors import (
    LLMAuthError,
    LLMBadRequest,
    LLMError,
    LLMInProgressError,
    LLMResponseInvalid,
    LLMRateLimited,
    LLMTimeout,
    LLMUnavailable,
    LLMWorkspaceRequiredError,
)
from app.llm.service import LLMService
from app.llm.types import (
    LLMConstraints,
    LLMMessage,
    LLMProfile,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMUsage,
)

__all__ = [
    "LLMService",
    "LLMRequest",
    "LLMResponse",
    "LLMMessage",
    "LLMProfile",
    "LLMProvider",
    "LLMConstraints",
    "LLMUsage",
    "LLMError",
    "LLMTimeout",
    "LLMRateLimited",
    "LLMBadRequest",
    "LLMAuthError",
    "LLMUnavailable",
    "LLMResponseInvalid",
    "LLMInProgressError",
    "LLMWorkspaceRequiredError",
]
