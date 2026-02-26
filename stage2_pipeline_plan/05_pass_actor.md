# 05 — Pass 1: ACTOR Resolution

## Goal
Deduplicate and canonicalize ACTOR claims so later passes can reference stable actor IDs.

## Prompt
- `prompts/actor_resolution.md`
- Shared rules: `prompts/common_instructions.md`
- Output schema: `prompts/output_schema.md`

## Output
- Canonical ACTOR claims: `review_status=ACCEPTED`
- Duplicates: `review_status=SUPERSEDED` + `superseded_by=<canonical_claim_id>`
- Noise: `review_status=REJECTED`
- Optional alias suggestions stored under `value_json.stage2.aliases`

## Procedure
1) Pick seed ACTOR claim
2) Build context pack
3) Call LLM
4) Validate JSON output
5) Apply decision + audit
