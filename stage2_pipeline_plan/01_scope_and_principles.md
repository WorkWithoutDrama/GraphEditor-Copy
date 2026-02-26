# 01 — Scope and Principles

## Stage separation (do not blur stages)
- **Stage‑1**: extract *explicit-only*, chunk-local **claim cards** with evidence snippets.
- **Stage‑2** (this module): cross-chunk **dedup + normalization** producing canonical IDs (via `superseded_by` chains) and optionally conflict groups.
- **Stage‑3**: compose canonical claims into domain objects: Objects+States, AtomicActions, BusinessOperations.

Stage‑2 must not invent new “truth”; it only **selects canonicals**, links duplicates, and records decisions.

## Authoritative stores
- **SQL** is authoritative for claims, evidence, review status, and decisions.
- **Qdrant** is retrieval-only: it helps find *similar* claims to compare.

## Canonical ID strategy (recommended)
Use **existing Stage‑1 claim IDs as canonical IDs**:
- One claim in a cluster becomes canonical: `review_status=ACCEPTED`
- Duplicates become `review_status=SUPERSEDED` and `superseded_by=<canonical_claim_id>`
- Rejected extraction artifacts become `review_status=REJECTED`
- If ambiguous, keep unmerged and store a **conflict group**

This avoids new “canonical tables” in MVP and matches the ledger approach.

## Required pass order rationale
The domain model has dependencies:
- **Actors**: referenced by Actions; stabilize early.
- **Objects**: referenced by Actions; object naming often depends on actor context.
- **States**: belong to Objects (finite enum set per object).
- **Actions**: depend on canonical Actors/Objects, and are later used to compose AtomicActions.

## Determinism & auditability
Every Stage‑2 decision must be reproducible:
- record the decision JSON (LLM output) + the evidence refs used
- keep raw Stage‑1 claims unchanged (only set review/supersede fields)
- never rely on Qdrant as truth; always re-fetch evidence from SQL for prompts.
