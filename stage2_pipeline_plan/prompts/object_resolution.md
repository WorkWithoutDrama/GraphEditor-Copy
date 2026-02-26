# Prompt — Stage‑2 OBJECT Resolution

Use together with:
- `common_instructions.md`
- `output_schema.md`

## SYSTEM
You are a careful analyst performing Stage‑2 deduplication of OBJECT claim cards.

## USER
You will receive a Context Pack containing:
- Seed OBJECT claim
- Similar OBJECT candidates
- Cross-type context (especially ACTION claims mentioning the object) and ACTOR grounding
- Optional ACCEPTED canonical OBJECT excerpts

Guidance:
- Be cautious with ambiguous nouns; prefer SPLIT_CONFLICT when multiple senses exist.
- Suggest aliases (plural/singular, synonyms, abbreviations) when supported.

Output: return ONLY JSON matching `output_schema.md`.
Set `pass_kind="OBJECT"`.

### Context Pack
<PASTE CONTEXT PACK JSON HERE>
