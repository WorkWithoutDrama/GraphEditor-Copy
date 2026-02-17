"""Port interfaces for the LLM module. Other modules depend on these, not on implementations."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.llm.types import LLMConstraints, LLMProvider, LLMRequest, LLMResponse


@runtime_checkable
class LLMClientPort(Protocol):
    """Low-level, provider-agnostic completion. Used by router/service."""

    async def acompletion(
        self,
        provider: LLMProvider,
        model: str,
        req: LLMRequest,
        *,
        timeout_s: float | None = None,
        api_base: str | None = None,
        api_key: str | None = None,
    ) -> LLMResponse:
        """Execute one completion for the given provider/model. Raises LLMError on failure."""
        ...


@runtime_checkable
class LLMRunRepoPort(Protocol):
    """Persistence for LLM runs. Bound to caller's session; methods do not commit."""

    async def create_started(
        self,
        workspace_id: str,
        provider: str,
        model: str,
        profile: str,
        prompt_sha256: str,
        idempotency_key: str | None = None,
        pipeline_run_id: str | None = None,
        stage: str | None = None,
    ) -> str:
        """Create a run in STARTED status; return run id."""
        ...

    async def mark_succeeded(
        self,
        run_id: str,
        response_text: str,
        response_sha256: str,
        latency_ms: int,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        cost_usd: float | None = None,
        response_preview: str | None = None,
        prompt_preview: str | None = None,
    ) -> None:
        """Update run to SUCCEEDED with usage and previews."""
        ...

    async def mark_failed(
        self,
        run_id: str,
        error_code: str,
        error_message: str,
        error_details_json: str | None = None,
    ) -> None:
        """Update run to FAILED."""
        ...

    async def get_by_idempotency_key(self, key: str) -> dict | None:
        """Return stored result for replay if SUCCEEDED run exists; else None."""
        ...

    async def get_by_status_and_idempotency_key(self, key: str) -> str | None:
        """Return status ('STARTED'|'SUCCEEDED'|'FAILED') if run exists; else None."""
        ...

    async def save_result_for_idempotency_key(
        self,
        key: str,
        run_id: str,
        response_text: str,
        response_sha256: str,
        latency_ms: int,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        provider: str,
        model: str,
    ) -> None:
        """Store response for idempotent replay (called after mark_succeeded)."""
        ...

    async def get_cached(
        self,
        prompt_sha256: str,
        model: str,
        profile: str,
        ttl_s: int,
    ) -> dict | None:
        """Return cached response if found and not expired; else None."""
        ...

    async def set_cached(
        self,
        prompt_sha256: str,
        model: str,
        profile: str,
        response_data: dict,
        ttl_s: int,
    ) -> None:
        """Store response in cache."""
        ...
