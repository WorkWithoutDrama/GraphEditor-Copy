# 02 — Stage‑2 Data Model Expectations (Non-binding)

This doc describes the **roles** Stage‑2 needs. Your codebase may name tables differently; map accordingly.

## Inputs Stage‑2 expects

### From SQL
- `claims` ledger entries with:
  - `claim_id`, `claim_type` (ACTOR|OBJECT|ACTION|STATE|DENY)
  - `value_json` shape per Stage‑1 v4
  - `review_status` in {UNREVIEWED, ACCEPTED, REJECTED, SUPERSEDED}
  - `superseded_by` nullable FK to `claims.claim_id`
  - `dedupe_key` precomputed
  - bookkeeping: doc_id, chunk_id, run_id, prompt_version, extractor_version, embedding_model_id

- `claim_evidence`:
  - one or more evidence snippets per claim, linked to a chunk

- `chunks`:
  - chunk text for minimal local context (optionally truncated for prompts)

### From Qdrant
- `stage1_cards` collection: 1 point per claim with payload including:
  - `claim_id`, `claim_type`, `dedupe_key`, `card_text`, `evidence_snippet`
  - optional fast fields (ACTION actor/verb/object; ACTOR/OBJECT name)

## Stage‑2 outputs

### Required: canonicalization fields on `claims`
Stage‑2 updates only:
- `review_status`
- `superseded_by`

Optionally also store:
- `value_json.stage2` sub-object with extra metadata (aliases, normalized label, notes)

### Required: decision audit trail (recommended)
A minimal `stage2_decisions` (or reuse `llm_calls` + link) storing:
- `pass_kind` (ACTOR|OBJECT|STATE|ACTION)
- `seed_claim_id`
- `decision_json` (parsed model output)
- `evidence_refs`
- model/prompt identifiers + timestamps

### Optional: conflict groups
If you support “do not merge, ambiguous”:
- `stage2_conflict_groups(group_id, group_kind, notes, created_at)`
- `stage2_conflict_members(group_id, claim_id, role)`

### Optional: action bindings (helpful for Stage‑3)
To avoid repeatedly resolving actor/object chains:
- `stage2_action_bindings(action_claim_id, actor_claim_id, object_claim_id)`
where `actor_claim_id` and `object_claim_id` are canonical IDs.
