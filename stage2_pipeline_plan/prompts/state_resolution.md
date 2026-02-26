# Prompt — Stage‑2 STATE Resolution

Use together with:
- `common_instructions.md`
- `output_schema.md`

## SYSTEM
You are a careful analyst performing Stage‑2 deduplication of explicit STATE claim cards.

## USER
You will receive a Context Pack containing:
- Seed STATE claim
- Similar STATE candidates
- Candidate owning OBJECT claims
- Nearby ACTION/ACTOR context (small)

Task:
1) Canonicalize the state label (merge duplicates).
2) Attach the canonical state to one or more canonical OBJECT claims as candidate state labels (if supported).
   Use `attachments.object_claim_ids`.

Constraints:
- Do not invent NONEXISTENT or default states.
- Do not infer transitions; Stage‑3 composes transitions.

Output: return ONLY JSON matching `output_schema.md`.
Set `pass_kind="STATE"`.

### Context Pack
<PASTE CONTEXT PACK JSON HERE>
