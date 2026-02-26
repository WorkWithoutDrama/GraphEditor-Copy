# 06 — Pass 2: OBJECT Resolution

## Goal
Deduplicate OBJECT claims and produce stable object IDs for later state/action binding.

## Prompt
- `prompts/object_resolution.md`
- Shared rules: `prompts/common_instructions.md`
- Output schema: `prompts/output_schema.md`

## Key guidance
- Use ACTION evidence to disambiguate object senses.
- Prefer conflict groups over wrong merges for ambiguous nouns.

## Procedure
1) Pick seed OBJECT claim
2) Build context pack (OBJECT neighbors + supporting ACTION/ACTOR context)
3) Call LLM, validate, apply + audit
