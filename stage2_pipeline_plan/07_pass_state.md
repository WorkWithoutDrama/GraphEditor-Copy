# 07 — Pass 3: STATE Resolution and Attachment

## Goal
Canonicalize explicit STATE claims and attach them to canonical OBJECT(s) as candidate state labels.

## Prompt
- `prompts/state_resolution.md`
- Shared rules: `prompts/common_instructions.md`
- Output schema: `prompts/output_schema.md`

## Constraints
- Do not invent NONEXISTENT; only work from explicit text.
- Do not infer transitions; Stage‑3 will do that.

## Procedure
1) Pick seed STATE claim
2) Build context pack (STATE neighbors + candidate owning OBJECTs + nearby ACTION/ACTOR context)
3) Call LLM, validate, apply:
   - canonicalize state label
   - attach to object canonicals if supported
4) Audit
