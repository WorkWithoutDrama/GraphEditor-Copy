# 08 — Pass 4: ACTION Resolution

## Goal
Canonicalize ACTION mention claims and bind them to canonical ACTOR/OBJECT IDs.

## Prompt
- `prompts/action_resolution.md`
- Shared rules: `prompts/common_instructions.md`
- Output schema: `prompts/output_schema.md`

## Endpoint binding
If canonical ACTOR/OBJECT IDs are known for the action endpoints, store them as Stage‑2 annotations
(link table or `value_json.stage2`). This helps Stage‑3 composition.

## Procedure
1) Pick seed ACTION claim
2) Resolve actor/object canonicals via superseded_by chains
3) Build context pack (ACTION neighbors + related ACTOR/OBJECT + any explicit STATE)
4) Call LLM, validate, apply + audit

## Merging caution
- Do not collapse distinct business actions prematurely.
- Use conflict groups when uncertain.
