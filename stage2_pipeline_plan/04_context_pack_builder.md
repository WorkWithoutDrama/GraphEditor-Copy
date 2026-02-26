# 04 — Context Pack Builder

Stage‑2 quality depends on consistent, bounded context.

## Retrieval workflow (must match the spec)
1) Qdrant vector search top‑K
2) unique by `dedupe_key` (keep best score per key)
3) fetch SQL claim + evidence using `claim_id` for prompt injection

## Type-balanced context pack (recommended)
For seed claim `S`:

**A) Seed block**
- claim_id, type, card_text, dedupe_key
- value_json
- 1–3 evidence snippets + chunk_ids
- optional chunk excerpt (short)

**B) Same-type neighbors**
- 6–10 candidates after dedupe_key collapse

**C) Cross-type support (inject all types safely)**
- For ACTOR: 2–4 ACTION + 1–3 OBJECT + 0–2 STATE
- For OBJECT: 2–4 ACTION + 1–3 ACTOR + 0–2 STATE
- For STATE: 1–3 OBJECT + 1–3 ACTION + 1–2 ACTOR
- For ACTION: 2–4 ACTOR/OBJECT + 0–2 STATE

**D) Optional accepted canonicals**
- small retrieval-based excerpt of ACCEPTED claims for grounding

## Token budgeting
- cap candidates per section
- truncate chunk excerpts
- prefer snippets over full chunks

## Output
`ContextPackBuilder.build(seed_claim_id, pass_kind) -> ContextPack` (serializable; can be stored in `llm_calls.request_json`).
