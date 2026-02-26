# Common Stage‑2 LLM Instructions (applies to all prompts)

You are performing **Stage‑2 normalization/deduplication** over Stage‑1 claim cards.
Stage‑1 claims are explicit-only and chunk-local; Stage‑2 must not invent new facts.

## Hard rules
1) Use only provided evidence (snippets / chunk excerpts). Do not infer unstated relationships.
2) If evidence is insufficient, choose DEFER or SPLIT_CONFLICT rather than forcing a merge.
3) Output valid JSON matching `output_schema.md`.
4) MERGE_INTO is only valid when a **Closest canonical** block is present in the context; then set `decision.canonical_claim_id` to the `canonical_claim_id` shown in that block.
5) Every decision must cite at least one evidence_ref that exists in the context pack.

## Rejecting hallucinations
REJECT only when the claim is not supported by provided evidence.

## Language
Return canonical labels and aliases in the document language.
