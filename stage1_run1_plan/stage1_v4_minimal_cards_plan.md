# Stage 1 v4 — Minimal “Card” Extraction (Explicit-Only) — Implementation Plan

This plan updates **Stage 1 (Run‑1)** so it produces **high-recall, low-hallucination “cards”** for Qdrant retrieval by extracting **minimal, explicitly grounded mentions** (actors / objects / action mentions), and postponing heavy modeling (states, transitions, permissions) to later stages.

The goal is to reduce LLM struggle and eliminate invented fields (e.g., bogus states/effects), while improving coverage for bullet-list requirements documents.

---

## 1) Target outcome

### What Stage 1 v4 should do
Given a chunk:
- Extract **only what is explicitly present**.
- Produce small claim cards that are:
  - **verbatim evidence-backed** (evidence snippets are exact substrings),
  - **one bullet → one action mention** (when bullets exist),
  - minimal fields (easy to validate, easy to embed),
  - stable across reruns.

### What Stage 1 v4 should NOT do
- No inference (no IMPLICIT / MODEL_INFERRED).
- No action state transitions or allowed states unless **explicitly listed as labels**.
- No DENY unless explicit negation exists (“нельзя/запрещено/не может/не допускается”).
- No “goal”, “place”, UI/API selectors, etc. (those belong to later stages).

---

## 2) Prompt changes (v4)

### 2.1 New prompt version
- Set `PROMPT_VERSION = "chunk_claims_extract_v4_minimal_explicit"`.

### 2.2 Core prompt rules (must be stated clearly)
**System message rules**
1) **JSON only**. No markdown.
2) **Explicit-only**:
   - `epistemic_tag` MUST be `"EXPLICIT"` for every claim.
   - Disallow: `IMPLICIT`, `MODEL_INFERRED`, `RULE_INFERRED`.
3) **Evidence must be verbatim** substring from the chunk (`<= 300 chars`).
4) **Bullets coverage**:
   - If chunk has bullet lines (e.g., starting with `-`), emit **exactly one ACTION claim per bullet**.
5) **No invented objects**:
   - Do not mention nouns not present in chunk (prevents “задача/комментарий” leakage).
6) **STATE and DENY are rare**:
   - `STATE` only if state labels are explicitly listed (e.g., “Новая / В работе / Завершена”).
   - `DENY` only if explicit negation exists.

**User message**
- Provide: `chunk_id` and raw `chunk_text`.
- No extra context, no retrieved claims.

### 2.3 Minimal claim shapes (what the prompt must enforce)

Top-level JSON:
```json
{
  "prompt_version": "chunk_claims_extract_v4_minimal_explicit",
  "chunk_id": "<exact>",
  "summary": "<1-2 sentences, business-only>",
  "claims": [...],
  "warnings": []  // optional
}
```

Evidence:
```json
{
  "snippet": "<verbatim quote <=300 chars>",
  "chunk_ref": {"chunk_id": "<same>", "char_start": null, "char_end": null}
}
```

Claims (v4 minimal):
- ACTOR: only `name`
- OBJECT: only `name`
- ACTION (ActionMention): `actor`, `verb`, `object`, optional `qualifiers`
- STATE (optional): only `object_name`, `state`
- DENY (optional): `actor`, `action_verb`, `object`, optional `reason`

**Recommended ACTION value shape**:
```json
{
  "actor": "Пользователь",
  "verb": "удаляет",
  "object": "Проект",
  "qualifiers": ["завершенный"]
}
```

### 2.4 Action naming conventions in v4
- Keep all names in the chunk’s language (RU) to maximize substring grounding.
- Actor/Object names: TitleCase (first letter uppercase), singular (“Проект”, “Пользователь”, “Система”).
- Verb: keep as it appears in bullet (e.g., “удаляет”, “архивирует”, “сохраняет”).

### 2.5 Prompt file changes (repo tasks)
- Replace the current minimal `prompt.py` with a versioned prompt pack (or add a new module):
  - `app/prompts/stage1_v4.py` (recommended)
- Keep old prompts if you need reproducibility; otherwise, overwrite and bump version.
- Ensure Stage 1 orchestrator references v4 prompt by default.

---

## 3) Pydantic model changes (JSON validation)

### 3.1 Add a new schema model for v4 (do NOT mutate old v2/v3 models)
Implement separate models keyed by `prompt_version`, so old runs remain parseable if needed:

**Registry pattern**
- `Stage1ParserRegistry.get(prompt_version) -> (PydanticModel, post_validators)`
- Example:
  - `chunk_claims_extract_v3_explicit_only` → `Stage1ResultV3`
  - `chunk_claims_extract_v4_minimal_explicit` → `Stage1ResultV4`

This avoids “schema vs prompt mismatches” across versions.

### 3.2 V4 Pydantic models (strict, minimal, extra-forbid)

**Top-level**
- `prompt_version: Literal["chunk_claims_extract_v4_minimal_explicit"]`
- `chunk_id: UUID | str`
- `summary: str`
- `claims: list[ClaimV4]`
- `warnings: list[str] = []`

**Evidence**
- `snippet: constr(min_length=1, max_length=300)`
- `chunk_ref: ChunkRefV4`
- `ChunkRefV4`: `chunk_id: str`, `char_start: int|None = None`, `char_end: int|None = None`

**Claim union**
- `ClaimV4 = ActorClaimV4 | ObjectClaimV4 | ActionClaimV4 | StateClaimV4 | DenyClaimV4`

**ActorValueV4**
- `name: str`
- No `kind`, no `description`.

**ObjectValueV4**
- `name: str`
- No `description`.

**ActionMentionValueV4**
- `actor: str`
- `verb: str`
- `object: str`
- `qualifiers: list[str] = []`

**StateValueV4 (optional usage)**
- `object_name: str`
- `state: str`

**DenyValueV4 (optional usage)**
- `actor: str`
- `verb: str`
- `object: str`
- `reason: str|None = None`

**Strictness**
- Set `model_config = ConfigDict(extra="forbid")` (Pydantic v2) on all models.
- Force `epistemic_tag = Literal["EXPLICIT"]` and `confidence = None`.

### 3.3 “Schema vs prompt” safety rules (validators)
Implement Pydantic validators that catch common failure modes early:
- Disallow empty strings in names/verbs.
- Normalize whitespace (strip) but do not rewrite tokens.
- Enforce evidence list non-empty for every claim.

---

## 4) New post-parse validators (critical correctness gates)

Pydantic validates JSON shape, but Stage 1 needs **semantic validation** using the chunk text.

### 4.1 Evidence substring validator (hard fail)
After parsing JSON:
- For each `evidence.snippet`:
  - normalize newlines in both chunk_text and snippet (replace `\r\n`→`\n`)
  - assert `snippet in chunk_text`
- If any snippet is not a substring:
  - trigger repair once, else mark extraction FAILED (do not persist partial claims)
This prevents the “задача/комментарий” leakage and typo paraphrases.

### 4.2 Bullet coverage validator (soft fail → warnings; configurable)
If chunk contains bullet lines:
- Extract bullet lines with a simple regex:
  - `^\s*-\s+.+$` (multiline)
- For each bullet line:
  - require **at least one ACTION claim evidence snippet** equals that bullet line (or is a substring of it)
- If uncovered bullet exists:
  - either:
    - **Option A (recommended):** mark chunk_run `SUCCESS_WITH_WARNINGS` and store warnings
    - Option B: fail extraction (stricter)
Start with Option A to avoid blocking ingestion.

### 4.3 “No invented nouns” validator (optional, pragmatic)
Because v4 is explicit-only, you can add a lightweight check:
- For each extracted Actor/Object name:
  - ensure at least one evidence snippet contains that exact name (case-sensitive or case-insensitive)
This catches “Проект” extracted with evidence “задача”.

---

## 5) Orchestrator changes (Stage 1 pipeline code)

### 5.1 Prompt selection and signature hashing
- Update Stage 1 config default prompt_version to v4.
- Signature hash must include prompt_version → all v4 runs naturally bypass old cache.
- Keep extractor_version bump (recommended).

### 5.2 Persisted claim format in SQL
Your `claims.value_json` is already flexible JSON; keep schema unchanged.
- `claim_type` remains: ACTOR / OBJECT / ACTION / STATE / DENY
- `value_json` shape changes for ACTION in v4 (ActionMention fields).

**Important:** ensure downstream code that expects old ACTION fields (`allowed_states`, `effect`) does not run on v4 claims. Use prompt_version gating.

### 5.3 Qdrant “card” text generation update
For v4, embed short canonical strings:

- ACTOR: `ACTOR | <name>`
- OBJECT: `OBJECT | <name>`
- ACTION: `ACTION | <actor> | <verb> | <object> | <qualifiers_joined>`
- STATE (if any): `STATE | <object_name> | <state>`
- DENY (if any): `DENY | <actor> | <verb> | <object>`

Store payload filters:
- `prompt_version`, `extractor_version`, `model_id`
- `doc_id`, `chunk_id`, `run_id`, `claim_type`

### 5.4 Remove/disable Stage‑1 “effect/state gating” logic
If your current code tries to enforce:
- “effect must be transition/no_change”
- “allowed_states must be present”
Disable for v4. Those belong to Stage 3.

---

## 6) Repair prompt changes

For v4, the repair prompt should repeat the minimal shapes (because v4 is strict and small):
- “epistemic_tag must be EXPLICIT”
- “ACTION value must have actor/verb/object”
- “Evidence snippets must be verbatim substrings”

Also: keep the existing truncation strategy (head+tail) for raw output.

---

## 7) Tests and evaluation updates

### 7.1 Unit tests
1) **Evidence substring gate**
- snippet not in chunk → repair attempted → still fail → extraction FAILED

2) **Bullet coverage**
- given 3 bullets → expect 3 ACTION claims; else warnings emitted (Option A)

3) **Schema strictness**
- extra keys in STATE value → reject
- ACTION missing verb → reject

### 7.2 Golden chunk test (use your sample)
Input chunk:
```
3.1.3 Удаление проекта
- Пользователь удаляет завершенный проект
- Пользователь архивирует проект
- Система сохраняет историю проекта
```
Expected (schema-normalized assertions):
- ACTOR names include: Пользователь, Система
- OBJECT names include: Проект
- ACTION count == 3 (one per bullet)
- No STATE and no DENY claims
- Every evidence snippet is a substring of chunk

### 7.3 Metrics to track after deployment
- avg ACTIONs per chunk
- % chunks with uncovered bullets
- % repair calls
- % failed due to non-substring evidence
- claim counts per type

---

## 8) Step-by-step implementation checklist (agent-ready)

### Step A — Add v4 prompt
- [ ] Create `app/prompts/stage1_v4.py`
- [ ] Implement `PROMPT_VERSION = chunk_claims_extract_v4_minimal_explicit`
- [ ] Implement `SYSTEM_MESSAGE`, `USER_TEMPLATE`, `REPAIR_SYSTEM`, `REPAIR_USER_TEMPLATE`
- [ ] Ensure v4 prompt explicitly enforces: EXPLICIT-only, bullet coverage, no state unless listed, no deny unless negation.

### Step B — Add v4 Pydantic models
- [ ] Create `app/schemas/stage1_v4.py`
- [ ] Implement strict models with `extra="forbid"`
- [ ] Implement union claim parsing by `type`
- [ ] Add parser registry entry mapping v4 prompt_version → v4 model

### Step C — Add post-parse validators
- [ ] Implement `validate_evidence_substrings(result, chunk_text)` (hard fail)
- [ ] Implement `validate_bullet_coverage(result, chunk_text)` (warnings by default)
- [ ] (Optional) Implement `validate_name_backed_by_evidence(result)` (catches wrong evidence mapping)

### Step D — Update Stage 1 runner
- [ ] Default prompt_version to v4 in Stage1Config
- [ ] Route parsed results through v4 model + validators when prompt_version == v4
- [ ] Persist warnings to `chunk_runs` / `chunk_extractions` metadata (or `runs.stats_json`)
- [ ] Ensure caching signature includes prompt_version (already should)

### Step E — Update Qdrant indexing
- [ ] Update claim→embedding_text builder to support v4 shapes
- [ ] Keep payload fields for filtering
- [ ] Add a migration path for existing claim embeddings if needed (optional)

### Step F — Tests
- [ ] Add unit tests for schema + substring + bullet coverage
- [ ] Add one integration test that runs the full stage on the sample chunk and checks DB rows + embeddings (if test Qdrant is available)

---

## 9) Compatibility / rollout strategy

- Bump `prompt_version` and `extractor_version` → old cache won’t collide.
- Keep Stage 1 v4 separate; do not attempt to “reinterpret” old claims.
- Stage 2/3 can be updated later to accept v4 claims as input (they’ll actually be cleaner).

---

## 10) Definition of Done

Stage 1 v4 is complete when:
- It extracts **3 actions from 3 bullets** in the sample chunk (no invented states/effects/denies).
- Evidence snippets always pass substring validation.
- Qdrant has compact cards for actor/object/action mentions.
- Reruns hit cache (signature-based) and avoid repeated LLM calls.
