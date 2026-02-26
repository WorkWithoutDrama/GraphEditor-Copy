# Prompt — Stage‑2 ACTOR Resolution

Use together with:
- `common_instructions.md`
- `output_schema.md`

## SYSTEM
You are a careful analyst performing Stage‑2 deduplication of ACTOR claim cards.

## USER
You will receive a Context Pack as text blocks. Each block has:
- type (e.g. ACTOR, OBJECT)
- value fields for that type (e.g. name for ACTOR)
- evidence: list of snippets
- chunk excerpt (text around the first evidence)

The pack contains:
- Seed ACTOR claim (one block)
- Optionally: **Closest canonical** (one block, same type, already accepted)—if present, it is the one most similar canonical you can merge into.
- Same-type neighbors: similar ACTOR candidates
- Cross-type: a few ACTION/OBJECT/STATE claims

When **Closest canonical** is present: decide either **ACCEPT_AS_CANONICAL** (seed is a new, distinct canonical; context suggests it is not a hallucination) or **MERGE_INTO** (seed is a duplicate of that canonical). For MERGE_INTO, set `decision.canonical_claim_id` to the **canonical_claim_id** shown in that block.
When **Closest canonical** is absent: do not use MERGE_INTO; choose among ACCEPT_AS_CANONICAL, REJECT, DEFER, SPLIT_CONFLICT.

Task: decide whether the seed ACTOR is canonical, a duplicate, unsupported, needs deferral, or should be placed into a conflict group.

Output: return ONLY JSON matching `output_schema.md`.
Set `pass_kind="ACTOR"`.
Cite evidence by **snippet** only (exact quote from the context); do not fabricate IDs.

### Context Pack
<CONTEXT PACK>
