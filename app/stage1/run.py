"""Stage 1 run entrypoint: chunk selection, extract, persist, embed."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.db.repositories.chunk_repo import ChunkRepo
from app.db.session import session_scope
from app.stage1.config import (
    CLAIMS_HARD_LIMIT,
    CLAIMS_SOFT_WARNING,
    Stage1Config,
)
from app.stage1.extract import extract_one_chunk
from app.stage1.hashing import (
    chunk_content_hash,
    params_fingerprint,
    signature_hash,
)
from app.stage1.repo import (
    get_workspace_id_for_document,
    Stage1CacheRepo,
    Stage1ChunkRunRepo,
    Stage1ClaimRepo,
    Stage1LlmCallRepo,
    Stage1RunRepo,
)
from app.stage1.schema import Stage1ExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    run_id: str
    status: str
    stats: dict[str, Any] = field(default_factory=dict)
    error_summary: str | None = None


def _persist_claims_and_evidence(
    session: Session,
    run_id: str,
    chunk_id: str,
    chunk_extraction_id: str,
    result: Stage1ExtractionResult,
    claim_repo: Stage1ClaimRepo,
    claims_hard_limit: int,
) -> tuple[int, bool]:
    """Persist claims and evidence. Returns (count, success_with_warnings)."""
    claims = result.claims
    if len(claims) > claims_hard_limit:
        return 0, False  # Caller should not persist claims
    success_with_warnings = len(claims) > CLAIMS_SOFT_WARNING
    for c in claims:
        value_json = c.value.model_dump_json() if hasattr(c.value, "model_dump_json") else json.dumps(c.value)
        claim = claim_repo.create_claim(
            session,
            run_id=run_id,
            chunk_id=chunk_id,
            chunk_extraction_id=chunk_extraction_id,
            claim_type=c.type,
            value_json=value_json,
            epistemic_tag=c.epistemic_tag,
            confidence=c.confidence,
            rule_id=c.rule_id,
        )
        for ev in c.evidence:
            char_start = ev.chunk_ref.char_start if ev.chunk_ref else None
            char_end = ev.chunk_ref.char_end if ev.chunk_ref else None
            claim_repo.create_evidence(
                session,
                claim_id=claim.id,
                chunk_id=chunk_id,
                snippet_text=ev.snippet,
                char_start=char_start,
                char_end=char_end,
            )
    return len(claims), success_with_warnings


def run_stage1_extract(
    document_id: str,
    config: Stage1Config,
    *,
    chunk_ids: list[str] | None = None,
    pending_only: bool = False,
) -> RunResult:
    """
    Run Stage 1 extraction for one document. One run = one document.
    If chunk_ids is set, process only those chunks (must belong to document).
    If pending_only is True, skip chunks that already have a successful cache for current signature.
    """
    run_repo = Stage1RunRepo()
    chunk_run_repo = Stage1ChunkRunRepo()
    cache_repo = Stage1CacheRepo()
    llm_repo = Stage1LlmCallRepo()
    claim_repo = Stage1ClaimRepo()
    chunk_repo = ChunkRepo()

    with session_scope() as session:
        workspace_id = get_workspace_id_for_document(session, document_id)
        if not workspace_id:
            return RunResult(
                run_id="",
                status="FAILED",
                error_summary="Document not found or workspace could not be resolved",
            )
        # Build signature for this run (no force_nonce unless --force)
        config_dict = config.model_dump()
        params_fp = params_fingerprint(config.temperature, config.max_tokens)
        if config.force_nonce:
            params_fp = params_fp + "|" + config.force_nonce
        run = run_repo.create(
            session,
            workspace_id=workspace_id,
            document_id=document_id,
            config=config_dict,
            prompt_version=config.prompt_version,
            extractor_version=config.extractor_version,
            model_id=config.model_id,
        )
        run_id = run.id
        # Chunk list
        all_chunks = chunk_repo.list_by_document(session, document_id)
        if chunk_ids:
            doc_chunk_ids = {c[0] for c in all_chunks}
            to_process = [(cid, next((t for i, t, _ in all_chunks if i == cid), "")) for cid in chunk_ids if cid in doc_chunk_ids]
        else:
            to_process = [(c[0], c[1] or "") for c in all_chunks]
        if pending_only:
            to_process = [
                (cid, text)
                for cid, text in to_process
                if not cache_repo.get_successful(
                    session, cid,
                    signature_hash(chunk_content_hash(text), config.prompt_version, config.extractor_version, config.model_id, params_fp, config.force_nonce),
                )
            ]
        chunk_run_repo.bulk_ensure(session, run_id, [c[0] for c in to_process])
        session.commit()

    # Stats
    chunks_total = len(to_process)
    chunks_cached = 0
    chunks_success = 0
    chunks_failed = 0
    claims_total = 0
    token_usage: dict[str, int] = {}

    for cid, text in to_process:
        content_hash = chunk_content_hash(text)
        sig_hash = signature_hash(
            content_hash,
            config.prompt_version,
            config.extractor_version,
            config.model_id,
            params_fp,
            config.force_nonce,
        )
        with session_scope() as session:
            cached = cache_repo.get_successful(session, cid, sig_hash)
            if cached:
                chunk_run_repo.mark_cached(session, run_id, cid, cached.id)
                session.commit()
                chunks_cached += 1
                from app.db.models.claim import Claim
                from sqlalchemy import select
                existing = session.execute(select(Claim).where(Claim.chunk_extraction_id == cached.id)).scalars().all()
                claims_total += len(existing)
                continue
        # Extract (async call from sync context)
        result, raw_text, error, usage = asyncio.run(
            extract_one_chunk(
                cid,
                text,
                config.model_id,
                config.temperature,
                config.max_tokens,
                repair_attempts=config.repair_attempts,
                repair_raw_max_chars=config.repair_raw_max_chars,
                timeout_s=config.timeout_s,
            )
        )
        with session_scope() as session:
            if result is None:
                chunk_run_repo.mark_failed(session, run_id, cid, error_message=error)
                llm_repo.create(
                    session,
                    run_id=run_id,
                    chunk_id=cid,
                    signature_hash=sig_hash,
                    request_json=json.dumps({"chunk_id": cid}),
                    response_text=raw_text,
                    status="FAILED",
                    error_message=error,
                )
                session.commit()
                chunks_failed += 1
                continue
            if len(result.claims) > config.claims_hard_limit:
                chunk_run_repo.mark_failed(
                    session,
                    run_id,
                    cid,
                    error_type="FAILED_TOO_MANY_CLAIMS",
                    error_message=f"Claims count {len(result.claims)} exceeds hard limit {config.claims_hard_limit}",
                )
                llm_repo.create(
                    session,
                    run_id=run_id,
                    chunk_id=cid,
                    signature_hash=sig_hash,
                    response_text=raw_text,
                    status="FAILED",
                    error_message="Too many claims",
                )
                session.commit()
                chunks_failed += 1
                continue
            llm_call = llm_repo.create(
                session,
                run_id=run_id,
                chunk_id=cid,
                signature_hash=sig_hash,
                request_json=json.dumps({"chunk_id": cid}),
                response_text=raw_text,
                response_json=result.model_dump_json(),
                status="SUCCESS",
                latency_ms=usage.get("latency_ms") if usage else None,
                prompt_tokens=usage.get("prompt_tokens") if usage else None,
                completion_tokens=usage.get("completion_tokens") if usage else None,
            )
            ext = cache_repo.insert(
                session,
                chunk_id=cid,
                run_id=run_id,
                signature_hash=sig_hash,
                chunk_content_hash=content_hash,
                prompt_version=config.prompt_version,
                extractor_version=config.extractor_version,
                model_id=config.model_id,
                produced_run_id=run_id,
                llm_call_id=llm_call.id,
                raw_text=raw_text,
                parsed_json=result.model_dump_json(),
                usage_json=json.dumps(usage) if usage else None,
            )
            n_claims, success_with_warnings = _persist_claims_and_evidence(
                session,
                run_id,
                cid,
                ext.id,
                result,
                claim_repo,
                config.claims_hard_limit,
            )
            claims_total += n_claims
            chunk_run_repo.mark_success(
                session,
                run_id,
                cid,
                ext.id,
                success_with_warnings=success_with_warnings,
                latency_ms=llm_call.latency_ms,
            )
            if usage and isinstance(usage, dict):
                token_usage["prompt_tokens"] = token_usage.get("prompt_tokens", 0) + usage.get("prompt_tokens", 0)
                token_usage["completion_tokens"] = token_usage.get("completion_tokens", 0) + usage.get("completion_tokens", 0)
            session.commit()
            chunks_success += 1

    # Embedding: when config.embed_claims is True, a separate embed_missing_claims job
    # (by run_id or by claims where embedding_status != EMBEDDED) can embed and upsert to Qdrant.
    # Claims are stored with embedding_status=PENDING.

    # Finalize run
    status = "SUCCESS" if chunks_failed == 0 else "PARTIAL"
    if chunks_total == 0:
        status = "SUCCESS"
    stats = {
        "chunks_total": chunks_total,
        "chunks_cached": chunks_cached,
        "chunks_success": chunks_success,
        "chunks_failed": chunks_failed,
        "claims_total": claims_total,
        "token_usage": token_usage,
    }
    with session_scope() as session:
        run_repo.finalize(session, run_id, status, stats)
        session.commit()

    return RunResult(run_id=run_id, status=status, stats=stats)
