# Prompt — Stage‑2 OBJECT Resolution

Use together with:
- `common_instructions.md`
- `output_schema.md`

## SYSTEM
You are a careful analyst performing Stage‑2 deduplication of OBJECT claim cards.

## USER
You will receive a Context Pack as text blocks. Each block has:
- type (e.g. ACTOR, OBJECT)
- value fields for that type (e.g. name for OBJECT)
- evidence: list of snippets
- chunk excerpt (text around the first evidence)

The pack contains:
- Seed OBJECT claim (one block)
- Optionally: **Closest canonical** (one block, same type, already accepted)—if present, it is the one most similar canonical you can merge into.
- Same-type neighbors: similar OBJECT candidates
- Cross-type context (especially ACTION claims mentioning the object) and ACTOR grounding

When **Closest canonical** is present: decide either **ACCEPT_AS_CANONICAL** (seed is a new, distinct canonical) or **MERGE_INTO** (seed is a duplicate of that canonical). For MERGE_INTO, set `decision.canonical_claim_id` to the **canonical_claim_id** shown in that block.
When **Closest canonical** is absent: do not use MERGE_INTO; choose among ACCEPT_AS_CANONICAL, REJECT, DEFER, SPLIT_CONFLICT.

Guidance:
- Be cautious with ambiguous nouns; prefer SPLIT_CONFLICT when multiple senses exist.
- Suggest aliases (plural/singular, synonyms, abbreviations) when supported.

Output: return ONLY JSON matching `output_schema.md`.
Set `pass_kind="OBJECT"`.
Cite evidence by **snippet** only (exact quote from the context); do not fabricate IDs.

### Context Pack
<CONTEXT PACK>
