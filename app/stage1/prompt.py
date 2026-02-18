# # # """Stage 1 extraction and repair prompts."""
# # # from __future__ import annotations

# # # SYSTEM_MESSAGE = """You must output valid JSON matching the schema.
# # # Use only the chunk text; do not assume anything outside it.
# # # If uncertain, omit the claim.
# # # Every claim must include at least one evidence snippet (short quote from the chunk).
# # # Allowed epistemic tags: EXPLICIT, IMPLICIT, MODEL_INFERRED. Do not use RULE_INFERRED.
# # # Output only the JSON object, no markdown or explanation."""

# # # USER_TEMPLATE = """Chunk ID: {chunk_id}
# # # ---
# # # {chunk_text}"""

# # # REPAIR_SYSTEM = """You are a JSON repair assistant. The previous extraction output is invalid or incomplete.
# # # Output only the corrected JSON object that conforms to the schema. No markdown, no explanation."""

# # # REPAIR_USER_TEMPLATE = """The raw extraction output (possibly truncated) was:

# # # ---
# # # {raw_output}
# # # ---

# # # Schema requirements:
# # # - Top-level: prompt_version, chunk_id, summary, claims, optional warnings.
# # # - Each claim: type (ACTOR|OBJECT|STATE|ACTION|DENY|NOTE), epistemic_tag (EXPLICIT|IMPLICIT|MODEL_INFERRED), value (object), evidence (non-empty list).
# # # - Each evidence: snippet (string, max 300 chars), optional chunk_ref.
# # # Output only the valid JSON object."""


# # # def build_extraction_messages(chunk_id: str, chunk_text: str) -> list[dict[str, str]]:
# # #     """Build [system, user] messages for extraction."""
# # #     return [
# # #         {"role": "system", "content": SYSTEM_MESSAGE},
# # #         {"role": "user", "content": USER_TEMPLATE.format(chunk_id=chunk_id, chunk_text=chunk_text or "")},
# # #     ]


# # # def build_repair_messages(
# # #     raw_output: str,
# # #     head_chars: int = 2000,
# # #     tail_chars: int = 10000,
# # # ) -> list[dict[str, str]]:
# # #     """Build repair prompt; truncate raw to head + tail (addressed doc §2.3)."""
# # #     total_max = head_chars + tail_chars
# # #     if len(raw_output) <= total_max:
# # #         snippet = raw_output
# # #         truncated = False
# # #     else:
# # #         head = raw_output[:head_chars]
# # #         tail = raw_output[-tail_chars:]
# # #         snippet = head + "\n\n... [truncated] ...\n\n" + tail
# # #         truncated = True
# # #     note = " (Output was truncated for repair.)" if truncated else ""
# # #     return [
# # #         {"role": "system", "content": REPAIR_SYSTEM + note},
# # #         {"role": "user", "content": REPAIR_USER_TEMPLATE.format(raw_output=snippet)},
# # #     ]



# # """Stage 1 extraction and repair prompts (v2)."""

# # from __future__ import annotations

# # PROMPT_VERSION = "chunk_claims_extract_v2"

# # SYSTEM_MESSAGE = f"""
# # You are a strict business-logic extraction engine.

# # HARD RULES:
# # - Output ONLY a single valid JSON object. No markdown. No commentary.
# # - Use ONLY the provided chunk text. Do NOT assume anything outside it.
# # - Prefer omitting a claim over guessing. If you guess, tag MODEL_INFERRED with low confidence.
# # - Allowed epistemic_tag values: EXPLICIT, IMPLICIT, MODEL_INFERRED. Do NOT use RULE_INFERRED.
# # - Every claim MUST include >=1 evidence snippet (a short DIRECT QUOTE from the chunk, <=300 chars).
# # - Do NOT output NOTE claims in v2. (Type NOTE is reserved; do not use it.)
# # - Deduplicate within the chunk: do not output the same actor/object/state/action twice.

# # TOP-LEVEL JSON SHAPE (MUST MATCH):
# # {{
# #   "prompt_version": "{PROMPT_VERSION}",
# #   "chunk_id": "<must equal the provided Chunk ID>",
# #   "summary": "<1-2 sentences about business meaning of the chunk (not UI steps)>",
# #   "claims": [ ... ],
# #   "warnings": [ ... ]   // optional; strings
# # }}

# # EVIDENCE SHAPE:
# # Each evidence item:
# # {{
# #   "snippet": "<direct quote from chunk, <=300 chars>",
# #   "chunk_ref": {{
# #     "chunk_id": "<same as top-level chunk_id>",
# #     "char_start": <int or null>,
# #     "char_end": <int or null>
# #   }}
# # }}
# # - char_start/char_end: if you can locate the snippet in the chunk text, provide offsets; else null.

# # CLAIM SHAPE (MUST MATCH):
# # Each claim:
# # {{
# #   "type": "ACTOR" | "OBJECT" | "STATE" | "ACTION" | "DENY",
# #   "epistemic_tag": "EXPLICIT" | "IMPLICIT" | "MODEL_INFERRED",
# #   "confidence": <float 0..1 or null>,
# #   "value": {{ ... type-specific ... }},
# #   "evidence": [ <Evidence>, ... ]
# # }}

# # TYPE-SPECIFIC VALUE SHAPES:

# # 1) ACTOR
# # "value": {{
# #   "name": "<Role/System name, TitleCase if possible>",
# #   "kind": "role" | "system" | "external" | "unknown",
# #   "description": "<optional short description or null>"
# # }}

# # 2) OBJECT
# # "value": {{
# #   "name": "<Business object type name, singular TitleCase>",
# #   "description": "<optional short description or null>"
# # }}

# # 3) STATE
# # "value": {{
# #   "object_name": "<must match an OBJECT name used in this chunk>",
# #   "state": "<UPPER_SNAKE_CASE label>",
# #   "description": "<optional short description or null>"
# # }}

# # 4) ACTION  (AtomicAction claim; single target object)
# # "value": {{
# #   "name": "<business verb phrase, e.g. 'Sign document'>",
# #   "goal": "<business intent, e.g. 'Finalize document approval'>",
# #   "actors_allowed": ["<ActorName>", ...],
# #   "target_object": "<ObjectName>",
# #   "allowed_states": ["<STATE>", ...],   // list may be empty if truly not stated
# #   "effect": {{ "transition_to": "<STATE>" }} | {{ "no_change": true }},
# #   "place": "<optional business location or null>",
# #   "metadata_refs": {{
# #     "ui": {{ "steps": [..], "selectors": [..] }},
# #     "api": {{ "endpoints": [..], "methods": [..] }}
# #   }} | null
# # }}

# # 5) DENY
# # "value": {{
# #   "actor": "<ActorName>",
# #   "action_name": "<Action name, must match an ACTION.name if present>",
# #   "reason": "<optional reason or null>"
# # }}

# # NAMING / NORMALIZATION RULES (IMPORTANT FOR STABILITY):
# # - Object/Actor names: prefer singular nouns; TitleCase (e.g., "Document", "Admin", "User").
# # - State labels: UPPER_SNAKE_CASE (e.g., "EXISTS", "NONEXISTENT", "SIGNED", "UNSIGNED", "PUBLISHED").
# # - Action name: Verb + object (e.g., "Publish document"). Keep short and business-level.

# # HOW TO EXTRACT STATE GATING + EFFECTS (THIS FIXES 'MISSING V-INFO'):
# # When the chunk describes conditions like:
# # - "if <object> exists" -> create STATE(object, EXISTS) and include "EXISTS" in allowed_states
# # - "if <object> does not exist" / "missing" -> create STATE(object, NONEXISTENT) (EXPLICIT/IMPLICIT depending on wording)
# # - "not signed" -> create STATE(object, UNSIGNED) and include "UNSIGNED" in allowed_states
# # - "already signed" -> create STATE(object, SIGNED) and (if action is allowed only when not signed) use allowed_states including UNSIGNED (not a negative list)

# # When the chunk describes an action result like:
# # - "becomes signed" / "is signed" -> effect transition_to SIGNED
# # - "becomes published" -> transition_to PUBLISHED
# # - "view/list/read" with no stated change -> effect no_change true

# # If the chunk says an actor can perform an action but DOES NOT state the effect:
# # - Only emit the ACTION if you can infer the effect directly from wording (IMPLICIT) with confidence <= 0.6.
# # - Otherwise, omit the ACTION and add a warning string explaining what is missing.

# # COMPLETENESS RULE:
# # - If you emit an ACTION that references an actor/object/state not yet introduced in claims, ALSO emit the needed ACTOR/OBJECT/STATE claims (once) if the chunk contains evidence.

# # OUTPUT ORDER (for rerun stability):
# # - Sort claims by type in this order: ACTOR, OBJECT, STATE, ACTION, DENY
# # - Within each type, sort by name fields (alphabetical) if possible.
# # """.strip()

# # USER_TEMPLATE = """Prompt version: {prompt_version}
# # Chunk ID: {chunk_id}
# # Chunk text:
# # ---
# # {chunk_text}
# # ---
# # Reminder: output ONLY the JSON object, and set prompt_version and chunk_id exactly as provided.
# # """

# # REPAIR_SYSTEM = f"""
# # You are a strict JSON repair assistant.
# # Output ONLY a corrected JSON object that conforms to the SAME schema and rules as extraction v2.
# # - Do NOT add NOTE claims.
# # - Ensure prompt_version = "{PROMPT_VERSION}".
# # - Ensure every claim has evidence with snippet <=300 chars.
# # No markdown. No explanations.
# # """.strip()

# # REPAIR_USER_TEMPLATE = """The raw extraction output (possibly truncated) was:

# # ---
# # {raw_output}
# # ---

# # Repair goals:
# # 1) Produce valid JSON only
# # 2) Ensure required keys exist (prompt_version, chunk_id, summary, claims)
# # 3) Ensure claim objects conform to v2 shapes (ACTOR/OBJECT/STATE/ACTION/DENY)
# # 4) Ensure evidence exists for every claim
# # Return ONLY the corrected JSON object.
# # """


# # def build_extraction_messages(chunk_id: str, chunk_text: str) -> list[dict[str, str]]:
# #     return [
# #         {"role": "system", "content": SYSTEM_MESSAGE},
# #         {
# #             "role": "user",
# #             "content": USER_TEMPLATE.format(
# #                 prompt_version=PROMPT_VERSION,
# #                 chunk_id=chunk_id,
# #                 chunk_text=chunk_text or "",
# #             ),
# #         },
# #     ]


# # def build_repair_messages(
# #     raw_output: str,
# #     head_chars: int = 2000,
# #     tail_chars: int = 10000,
# # ) -> list[dict[str, str]]:
# #     total_max = head_chars + tail_chars
# #     if len(raw_output) <= total_max:
# #         snippet = raw_output
# #         truncated = False
# #     else:
# #         head = raw_output[:head_chars]
# #         tail = raw_output[-tail_chars:]
# #         snippet = head + "\n\n... [truncated] ...\n\n" + tail
# #         truncated = True
# #     note = " (Output was truncated for repair.)" if truncated else ""
# #     return [
# #         {"role": "system", "content": REPAIR_SYSTEM + note},
# #         {"role": "user", "content": REPAIR_USER_TEMPLATE.format(raw_output=snippet)},
# #     ]


# """Stage 1 extraction and repair prompts (v2.1)."""
# from __future__ import annotations

# PROMPT_VERSION = "chunk_claims_extract_v2_1"

# SYSTEM_MESSAGE = f"""
# You are a strict business-logic extraction engine.

# HARD RULES:
# - Output ONLY a single valid JSON object. No markdown. No commentary.
# - Use ONLY the provided chunk text. Do NOT assume anything outside it.
# - If the chunk contains no extractable business logic, output: claims: [] and explain briefly in summary.
# - Prefer omitting a claim over guessing.
# - Allowed epistemic tags: EXPLICIT, IMPLICIT, MODEL_INFERRED. Do NOT use RULE_INFERRED.
# - MODEL_INFERRED is ONLY allowed for ACTION claims in v2.1, and MUST include value.rationale (short).
# - Every claim MUST include >=1 evidence snippet: a short DIRECT QUOTE from the chunk (<=300 chars).
# - Deduplicate within the chunk: do not emit the same actor/object/state/action twice.

# TOP-LEVEL JSON SHAPE (MUST MATCH):
# {{
#   "prompt_version": "{PROMPT_VERSION}",
#   "chunk_id": "<must equal the provided Chunk ID>",
#   "summary": "<1-2 sentences about business meaning of the chunk (not UI steps)>",
#   "claims": [ ... ],
#   "warnings": [ ... ]   // optional; strings
# }}

# EVIDENCE SHAPE:
# Each evidence item:
# {{
#   "snippet": "<direct quote from chunk, <=300 chars>",
#   "chunk_ref": {{
#     "chunk_id": "<same as top-level chunk_id>",
#     "char_start": <int or null>,
#     "char_end": <int or null>
#   }}
# }}
# - If you cannot locate offsets reliably, set char_start/char_end to null (still include chunk_id).

# CLAIM SHAPE:
# Each claim:
# {{
#   "type": "ACTOR" | "OBJECT" | "STATE" | "ACTION" | "DENY",
#   "epistemic_tag": "EXPLICIT" | "IMPLICIT" | "MODEL_INFERRED",
#   "confidence": <float 0..1 or null>,
#   "value": {{ ... type-specific ... }},
#   "evidence": [ <Evidence>, ... ]
# }}

# TYPE-SPECIFIC VALUE SHAPES (MUST MATCH):

# 1) ACTOR
# "value": {{
#   "name": "<Role/System name, TitleCase if possible>",
#   "kind": "role" | "system" | "external" | "unknown",
#   "description": "<optional short description or null>"
# }}

# 2) OBJECT
# "value": {{
#   "name": "<Business object type name, singular TitleCase>",
#   "description": "<optional short description or null>"
# }}

# 3) STATE
# IMPORTANT: Schema expects ONLY object_name and state. Do NOT add other keys.
# "value": {{
#   "object_name": "<must match an OBJECT name used in this chunk>",
#   "state": "<UPPER_SNAKE_CASE label>"
# }}

# 4) ACTION (AtomicAction claim; single target object)
# "value": {{
#   "name": "<business verb phrase, e.g. 'Sign document'>",
#   "goal": "<business intent>",
#   "actors_allowed": ["<ActorName>", ...],
#   "target_object": "<ObjectName>",
#   "allowed_states": ["<STATE>", ...],   // may be empty only if truly not stated
#   "effect": {{ "transition_to": "<STATE>" }} | {{ "no_change": true }},
#   "place": "<optional business location or null>",
#   "metadata_refs": {{
#     "ui": {{ "steps": [..], "selectors": [..] }},
#     "api": {{ "endpoints": [..], "methods": [..] }}
#   }} | null,
#   "rationale": "<required ONLY if epistemic_tag == MODEL_INFERRED>"
# }}

# ACTION EFFECT RULE:
# - EXACTLY ONE of:
#   - effect.transition_to
#   - effect.no_change == true
# must be present. Never output both and never output neither.

# 5) DENY
# "value": {{
#   "actor": "<ActorName>",
#   "action_name": "<Action name; if an ACTION claim exists, match its name>",
#   "reason": "<optional reason or null>"
# }}

# NORMALIZATION RULES (for stable outputs):
# - Actor/Object names: singular, TitleCase (e.g., "Document", "Admin", "User").
# - State labels: UPPER_SNAKE_CASE (e.g., EXISTS, NONEXISTENT, SIGNED, UNSIGNED, PUBLISHED).
# - Action name: Verb + object (e.g., "Publish document"). Keep business-level.

# STATE GATING + EFFECT EXTRACTION RULES:
# - "if <object> exists" -> create STATE(object, EXISTS) and include EXISTS in allowed_states.
# - "does not exist"/"missing" -> STATE(object, NONEXISTENT) and include NONEXISTENT in allowed_states only if explicitly required.
# - "not signed"/"unsigned" -> STATE(object, UNSIGNED) and include UNSIGNED in allowed_states.
# - "already signed" -> STATE(object, SIGNED) (use allowed_states UNSIGNED if action requires not signed).
# - Result wording:
#   - "becomes signed"/"is signed" -> effect.transition_to SIGNED
#   - "becomes published" -> transition_to PUBLISHED
#   - "view/list/read" with no change stated -> effect.no_change true

# COMPLETENESS RULE:
# - If an ACTION references an actor/object/state not yet introduced in claims, ALSO emit the needed ACTOR/OBJECT/STATE claims (once) if the chunk contains evidence.

# OUTPUT ORDER (for rerun stability):
# - Sort claims by type in this order: ACTOR, OBJECT, STATE, ACTION, DENY.
# - Within each type, sort alphabetically by the main name field where possible.

# FINAL CHECKLIST BEFORE OUTPUT:
# - Valid JSON only
# - prompt_version and chunk_id set correctly
# - every claim has evidence snippet(s)
# - no NOTE, no RULE_INFERRED
# - STATE value has only object_name + state
# - MODEL_INFERRED only on ACTION and has value.rationale
# """.strip()

# USER_TEMPLATE = """Prompt version: {prompt_version}
# Chunk ID: {chunk_id}
# Chunk text:
# ---
# {chunk_text}
# ---
# Reminder: output ONLY the JSON object, with prompt_version and chunk_id exactly as provided.
# """

# REPAIR_SYSTEM = f"""
# You are a strict JSON repair assistant.
# Output ONLY a corrected JSON object that conforms to extraction prompt v2.1 rules.
# No markdown. No explanations.
# Key constraints:
# - prompt_version must be "{PROMPT_VERSION}"
# - MODEL_INFERRED only allowed on ACTION and must include value.rationale
# - STATE value must contain only object_name and state
# - every claim must have evidence with snippet <=300 chars
# """.strip()

# REPAIR_USER_TEMPLATE = """The raw extraction output (possibly truncated) was:

# ---
# {raw_output}
# ---

# Repair goals:
# 1) Produce valid JSON only
# 2) Ensure required keys exist (prompt_version, chunk_id, summary, claims)
# 3) Ensure claim objects conform exactly to v2.1 value shapes (ACTOR/OBJECT/STATE/ACTION/DENY)
# 4) Ensure every claim has evidence
# Return ONLY the corrected JSON object.
# """


# def build_extraction_messages(chunk_id: str, chunk_text: str) -> list[dict[str, str]]:
#     return [
#         {"role": "system", "content": SYSTEM_MESSAGE},
#         {
#             "role": "user",
#             "content": USER_TEMPLATE.format(
#                 prompt_version=PROMPT_VERSION,
#                 chunk_id=chunk_id,
#                 chunk_text=chunk_text or "",
#             ),
#         },
#     ]


# def build_repair_messages(
#     raw_output: str,
#     head_chars: int = 2000,
#     tail_chars: int = 10000,
# ) -> list[dict[str, str]]:
#     total_max = head_chars + tail_chars
#     if len(raw_output) <= total_max:
#         snippet = raw_output
#         truncated = False
#     else:
#         head = raw_output[:head_chars]
#         tail = raw_output[-tail_chars:]
#         snippet = head + "\n\n... [truncated] ...\n\n" + tail
#         truncated = True
#     note = " (Output was truncated for repair.)" if truncated else ""
#     return [
#         {"role": "system", "content": REPAIR_SYSTEM + note},
#         {"role": "user", "content": REPAIR_USER_TEMPLATE.format(raw_output=snippet)},
#     ]
PROMPT_VERSION = "chunk_claims_extract_v3_explicit_only"

SYSTEM_MESSAGE = f"""
You are a strict business-logic extractor for Stage 1 (chunk-only).

HARD RULES:
- Output ONLY one valid JSON object. No markdown. No explanations.
- Use ONLY the provided chunk text. Do NOT assume anything outside it.
- Stage 1 is EXPLICIT-ONLY:
  - epistemic_tag MUST be "EXPLICIT" for every claim.
  - Do NOT use IMPLICIT, MODEL_INFERRED, or RULE_INFERRED.
- Evidence MUST be a verbatim quote copied from the chunk text (<=300 chars).
- If the chunk has no extractable business logic, output claims: [] and explain in summary.
- IMPORTANT: This chunk is often structured as bullet points. You must cover them.

OUTPUT JSON SHAPE:
{{
  "prompt_version": "{PROMPT_VERSION}",
  "chunk_id": "<must equal provided chunk_id>",
  "summary": "<1-2 sentences about business logic in this chunk>",
  "claims": [ ... ],
  "warnings": [ ... ]   // optional list of strings
}}

CLAIM SHAPE:
Each claim:
{{
  "type": "ACTOR" | "OBJECT" | "STATE" | "ACTION" | "DENY",
  "epistemic_tag": "EXPLICIT",
  "confidence": null,
  "value": <OBJECT — see type-specific shapes below; NEVER a string>,
  "evidence": [ {{ "snippet": "...", "chunk_ref": {{ "chunk_id": "...", "char_start": null, "char_end": null }} }} ]
}}

CRITICAL — value is ALWAYS an object (dict), NEVER a plain string.
Match the exact shape below for each claim type.

TYPE-SPECIFIC VALUE SHAPES (use these exactly):

1) ACTOR — value must be:
   {{ "name": "<role/system name>", "kind": "role" | "system" | "external" | "unknown" | null, "description": "<optional or null>" }}
   Example: {{ "name": "Система", "kind": "system", "description": null }}

2) OBJECT — value must be:
   {{ "name": "<business object type, singular>", "description": "<optional or null>" }}
   Example: {{ "name": "Проект", "description": null }}

3) STATE — value must be:
   {{ "object_name": "<must match an OBJECT name in this chunk>", "state": "<state label>" }}
   Example: {{ "object_name": "Задача", "state": "Новая" }}

4) ACTION — value must be:
   {{ "name": "<verb phrase>", "goal": "<intent or null>", "actors_allowed": ["<ActorName>"], "target_object": "<ObjectName>", "allowed_states": [], "effect": {{ "transition_to": "<STATE>" }} | {{ "no_change": true }} | null, "place": null, "metadata_refs": null }}

5) DENY — value must be:
   {{ "actor": "<ActorName>", "action_name": "<Action name>", "reason": "<optional or null>" }}

WHAT TO EXTRACT (MINIMUM EXPECTATION):
1) ACTOR:
- Extract roles/agents explicitly mentioned (e.g., "Исполнитель", "Менеджер", "Система", "Пользователь").
- Put the name inside value.name; value must be the object above, not the string.

2) OBJECT:
- Extract business objects explicitly mentioned (e.g., "задача", "проект", "комментарий").
- Put the object type in value.name; use singular form. value must be the object above, not the string.

3) ACTION (AtomicAction claim; single target object):
- For EACH bullet line that describes behavior, emit one ACTION.
- ACTION.value must be the object shape above (name, goal, actors_allowed, target_object, allowed_states, effect, place, metadata_refs).

4) STATE:
- Emit STATE ONLY if the chunk explicitly lists concrete state labels (e.g., "Новая", "В работе", "Готово").
- value must be {{ "object_name": "...", "state": "..." }}, not a bare string like "Новая".
- If it only says "изменение статуса" without listing values: DO NOT emit STATE.

BULLET COVERAGE RULE:
- If the chunk contains bullet lines (starting with "-" or similar), you must produce an ACTION for each bullet line.
- If you cannot, add a warning: "Uncovered bullet: <quote of bullet>".

OUTPUT ORDER:
- ACTOR, OBJECT, STATE, ACTION, DENY
""".strip()

USER_TEMPLATE = """prompt_version: {prompt_version}
chunk_id: {chunk_id}

CHUNK TEXT:
---
{chunk_text}
---
Return ONLY the JSON object, with prompt_version and chunk_id exactly as provided.
"""

REPAIR_SYSTEM = f"""
You are a strict JSON repair assistant.
Return ONLY a corrected JSON object that conforms to Stage 1 v3 rules:
- prompt_version must be "{PROMPT_VERSION}"
- epistemic_tag must be EXPLICIT for all claims
- evidence snippets must be verbatim quotes from the chunk (<=300 chars)
- do not invent STATE transitions; ACTION.effect may be {{}} if not explicit
- CRITICAL: claim "value" must ALWAYS be an object, never a string. If you see "value": "Система" or "value": "проект" or "value": "Новая", convert to the correct shape:
  - ACTOR: value = {{ "name": "<that string>", "kind": null, "description": null }}
  - OBJECT: value = {{ "name": "<that string>", "description": null }}
  - STATE: value = {{ "object_name": "<object from context>", "state": "<that string>" }}
No markdown. No explanations.
""".strip()

REPAIR_USER_TEMPLATE = """Invalid output to repair:

---
{raw_output}
---

Repair it into a valid JSON object. Ensure every claim's "value" is an object (not a string): ACTOR/OBJECT/STATE/ACTION/DENY each have a specific value shape (see schema). Return ONLY the JSON object.
"""

def build_extraction_messages(chunk_id: str, chunk_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": USER_TEMPLATE.format(
            prompt_version=PROMPT_VERSION,
            chunk_id=chunk_id,
            chunk_text=chunk_text or "",
        )},
    ]
    
def build_repair_messages(
    raw_output: str,
    head_chars: int = 2000,
    tail_chars: int = 10000,
) -> list[dict[str, str]]:
    total_max = head_chars + tail_chars
    if len(raw_output) <= total_max:
        snippet = raw_output
        truncated = False
    else:
        head = raw_output[:head_chars]
        tail = raw_output[-tail_chars:]
        snippet = head + "\n\n... [truncated] ...\n\n" + tail
        truncated = True
    note = " (Output was truncated for repair.)" if truncated else ""
    return [
        {"role": "system", "content": REPAIR_SYSTEM + note},
        {"role": "user", "content": REPAIR_USER_TEMPLATE.format(raw_output=snippet)},
    ]