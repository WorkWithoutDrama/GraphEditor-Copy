"""Stage 2 decision applier: apply parsed decision to claims (review_status, superseded_by, value_json.stage2)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.claim import Claim
from app.stage1.repo import Stage1ClaimRepo
from app.stage2.schema import Stage2DecisionOutput


def apply_decision(
    session: Session,
    decision: Stage2DecisionOutput,
    *,
    claim_repo: Stage1ClaimRepo | None = None,
) -> None:
    """
    Apply one Stage-2 decision to claims. Call within a transaction.

    - ACCEPT_AS_CANONICAL: seed -> ACCEPTED; optional value_json.stage2 from normalization.
    - MERGE_INTO: seed -> SUPERSEDED, superseded_by_id=canonical_claim_id; canonical -> ACCEPTED if not already.
    - REJECT: seed -> REJECTED.
    - DEFER: no change (leave UNREVIEWED).
    - SPLIT_CONFLICT: no change for MVP (optional conflict groups deferred).
    """
    repo = claim_repo or Stage1ClaimRepo()
    seed_id = decision.seed_claim_id
    kind = decision.decision.kind
    canonical_id = decision.decision.canonical_claim_id

    if kind == "DEFER" or kind == "SPLIT_CONFLICT":
        return

    if kind == "REJECT":
        repo.update_review_status(session, seed_id, "REJECTED", superseded_by_id=None)
        return

    if kind == "ACCEPT_AS_CANONICAL":
        repo.update_review_status(session, seed_id, "ACCEPTED", superseded_by_id=None)
        _merge_stage2_normalization(repo, session, seed_id, decision)
        if decision.pass_kind == "ACTION":
            _merge_action_endpoints(repo, session, seed_id, decision)
        return

    if kind == "MERGE_INTO":
        if not canonical_id:
            return
        # Canonical must exist
        canonical = session.get(Claim, canonical_id)
        if not canonical:
            return
        repo.update_review_status(session, seed_id, "SUPERSEDED", superseded_by_id=canonical_id)
        repo.update_review_status(session, canonical_id, "ACCEPTED", superseded_by_id=None)
        _merge_stage2_normalization(repo, session, canonical_id, decision)
        if decision.pass_kind == "ACTION":
            _merge_action_endpoints(repo, session, canonical_id, decision)
        return


def _merge_stage2_normalization(
    repo: Stage1ClaimRepo,
    session: Session,
    claim_id: str,
    decision: Stage2DecisionOutput,
) -> None:
    """Merge normalization (canonical_label, aliases, notes) into value_json.stage2."""
    norm = decision.normalization
    stage2: dict = {}
    if norm.canonical_label is not None:
        stage2["canonical_label"] = norm.canonical_label
    if norm.aliases:
        stage2["aliases"] = norm.aliases
    if norm.notes is not None:
        stage2["notes"] = norm.notes
    if not stage2:
        return
    repo.merge_value_json_stage2(session, claim_id, stage2)


def _merge_action_endpoints(
    repo: Stage1ClaimRepo,
    session: Session,
    claim_id: str,
    decision: Stage2DecisionOutput,
) -> None:
    """Resolve actor/object claim IDs to canonical and store in value_json.stage2.action_endpoints."""
    ep = decision.attachments.action_endpoints
    actor_id = ep.actor_claim_id
    object_id = ep.object_claim_id
    if actor_id:
        actor_id = repo.resolve_canonical_claim_id(session, actor_id) or actor_id
    if object_id:
        object_id = repo.resolve_canonical_claim_id(session, object_id) or object_id
    stage2: dict = {"action_endpoints": {"actor_claim_id": actor_id, "object_claim_id": object_id}}
    repo.merge_value_json_stage2(session, claim_id, stage2)
