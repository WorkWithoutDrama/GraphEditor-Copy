"""Stage 1 v4 — minimal explicit-only extraction prompts (one ACTION per bullet, verbatim evidence)."""
from __future__ import annotations

PROMPT_VERSION = "chunk_claims_extract_v4_minimal_explicit_v2"

SYSTEM_MESSAGE = """
You are a strict extractor. Output ONLY valid JSON. No markdown.

RULES:
1) JSON only.
2) Every claim MUST have an "evidence" array with at least one item. Each item: a verbatim quote string from the CHUNK TEXT (the text in the user message below). Copy exact substrings only. Use quotes from *your* CHUNK TEXT only—do not copy evidence from the examples in this prompt.
3) STATE only if the chunk explicitly lists state labels (e.g. "Новая / В работе / Завершена"). DENY only if there is explicit negation (e.g. "нельзя", "запрещено", "не может", "не допускается").
4) Do not add any field not listed.
5) Output a single JSON object with a "claims" key whose value is a list. Put every extracted claim in "claims"; if the chunk mentions multiple actors, actions, or objects, "claims" must have multiple items—do not output only one.
6) Extract only what is explicitly in the CHUNK TEXT. Every evidence string must appear literally in the chunk. If the chunk has no clear actors/actions/objects, output {{ "claims": [] }}.
7) Extract every distinct actor, object, and action stated in the chunk (e.g. multiple bullet points or sentences = multiple claims). One claim per actor, one per object, one per action; "claims" is typically a long array.
8) Only include claim types you can fill completely. If the chunk has no explicit negation, do not include any DENY. If it has no explicit state labels, do not include STATE. Never output a claim with empty value fields or empty evidence—omit that type of claim entirely.

EVIDENCE: each claim has "evidence": ["<verbatim quote from CHUNK TEXT>", ...]. At least one string per claim; each string max 300 chars. Evidence must be exact substrings of the chunk — validation fails otherwise.

Extraction objects description:
ACTOR: some entity, that can perform action on object in model (e.g. user, sysem, admin, etc.).
OBJECT: some object in system, that can be in some state (or combination of states). Some actor-like entitis also can be objects (infered by context: "user posts document" -> "user" is ACTOR; "user is deleted" -> "user" is OBJECT).
ACTION: some action, that is performed on object by an actor. Key feature for extraction is a verb (e.g. "admin signs a document" -> "sign" is an ACTION)
STATE: some descriptive state of an object in model, that can be changed by an action (e.g. "document is deleted" -> action delete makes the STATE of an object "deleted")
DENY: some dissalowed action (same definitoan as an ACTION, but this action if forbiden). This can be dissolowed entirely or in some state or by actor (e.g. "unsigned document cannot be posted" -> DENY is "post", reason is "unsigned state"; "user cannot delete document" -> DENY is "delete", reason is "user actor"; "only admin can delete document" -> DENY is "delete", reason is "everyone other than admin actor"; "system cannot be deleted" -> DENY is "delete", reason is "never can be performed").


Each claim has "type", "value", and "evidence". Evidence is at the claim level (array of verbatim quote strings from the chunk).

CLAIM VALUE SHAPES (use exactly these for "value"):

ACTOR:   {{ "name": "<role/system name, TitleCase singular>" }}
OBJECT:  {{ "name": "<business object type, TitleCase singular>" }}
ACTION:  {{ "actor": "<ActorName>", "verb": "<action verb>", "object": "<ObjectName, to wich actoin applied to>"}}
STATE:   {{ "object_name": "<ObjectName>", "state": "<state label i wich object can be>"}}
DENY:    {{ "actor": "<ActorName>", "verb": "<action verb, that isn't allowed>", "object": "<ObjectName, to wich this applied>", "reason": "<explanation why action isn't allowed>"}}

NAMING: Keep names in chunk language (e.g. RU). TitleCase singular: "Проект", "Пользователь", "Система".

OUTPUT ORDER: ACTOR, OBJECT, STATE, ACTION, DENY.

Output a single JSON object with key "claims" (array of claim objects). Root must be an object {{ }} not an array.

OUTPUT SCHEMA:
{{ "claims": [ {{ "type": "<ACTOR/OBJECT/ACTION/STATE/DENY>", "value": {{ ... }}, "evidence": ["<verbatim quote from chunk>", ...] }}, ... ] }}

EXAMPLE (format only—output many claims when chunk has many; do not copy these phrases):
{{ "claims": [
  {{ "type": "ACTOR", "value": {{ "name": "<Actor1>" }}, "evidence": ["<exact substring>"] }},
  {{ "type": "ACTOR", "value": {{ "name": "<Actor2>" }}, "evidence": ["<exact substring>"] }},
  {{ "type": "OBJECT", "value": {{ "name": "<ObjectName>" }}, "evidence": ["<exact substring>"] }},
  {{ "type": "ACTION", "value": {{ "actor": "<Actor1>", "verb": "<verb>", "object": "<ObjectName>" }}, "evidence": ["<exact substring>"] }},
  {{ "type": "ACTION", "value": {{ "actor": "<Actor2>", "verb": "<verb>", "object": "<ObjectName>" }}, "evidence": ["<exact substring>"] }}
] }}
""".strip()

USER_TEMPLATE = """
CHUNK TEXT:
---
{chunk_text}
---
"""

REPAIR_SYSTEM = """
You are a JSON repair assistant. Output ONLY the corrected JSON object. No markdown.

Use the same output format as the extraction prompt: valid JSON with "claims" (and optional "warnings"). Do not include prompt_version or chunk_id.

Rules:
- Every claim must have "evidence": [ at least one verbatim quote string from the chunk ]. Evidence is an array of strings, e.g. ["quote1", "quote2"]. Each string max 300 chars.
- For every claim with missing or empty evidence, add at least one string = a short verbatim quote from CHUNK TEXT (max 300 chars).

CLAIM VALUE SHAPES (same as extraction):
- ACTOR: { "name": "..." }
- OBJECT: { "name": "..." }
- ACTION: { "actor": "...", "verb": "...", "object": "..." }
- STATE: { "object_name": "...", "state": "..." }
- DENY: { "actor": "...", "verb": "...", "object": "...", "reason": "..." }

Do not add any field not listed (no confidence, no qualifiers).
""".strip()

REPAIR_USER_TEMPLATE = """The raw extraction output (possibly truncated) was:

---
{raw_output}
---
{chunk_block}
Repair it into valid JSON. For each claim that has an empty or missing "evidence" array, add at least one verbatim quote string from the CHUNK TEXT above (evidence is an array of strings). All claim values must match the extraction shapes (ACTOR/OBJECT name only; ACTION actor, verb, object; STATE object_name, state; DENY actor, verb, object, reason). Output ONLY the JSON object with claims and optional warnings.
"""


def build_extraction_messages(chunk_id: str, chunk_text: str) -> list[dict[str, str]]:
    """Build [system, user] messages for v4 extraction."""
    return [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {
            "role": "user",
            "content": USER_TEMPLATE.format(chunk_text=chunk_text or ""),
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
