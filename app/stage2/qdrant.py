"""Stage 2 Qdrant helper: retrieve seed vector, search similar, unique by dedupe_key."""
from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient, models as qdrant_models

from app.vectorstore.client import build_qdrant_client
from app.vectorstore.collections import ensure_stage1_cards_collection


@dataclass(frozen=True)
class SimilarClaimHit:
    """One claim from similarity search after dedupe_key collapse."""
    claim_id: str
    score: float
    dedupe_key: str | None
    payload: dict


async def search_similar_claims(
    seed_claim_id: str,
    doc_id: str,
    pass_kind: str,
    *,
    collection_name: str = "stage1_cards",
    vector_size: int = 768,
    same_type_limit: int = 15,
    same_type_only: bool = False,
    client: AsyncQdrantClient | None = None,
) -> list[SimilarClaimHit]:
    """
    Retrieve seed claim vector from stage1_cards, search top-K similar, dedupe by dedupe_key.

    - same_type_only: if True, filter by claim_type == pass_kind (ACTOR/OBJECT/STATE/ACTION).
    - Returns at most same_type_limit results after keeping best score per dedupe_key, excluding seed.
    """
    c = client or build_qdrant_client()
    await ensure_stage1_cards_collection(c, collection_name, vector_size, "Cosine")

    # Retrieve seed point to get its vector (point id = claim_id in stage1_cards)
    try:
        records = await c.retrieve(
            collection_name=collection_name,
            ids=[seed_claim_id],
            with_vectors=True,
            with_payload=False,
        )
    except Exception:
        return []

    if not records or not records[0].vector:
        return []

    query_vector = records[0].vector
    if isinstance(query_vector, dict):
        # Named vectors: use default key
        query_vector = list(query_vector.values())[0] if query_vector else []
    query_vector = list(query_vector)

    if not query_vector:
        return []

    # Build filter: scope to same document (stage1_cards payload uses "doc_id"); exclude seed
    must: list[qdrant_models.Condition] = [
        qdrant_models.FieldCondition(
            key="doc_id",
            match=qdrant_models.MatchValue(value=doc_id),
        ),
    ]
    if same_type_only:
        must.append(
            qdrant_models.FieldCondition(
                key="claim_type",
                match=qdrant_models.MatchValue(value=pass_kind),
            ),
        )
    query_filter = qdrant_models.Filter(
        must=must,
        must_not=[qdrant_models.HasIdCondition(has_id=[seed_claim_id])],
    )

    limit = min(100, same_type_limit * 3)  # fetch extra for dedupe
    response = await c.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

    points = response.points or []
    # Dedupe by dedupe_key: keep best score per key
    by_key: dict[str, SimilarClaimHit] = {}
    for p in points:
        pid = str(p.id) if p.id is not None else ""
        if pid == seed_claim_id:
            continue
        payload = dict(p.payload or {})
        dk = payload.get("dedupe_key") or ""
        score = float(p.score or 0.0)
        hit = SimilarClaimHit(claim_id=pid, score=score, dedupe_key=dk or None, payload=payload)
        if dk:
            if dk not in by_key or by_key[dk].score < score:
                by_key[dk] = hit
        else:
            by_key[pid] = hit  # no key: use claim_id as key so we keep one

    # Sort by score descending, take same_type_limit
    ordered = sorted(by_key.values(), key=lambda h: -h.score)
    return ordered[:same_type_limit]
