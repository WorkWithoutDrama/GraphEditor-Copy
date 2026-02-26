"""Stage 1 claim cards: index claims to Qdrant (stage1_cards collection)."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from qdrant_client import models as qdrant_models
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db.models.claim import Claim
from app.db.models.pipeline_run import PipelineRun
from app.db.session import session_scope
from app.embeddings.ollama import OllamaEmbedClient
from app.embeddings.settings import EmbedSettings
from app.stage1.cards import (
    build_card_text,
    build_dedupe_key,
    build_embedding_text,
    evidence_snippet_for_payload,
)
from app.stage1.config import STAGE1_EXTRACTOR_VERSION
from app.vectorstore.client import build_qdrant_client
from app.vectorstore.collections import ensure_stage1_cards_collection
from app.vectorstore.errors import VectorSchemaMismatchError

logger = logging.getLogger(__name__)

DEFAULT_EMBED_BATCH_SIZE = 32


@dataclass
class ClaimCardItem:
    """One claim prepared for embedding and upsert."""

    claim_id: str
    embedding_text: str
    card_text: str
    dedupe_key: str
    payload: dict[str, Any]
    claim: Claim


@dataclass
class IndexStats:
    """Result of index_stage1_claims_to_qdrant."""

    claims_total: int = 0
    claims_indexed: int = 0
    claims_failed: int = 0
    error_summary: str | None = None


def _get_first_snippet(claim: Claim) -> str:
    """First evidence snippet for a claim (loaded with claim.evidence)."""
    if not claim.evidence:
        return ""
    return (claim.evidence[0].snippet_text or "").strip()


def _parse_value(value_json: str) -> dict:
    """Parse value_json to dict. Return {} on error."""
    if not value_json:
        return {}
    try:
        return json.loads(value_json) if isinstance(value_json, str) else value_json
    except (json.JSONDecodeError, TypeError):
        return {}


def _apply_option_b(claims: list[Claim], doc_id: str) -> list[Claim]:
    """Option B: for ACTOR/OBJECT keep first per (chunk_id, dedupe_key); keep all ACTION/STATE/DENY."""
    seen: set[tuple[str, str]] = set()
    result: list[Claim] = []
    for c in claims:
        value = _parse_value(c.value_json)
        dk = build_dedupe_key(c.claim_type, value)
        if c.claim_type in ("ACTOR", "OBJECT"):
            key = (c.chunk_id, dk)
            if key in seen:
                continue
            seen.add(key)
        result.append(c)
    return result


def _build_payload(
    claim: Claim,
    doc_id: str,
    prompt_version: str,
    extractor_version: str,
    model_id: str,
    embedding_model_id: str,
    card_text: str,
    evidence_snippet: str,
    dedupe_key: str,
) -> dict[str, Any]:
    """Build Qdrant payload dict for a claim point."""
    value = _parse_value(claim.value_json)
    payload: dict[str, Any] = {
        "claim_id": claim.id,
        "doc_id": doc_id,
        "chunk_id": claim.chunk_id,
        "run_id": claim.run_id,
        "claim_type": claim.claim_type,
        "prompt_version": prompt_version,
        "extractor_version": extractor_version,
        "model_id": model_id,
        "embedding_model_id": embedding_model_id,
        "epistemic_tag": claim.epistemic_tag,
        "card_text": card_text,
        "evidence_snippet": evidence_snippet_for_payload(evidence_snippet),
        "dedupe_key": dedupe_key,
    }
    if claim.claim_type in ("ACTOR", "OBJECT"):
        payload["name"] = (value.get("name") or "").strip() or None
    if claim.claim_type == "ACTION":
        payload["actor"] = (value.get("actor") or "").strip() or None
        payload["verb"] = (value.get("verb") or "").strip() or None
        payload["object"] = (value.get("object") or "").strip() or None
    return {k: v for k, v in payload.items() if v is not None}


def _load_claims_with_evidence(session, run_id: str, only_pending: bool) -> list[Claim]:
    """Load claims for run with evidence eager-loaded."""
    q = (
        select(Claim)
        .where(Claim.run_id == run_id)
        .options(joinedload(Claim.evidence))
    )
    if only_pending:
        q = q.where(Claim.embedding_status != "EMBEDDED")
    rows = session.execute(q).unique().scalars().all()
    return list(rows)


async def _embed_and_upsert(
    items: list[ClaimCardItem],
    collection_name: str,
    vector_size: int,
    embed_client: OllamaEmbedClient,
    batch_size: int,
) -> tuple[list[str], list[tuple[str, str]]]:
    """
    Embed texts in batches and upsert to Qdrant. Returns (success_claim_ids, [(claim_id, error), ...]).
    """
    client = build_qdrant_client()
    await ensure_stage1_cards_collection(client, collection_name, vector_size, "Cosine")

    success_ids: list[str] = []
    failures: list[tuple[str, str]] = []

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        texts = [x.embedding_text for x in batch]
        try:
            vectors = await embed_client.embed_texts(texts)
        except Exception as e:
            err_msg = str(e)[:1000]
            for x in batch:
                failures.append((x.claim_id, err_msg))
            continue

        if len(vectors) != len(batch):
            err_msg = f"Embed returned {len(vectors)} vectors for {len(batch)} texts"
            for x in batch:
                failures.append((x.claim_id, err_msg))
            continue

        for j, vec in enumerate(vectors):
            if len(vec) != vector_size:
                err_msg = f"Vector dimension {len(vec)} != expected {vector_size}"
                failures.append((batch[j].claim_id, err_msg))
                continue

        points = [
            qdrant_models.PointStruct(
                id=item.claim_id,
                vector=vec,
                payload=item.payload,
            )
            for item, vec in zip(batch, vectors)
        ]
        try:
            await client.upsert(collection_name=collection_name, points=points)
            for item in batch:
                success_ids.append(item.claim_id)
        except Exception as e:
            err_msg = str(e)[:1000]
            for item in batch:
                failures.append((item.claim_id, err_msg))

    return success_ids, failures


def index_stage1_claims_to_qdrant(
    run_id: str,
    *,
    only_pending: bool = True,
    collection_name: str | None = None,
    embedding_model_id: str | None = None,
    vector_size: int | None = None,
    embed_batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
) -> IndexStats:
    """
    Load claims for the run, build card/embedding text, batch-embed, upsert to Qdrant, update SQL.

    When only_pending is True, only claims with embedding_status != EMBEDDED are processed.
    Option B: for ACTOR/OBJECT only the first per (chunk_id, dedupe_key) is indexed.
    """
    embed_settings = EmbedSettings()
    dims = vector_size if vector_size is not None else embed_settings.dims
    model_id = embedding_model_id or embed_settings.ollama_model
    coll_name = collection_name or "stage1_cards"

    stats = IndexStats()

    with session_scope() as session:
        run = session.get(PipelineRun, run_id)
        if not run:
            stats.error_summary = "Run not found"
            return stats

        doc_id = run.document_id
        prompt_version = run.prompt_name or "chunk_claims_extract_v4_minimal_explicit_v2"
        extractor_version = STAGE1_EXTRACTOR_VERSION
        try:
            cfg = json.loads(run.config_json or "{}")
            extractor_version = cfg.get("extractor_version") or extractor_version
        except Exception:
            pass
        run_model_id = run.llm_profile or ""

        claims = _load_claims_with_evidence(session, run_id, only_pending)
        stats.claims_total = len(claims)
        if not claims:
            return stats

        claims = _apply_option_b(claims, doc_id)
        items: list[ClaimCardItem] = []
        for c in claims:
            value = _parse_value(c.value_json)
            snippet = _get_first_snippet(c)
            card_text = build_card_text(c.claim_type, value)
            embedding_text = build_embedding_text(c.claim_type, value, snippet)
            dedupe_key = build_dedupe_key(c.claim_type, value)
            payload = _build_payload(
                c,
                doc_id,
                prompt_version,
                extractor_version,
                run_model_id,
                model_id,
                card_text,
                snippet,
                dedupe_key,
            )
            items.append(
                ClaimCardItem(
                    claim_id=c.id,
                    embedding_text=embedding_text,
                    card_text=card_text,
                    dedupe_key=dedupe_key,
                    payload=payload,
                    claim=c,
                )
            )

    if not items:
        return stats

    embed_client = OllamaEmbedClient()
    try:
        success_ids, failures = asyncio.run(
            _embed_and_upsert(
                items,
                coll_name,
                dims,
                embed_client,
                embed_batch_size,
            )
        )
    except VectorSchemaMismatchError as e:
        stats.error_summary = str(e)
        return stats
    except Exception as e:
        logger.exception("Qdrant/embed failed for run %s", run_id)
        stats.error_summary = str(e)
        return stats

    now = datetime.now(timezone.utc)
    success_set = set(success_ids)
    failure_map = {cid: err for cid, err in failures}

    with session_scope() as session:
        for item in items:
            claim = session.get(Claim, item.claim_id)
            if not claim:
                continue
            if item.claim_id in success_set:
                claim.embedding_status = "EMBEDDED"
                claim.embedded_at = now
                claim.embedding_model_id = model_id
                claim.qdrant_collection = coll_name
                claim.qdrant_point_id = item.claim_id
                claim.card_text = item.card_text
                claim.dedupe_key = item.dedupe_key
                claim.embedding_error = None
                stats.claims_indexed += 1
            elif item.claim_id in failure_map:
                claim.embedding_status = "FAILED"
                claim.embedding_error = (failure_map[item.claim_id] or "")[:1024]
                stats.claims_failed += 1

    return stats
