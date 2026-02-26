"""LLM run repository. Bound to caller's session; does not commit."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.persistence.models import LLMRun


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LLMRunRepo:
    """Persistence for llm_runs. Session-bound; caller commits."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
        """Create run in STARTED status; return run id."""
        run_id = str(uuid4())
        row = LLMRun(
            id=run_id,
            workspace_id=workspace_id,
            pipeline_run_id=pipeline_run_id,
            stage=stage,
            provider=provider,
            model=model,
            profile=profile,
            status="STARTED",
            idempotency_key=idempotency_key,
            prompt_sha256=prompt_sha256,
        )
        self._session.add(row)
        await self._session.flush()
        return run_id

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
        """Update run to SUCCEEDED."""
        result = await self._session.execute(select(LLMRun).where(LLMRun.id == run_id))
        row = result.scalar_one_or_none()
        if not row:
            return
        row.status = "SUCCEEDED"
        row.response_sha256 = response_sha256
        row.response_preview = response_preview
        row.prompt_preview = prompt_preview
        row.latency_ms = latency_ms
        row.input_tokens = input_tokens
        row.output_tokens = output_tokens
        row.total_tokens = total_tokens
        row.cost_usd = cost_usd
        row.cached_response_text = response_text
        await self._session.flush()

    async def mark_failed(
        self,
        run_id: str,
        error_code: str,
        error_message: str,
        error_details_json: str | None = None,
    ) -> None:
        """Update run to FAILED."""
        result = await self._session.execute(select(LLMRun).where(LLMRun.id == run_id))
        row = result.scalar_one_or_none()
        if not row:
            return
        row.status = "FAILED"
        row.error_code = error_code
        row.error_message = error_message
        row.error_details_json = error_details_json
        await self._session.flush()

    async def get_by_idempotency_key(self, key: str) -> dict | None:
        """Return stored result for replay if SUCCEEDED run exists."""
        result = await self._session.execute(
            select(LLMRun).where(
                LLMRun.idempotency_key == key,
                LLMRun.status == "SUCCEEDED",
            )
        )
        row = result.scalar_one_or_none()
        if not row or not row.cached_response_text:
            return None
        return {
            "text": row.cached_response_text,
            "provider": row.provider,
            "model": row.model,
            "latency_ms": row.latency_ms or 0,
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "total_tokens": row.total_tokens,
        }

    async def get_by_status_and_idempotency_key(self, key: str) -> str | None:
        """Return status if run exists; else None."""
        result = await self._session.execute(
            select(LLMRun.status).where(LLMRun.idempotency_key == key)
        )
        return result.scalar_one_or_none()

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
        """Store response for idempotent replay (update the run we already have)."""
        result = await self._session.execute(select(LLMRun).where(LLMRun.id == run_id))
        row = result.scalar_one_or_none()
        if not row:
            return
        row.cached_response_text = response_text
        row.response_sha256 = response_sha256
        row.latency_ms = latency_ms
        row.input_tokens = input_tokens
        row.output_tokens = output_tokens
        row.total_tokens = total_tokens
        await self._session.flush()

    async def get_cached(
        self,
        prompt_sha256: str,
        model: str,
        profile: str,
        ttl_s: int,
    ) -> dict | None:
        """Return cached response if found and not expired."""
        from datetime import timedelta
        cutoff = _utc_now() - timedelta(seconds=ttl_s)
        result = await self._session.execute(
            select(LLMRun).where(
                LLMRun.prompt_sha256 == prompt_sha256,
                LLMRun.model == model,
                LLMRun.profile == profile,
                LLMRun.status == "SUCCEEDED",
                LLMRun.cached_response_text.isnot(None),
                LLMRun.updated_at >= cutoff,
            ).order_by(LLMRun.updated_at.desc()).limit(1)
        )
        row = result.scalar_one_or_none()
        if not row or not row.cached_response_text:
            return None
        return {
            "text": row.cached_response_text,
            "provider": row.provider,
            "model": row.model,
            "latency_ms": row.latency_ms or 0,
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "total_tokens": row.total_tokens,
        }

    async def set_cached(
        self,
        prompt_sha256: str,
        model: str,
        profile: str,
        response_data: dict,
        ttl_s: int,
    ) -> None:
        """Store response in cache (we reuse mark_succeeded + cached_response_text; no separate cache table)."""
        # Cache is implemented via SUCCEEDED rows with same prompt_sha256/model/profile; get_cached looks them up.
        # So set_cached is a no-op here unless we add a dedicated cache table. For v1 we only have idempotency replay.
        # Caller will have already called mark_succeeded; cache hit is just get_cached returning that row.
        pass
