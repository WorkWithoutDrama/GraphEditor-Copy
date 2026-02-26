# 09 — Storage Updates and Idempotency

Stage‑2 must be safely re-runnable.

## Canonical chain invariants
- SUPERSEDED claims must point to an existing claim_id
- follow superseded_by chains until terminal
- detect cycles as errors

## Transaction boundaries
- apply one seed decision in one SQL transaction:
  - updates to claims (review_status/superseded_by)
  - inserts to audit/conflicts/attachments

## Avoid exception-driven loops
Prefer on-conflict-no-op patterns for:
- audit rows (if idempotency keys used)
- conflict membership rows
- attachment/link tables

## Qdrant updates
Stage‑2 typically does not re-embed stage1_cards.
If you create an optional stage2_canon collection, upsert only ACCEPTED canonicals.
