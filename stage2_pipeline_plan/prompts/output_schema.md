# Stage‑2 Decision Output Schema (JSON)

All prompts must output a single JSON object matching this logical schema.

```json
{
  "pass_kind": "ACTOR|OBJECT|STATE|ACTION",
  "seed_claim_id": "uuid",
  "decision": {
    "kind": "ACCEPT_AS_CANONICAL|MERGE_INTO|REJECT|DEFER|SPLIT_CONFLICT",
    "canonical_claim_id": "uuid|null",
    "confidence": 0.0,
    "rationale": "short text",
    "evidence_refs": [
      {
        "claim_id": "uuid",
        "evidence_id": "uuid|null",
        "chunk_id": "uuid|null",
        "snippet": "string|null"
      }
    ]
  },
  "normalization": {
    "canonical_label": "string|null",
    "aliases": ["string"],
    "notes": "string|null"
  },
  "attachments": {
    "object_claim_ids": ["uuid"],
    "actor_claim_ids": ["uuid"],
    "action_endpoints": {
      "actor_claim_id": "uuid|null",
      "object_claim_id": "uuid|null"
    }
  },
  "conflict": {
    "group_label": "string|null",
    "members": [
      { "claim_id": "uuid", "role": "seed|candidate|other", "reason": "string" }
    ]
  }
}
```

Notes:
- MERGE_INTO requires canonical_claim_id.
- SPLIT_CONFLICT should fill conflict.members and leave canonical_claim_id null.
- evidence_refs must reference provided context; do not fabricate IDs.
