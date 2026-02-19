"""Stage 1 v4 — minimal explicit-only extraction prompts (one ACTION per bullet, verbatim evidence)."""
from __future__ import annotations

PROMPT_VERSION = "chunk_claims_extract_v4_minimal_explicit"

SYSTEM_MESSAGE = f"""
You are a strict extractor. Output ONLY valid JSON. No markdown.

RULES:
1) JSON only. No markdown, no explanation.
2) EXPLICIT-ONLY: epistemic_tag MUST be "EXPLICIT" for every claim. Do NOT use IMPLICIT, MODEL_INFERRED, or RULE_INFERRED.
3) Every claim MUST have an "evidence" array with at least one item. Each item: verbatim substring from the chunk.
4) If the chunk has bullet lines, emit exactly one ACTION claim per bullet. Emit exactly one ACTION per bullet line when the chunk contains a bullet list.
5) STATE only if the chunk explicitly lists state labels (e.g. "Новая / В работе / Завершена"). DENY only if there is explicit negation ("нельзя", "запрещено", "не может", "не допускается").
6) Do not add any field not listed (no description, kind, or other extra keys in value objects).

EXAMPLE (one claim with evidence):
{{ "type": "ACTOR", "epistemic_tag": "EXPLICIT", "confidence": null, "value": {{ "name": "Система" }}, "evidence": [ {{ "snippet": "Система управления", "chunk_ref": {{ "chunk_id": "<chunk_id>"}} }} ] }}

TOP-LEVEL JSON:
{{
  "prompt_version": "{PROMPT_VERSION}",
  "chunk_id": "<exact chunk_id provided>",
  "claims": [ ... ],
  "warnings": [ ]
}}

EVIDENCE (each claim must have at least one):
{{ "snippet": "<verbatim quote from chunk>", "chunk_ref": {{ "chunk_id": "<same>" }} }}

CLAIM VALUE SHAPES (use exactly these):

ACTOR:   {{ "name": "<role/system name, TitleCase singular>" }}
OBJECT:  {{ "name": "<business object type, TitleCase singular>" }}
ACTION:  {{ "actor": "<ActorName>", "verb": "<as in bullet>", "object": "<ObjectName>", "qualifiers": ["<optional>"] }}
STATE:   {{ "object_name": "<ObjectName>", "state": "<state label>" }}   (only if states explicitly listed)
DENY:    {{ "actor": "<ActorName>", "verb": "<action verb>", "object": "<ObjectName>", "reason": "<optional or null>" }}

Each claim MUST have: "type", "epistemic_tag": "EXPLICIT", "confidence": null, "value": <object above>, "evidence": [ {{ "snippet": "<quote from chunk>", "chunk_ref": {{ "chunk_id": "<same>"}} }} ]  (at least one evidence per claim)

NAMING: Keep names in chunk language (e.g. RU). TitleCase singular: "Проект", "Пользователь", "Система". Verb as in bullet: "удаляет", "архивирует", "сохраняет".

OUTPUT ORDER: ACTOR, OBJECT, STATE, ACTION, DENY.
""".strip()

USER_TEMPLATE = """chunk_id: {chunk_id}

CHUNK TEXT:
---
{chunk_text}
---

Output ONLY the JSON object. Set prompt_version to "{prompt_version}" and chunk_id to the value above.
"""

REPAIR_SYSTEM = f"""
You are a JSON repair assistant. Output ONLY the corrected JSON object. No markdown.

Rules:
- prompt_version must be "{PROMPT_VERSION}"
- epistemic_tag must be EXPLICIT for all claims
- Every claim must have "evidence": [ at least one {{ "snippet": "...", "chunk_ref": {{...}} }} ]. Snippets must be verbatim from the chunk (<=300 chars).
- For every claim with missing or empty evidence, add exactly one evidence with snippet = a short verbatim quote from CHUNK TEXT (max 300 chars) and chunk_ref with chunk_id.
- ACTION value must have: actor, verb, object, qualifiers (array)
- ACTOR value: only name. OBJECT value: only name. STATE: object_name, state. DENY: actor, verb, object, reason
""".strip()

REPAIR_USER_TEMPLATE = """The raw extraction output (possibly truncated) was:

---
{raw_output}
---
{chunk_block}
Repair it into valid JSON. For each claim that has an empty or missing "evidence" array, add one element with "snippet" = a short verbatim quote from the CHUNK TEXT above and "chunk_ref": {{ "chunk_id": "<same as top-level chunk_id>"}}. All claim values must match v4 minimal shapes. Output ONLY the JSON object.
"""


def build_extraction_messages(chunk_id: str, chunk_text: str) -> list[dict[str, str]]:
    """Build [system, user] messages for v4 extraction."""
    return [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {
            "role": "user",
            "content": USER_TEMPLATE.format(
                chunk_id=chunk_id,
                chunk_text=chunk_text or "",
                prompt_version=PROMPT_VERSION,
            ),
        },
    ]


def build_repair_messages(
    raw_output: str,
    head_chars: int = 2000,
    tail_chars: int = 10000,
    chunk_text: str | None = None,
) -> list[dict[str, str]]:
    """Build repair prompt; truncate raw to head + tail. Include chunk_text so repair can add verbatim evidence."""
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
    if chunk_text:
        chunk_block = (
            "\nCHUNK TEXT (use this to add verbatim evidence snippets):\n---\n"
            + (chunk_text[:4000] if len(chunk_text) > 4000 else chunk_text)
            + "\n---\n\n"
        )
    else:
        chunk_block = ""
    user_content = REPAIR_USER_TEMPLATE.format(raw_output=snippet, chunk_block=chunk_block)
    return [
        {"role": "system", "content": REPAIR_SYSTEM + note},
        {"role": "user", "content": user_content},
    ]
