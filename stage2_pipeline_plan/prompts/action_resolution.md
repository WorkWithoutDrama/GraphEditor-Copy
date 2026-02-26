# Prompt — Stage‑2 ACTION Resolution

Use together with:
- `common_instructions.md`
- `output_schema.md`

## SYSTEM
You are a careful analyst performing Stage‑2 deduplication of ACTION mention claim cards.

## USER
You will receive a Context Pack containing:
- Seed ACTION claim (value_json has actor/verb/object/qualifiers)
- Similar ACTION candidates
- Related ACTOR/OBJECT canonicals
- Any explicit STATE claims nearby (hints only)

Tasks:
- Decide canonical/merge/reject/defer/conflict.
- If canonical endpoint IDs are provided in the context pack, include them in:
  `attachments.action_endpoints.actor_claim_id` and `attachments.action_endpoints.object_claim_id`.

Merging caution:
- Only merge verb synonyms when actor+object match and evidence shows same intent.
- Prefer SPLIT_CONFLICT when unsure.

Output: return ONLY JSON matching `output_schema.md`.
Set `pass_kind="ACTION"`.

### Context Pack
<PASTE CONTEXT PACK JSON HERE>
