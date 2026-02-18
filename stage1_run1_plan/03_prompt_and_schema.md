# Stage 1 Prompt Pack v1 + Output Schema

## Goals of the prompt
- Extract **atomic claims** from a single chunk only
- Ground each claim with evidence
- Be conservative: do not invent missing business logic
- Output strict JSON that validates

---

## Epistemic tags (Stage 1 allowed set)
Stage 1 should use:

- `EXPLICIT`: directly stated
- `IMPLICIT`: strongly implied by the chunk (still needs evidence snippet)
- `MODEL_INFERRED`: allowed only when unavoidable; must include rationale + low confidence
- `RULE_INFERRED`: generally avoid in Stage 1 unless you explicitly implement deterministic rules inside Stage 1 (optional). If used, include `rule_id`.

**Strong rule:** If unsure, omit the claim.

---

## Claim types (v1 minimal)
### ACTOR
Value fields:
- `name`
- `kind` = `role|system|external` (best guess; if unsure, omit `kind` or set `unknown`)
- `description` (optional)

### OBJECT
Value fields:
- `name`
- `description` (optional)

### STATE
Value fields:
- `object_name` (string)
- `state` (string)

### ACTION (AtomicAction claim)
Value fields (minimal, business-first):
- `name` (business verb phrase)
- `goal` (business intent)
- `actors_allowed` (list of actor names)
- `target_object` (single object name)
- `allowed_states` (list of states of target object; may be empty if not specified)
- `effect`:
  - either `{ "transition_to": "STATE" }` or `{ "no_change": true }`
- `place` (optional string or null)
- `metadata_refs` (optional object: ui/api details if present)

### DENY
Value fields:
- `actor` (string)
- `action_name` (string)
- `reason` (optional string)

---

## Strict JSON schema (Pydantic)
Implement a Pydantic model `Stage1ExtractionResult` and validate the LLM output.

Recommended top-level structure:
- `prompt_version`: string (e.g., "chunk_claims_extract_v1")
- `chunk_id`: string (uuid)
- `summary`: string (1–2 sentences)
- `claims`: list[Claim]
- `warnings`: list[str] (optional)

Each `Claim`:
- `type`: one of ACTOR|OBJECT|STATE|ACTION|DENY|NOTE
- `epistemic_tag`: EXPLICIT|IMPLICIT|RULE_INFERRED|MODEL_INFERRED
- `confidence`: optional float (only for IMPLICIT/MODEL_INFERRED)
- `rule_id`: optional string
- `value`: typed per claim type
- `evidence`: list[Evidence] (must be non-empty unless RULE_INFERRED)

Each `Evidence`:
- `snippet`: string (short; <= ~300 chars)
- `chunk_ref`: includes chunk_id (and optional offsets)

---

## Prompt template (conceptual)
System message (core constraints):
- "You must output valid JSON matching the schema."
- "Use only the chunk text; do not assume anything outside it."
- "If uncertain, omit the claim."
- "Every claim must include evidence snippet(s)."

User message payload:
- chunk metadata (doc title/section optional)
- chunk text

---

## Repair strategy (required)
LLMs sometimes return:
- non-JSON text
- JSON with trailing commas
- schema mismatches
- missing evidence

Implement a two-step repair flow:
1) Try to parse and validate. If fails:
2) Call LLM with a **repair prompt**:
   - Provide the raw output
   - Provide schema
   - Ask to output corrected JSON only
3) If still fails:
   - mark extraction FAILED
   - persist raw response + error info
