# Stage‑2 Decision Output (JSON)

Output a **single JSON object**. The system adds `seed_claim_id` and resolves evidence IDs from your snippets; you never output those.

**Required from you:**
- **pass_kind** — `"ACTOR"` | `"OBJECT"` | `"STATE"` | `"ACTION"` (match the current pass).
- **decision.kind** — `"ACCEPT_AS_CANONICAL"` | `"MERGE_INTO"` | `"REJECT"` | `"DEFER"` | `"SPLIT_CONFLICT"`.
- **decision.confidence** — number 0.0–1.0.
- **decision.rationale** — short explanation why decision was made.
- **decision.evidence_refs** — array of `{ "snippet": "exact quote from context" }`. No IDs; we resolve them.

**IF decision.kind is:**
- **MERGE_INTO** — only when a **Closest canonical** block is present: set `decision.canonical_claim_id` to the **canonical_claim_id** shown in that block. If that block is not in the context, do not use MERGE_INTO.
- **ACCEPT_AS_CANONICAL** / **MERGE_INTO** — optionally set `normalization.canonical_label`, `normalization.aliases`, `normalization.notes`.

**IF pass_kind is:**
- **ACTION** pass — optionally set `attachments.action_endpoints.actor_claim_id` and `object_claim_id` when you can link to ACTOR/OBJECT claims.

**IF provided context conflicts each other:**
- **SPLIT_CONFLICT** — set `conflict.members` (each: `claim_id`, `role`, `reason`); leave `canonical_claim_id` null.

**JSON schema**
{
  "pass_kind": "<pass_kind>",
  "decision": {
    "kind": "<decision.kind>",
    "canonical_claim_id": <canonical claim id only if MERGE_INTO, else null>,
    "confidence": "<decision.confidence>",
    "rationale": "<decision.rationale>",
    "evidence_refs": "<decision.evidence_refs>"
  },
  "normalization": { "canonical_label": "<self label if ACCEPT_AS_CANONICAL, canonical claim label if MERGE_INTO>", "aliases" [<list of aliases, if present in context>]: , "notes": <short note of normalisation> },
  "attachments": {
    "object_claim_ids": [],
    "actor_claim_ids": [],
    "action_endpoints": { "actor_claim_id": <claim id of actor if action can be linked to it ONLY if pass_kind is action>, "object_claim_id": <claim id of object if action can be linked to it ONLY if pass_kind is action> }
  },
  "conflict": { "group_label": null, "members": [] }
}

Omit or null optional fields when not needed. The parser accepts this shape and the system fills `seed_claim_id` and evidence ref IDs.
