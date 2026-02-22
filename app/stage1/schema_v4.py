"""Stage 1 v4 Pydantic schemas: minimal explicit-only claim shapes (extra=forbid)."""
from __future__ import annotations

from typing import Annotated, Literal, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

PROMPT_VERSION_V4 = "chunk_claims_extract_v4_minimal_explicit_v2"


# --- Evidence V4 ---
class ChunkRefV4(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str


class EvidenceV4(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snippet: Annotated[str, Field(min_length=1, max_length=300)]
    chunk_ref: ChunkRefV4 | None = None


# --- Claim value types V4 (minimal) ---
class ActorValueV4(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str

    @field_validator("name")
    @classmethod
    def name_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must be non-empty")
        return v.strip()


class ObjectValueV4(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str

    @field_validator("name")
    @classmethod
    def name_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must be non-empty")
        return v.strip()


class ActionMentionValueV4(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor: str
    verb: str
    object: str

    @field_validator("actor", "verb", "object")
    @classmethod
    def strip_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("actor/verb/object must be non-empty")
        return v.strip()


class StateValueV4(BaseModel):
    model_config = ConfigDict(extra="forbid")
    object_name: str
    state: str

    @field_validator("object_name", "state")
    @classmethod
    def strip_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("object_name/state must be non-empty")
        return v.strip()


class DenyValueV4(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor: str
    verb: str
    object: str
    reason: str | None = None

    @field_validator("actor", "verb", "object")
    @classmethod
    def strip_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("actor/verb/object must be non-empty")
        return v.strip()


# --- Claim V4: discriminated by type so value shape is unambiguous ---
class _ClaimV4Base(BaseModel):
    model_config = ConfigDict(extra="forbid")
    epistemic_tag: Literal["EXPLICIT"] = "EXPLICIT"
    # Allow empty so parsing succeeds when LLM omits evidence; post-parse validator requires at least one
    evidence: list[EvidenceV4] = Field(default_factory=list)


class ActorClaimV4(_ClaimV4Base):
    type: Literal["ACTOR"] = "ACTOR"
    value: ActorValueV4


class ObjectClaimV4(_ClaimV4Base):
    type: Literal["OBJECT"] = "OBJECT"
    value: ObjectValueV4


class StateClaimV4(_ClaimV4Base):
    type: Literal["STATE"] = "STATE"
    value: StateValueV4


class ActionClaimV4(_ClaimV4Base):
    type: Literal["ACTION"] = "ACTION"
    value: ActionMentionValueV4


class DenyClaimV4(_ClaimV4Base):
    type: Literal["DENY"] = "DENY"
    value: DenyValueV4


ClaimV4 = Annotated[
    ActorClaimV4 | ObjectClaimV4 | StateClaimV4 | ActionClaimV4 | DenyClaimV4,
    Field(discriminator="type"),
]


class Stage1ResultV4(BaseModel):
    # extra="ignore" so LLM output with claim fields duplicated at root still parses
    model_config = ConfigDict(extra="ignore")
    prompt_version: Literal["chunk_claims_extract_v4_minimal_explicit_v2"] = PROMPT_VERSION_V4
    chunk_id: str
    claims: list[ClaimV4] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


SNIPPET_MAX_LENGTH = 300


def _normalize_evidence_list(
    evidence_list: Any,
    chunk_id: str,
    claim_type: str,
    warnings: list[str],
) -> list[dict[str, Any]]:
    """Normalize evidence items: accept string or {snippet}; fix chunk_ref, truncate snippet if > 300 chars. Mutates warnings."""
    if not isinstance(evidence_list, list):
        return []
    result: list[dict[str, Any]] = []
    for i, ev in enumerate(evidence_list):
        if isinstance(ev, str):
            snippet = ev
            if len(snippet) > SNIPPET_MAX_LENGTH:
                snippet = snippet[:SNIPPET_MAX_LENGTH]
                warnings.append(f"Truncated evidence to {SNIPPET_MAX_LENGTH} chars for claim type {claim_type}")
            ev = {"snippet": snippet, "chunk_ref": {"chunk_id": chunk_id}}
            result.append(ev)
            continue
        if not isinstance(ev, dict):
            continue
        snippet = ev.get("snippet")
        if isinstance(snippet, str):
            if len(snippet) > SNIPPET_MAX_LENGTH:
                ev = {**ev, "snippet": snippet[:SNIPPET_MAX_LENGTH]}
                warnings.append(f"Truncated evidence to {SNIPPET_MAX_LENGTH} chars for claim type {claim_type}")
        chunk_ref = ev.get("chunk_ref")
        if not isinstance(chunk_ref, dict) or not isinstance(chunk_ref.get("chunk_id"), str):
            ev = {
                **ev,
                "chunk_ref": {"chunk_id": chunk_id},
            }
        result.append(ev)
    return result


def _normalize_claims_for_parsing(data: dict[str, Any], chunk_id: str) -> None:
    """
    Mutate data so claims list only contains valid claim dicts; drop malformed items.
    LLM sometimes omits evidence, outputs truncated JSON (strings in list), or duplicates keys at root.
    Normalizes evidence: chunk_ref fixed if missing/invalid; snippet truncated to 300 chars with warning.
    """
    raw_claims = data.get("claims")
    if not isinstance(raw_claims, list):
        data["claims"] = []
        data.setdefault("warnings", [])
        return
    allowed_types = ("ACTOR", "OBJECT", "STATE", "ACTION", "DENY")
    warnings: list[str] = list(data.get("warnings") or [])
    normalized: list[dict[str, Any]] = []
    dropped = 0
    for item in raw_claims:
        if not isinstance(item, dict):
            dropped += 1
            continue
        t = item.get("type")
        if t not in allowed_types:
            # Type "CLAIM" or unknown with "state"/"action" -> expand into STATE and/or ACTION claims
            state_val = item.get("state") if isinstance(item.get("state"), dict) else None
            action_val = item.get("action") if isinstance(item.get("action"), dict) else None
            base_evidence: list[Any] = item.get("evidence") if isinstance(item.get("evidence"), list) else []
            expanded: list[dict[str, Any]] = []
            if state_val and isinstance(state_val.get("object_name"), str) and isinstance(state_val.get("state"), str):
                expanded.append({
                    "type": "STATE",
                    "epistemic_tag": "EXPLICIT",
                    "value": {"object_name": str(state_val["object_name"]).strip(), "state": str(state_val["state"]).strip()},
                    "evidence": base_evidence.copy(),
                })
            if action_val and isinstance(action_val.get("actor"), str) and isinstance(action_val.get("verb"), str) and isinstance(action_val.get("object"), str):
                expanded.append({
                    "type": "ACTION",
                    "epistemic_tag": "EXPLICIT",
                    "value": {
                        "actor": str(action_val["actor"]).strip(),
                        "verb": str(action_val["verb"]).strip(),
                        "object": str(action_val["object"]).strip(),
                    },
                    "evidence": base_evidence.copy(),
                })
            if expanded:
                for sub in expanded:
                    sub["evidence"] = _normalize_evidence_list(sub["evidence"], chunk_id, str(sub["type"]), warnings)
                    normalized.append(sub)
                continue
            # Bare value object? Try to infer type and wrap
            if "name" in item and "actor" not in item and "object_name" not in item:
                if "verb" in item or "object" in item:
                    dropped += 1
                    continue
                item = {"type": "OBJECT", "epistemic_tag": "EXPLICIT", "value": {"name": item["name"]}, "evidence": item.get("evidence", [])}
            else:
                dropped += 1
                continue
        if "evidence" not in item:
            item = {**item, "evidence": []}
        # Normalize evidence: fix chunk_ref, truncate long snippets
        item["evidence"] = _normalize_evidence_list(
            item["evidence"],
            chunk_id,
            str(t),
            warnings,
        )
        # Drop claims with no evidence (prompt says omit such types entirely)
        if not item["evidence"]:
            dropped += 1
            continue
        if "epistemic_tag" not in item:
            item = {**item, "epistemic_tag": "EXPLICIT"}
        if "confidence" in item:
            item = {k: v for k, v in item.items() if k != "confidence"}
        # Drop DENY with empty required value fields (prompt says do not include if cannot extract)
        if t == "DENY" and isinstance(item.get("value"), dict):
            val = item["value"]
            if not (str(val.get("actor") or "").strip()) or not (str(val.get("verb") or "").strip()) or not (str(val.get("object") or "").strip()):
                dropped += 1
                warnings.append("Skipped DENY claim with empty actor/verb/object")
                continue
        # STATE value requires both object_name and state; fill missing state so validation passes
        if t == "STATE" and isinstance(item.get("value"), dict):
            val = item["value"]
            if "state" not in val or not isinstance(val.get("state"), str) or not str(val.get("state", "")).strip():
                val = {**val, "state": (val.get("state") or "").strip() or "(unspecified)"}
                item = {**item, "value": val}
                warnings.append("STATE claim missing or empty 'state'; set to '(unspecified)'")
        if t == "ACTION" and isinstance(item.get("value"), dict) and "qualifiers" in item["value"]:
            item = {**item, "value": {k: v for k, v in item["value"].items() if k != "qualifiers"}}
        normalized.append(item)
    data["claims"] = normalized
    data["warnings"] = warnings
    if dropped:
        data["warnings"].append(f"Skipped {dropped} malformed claim entry(ies)")


def _try_repair_truncated_json(s: str):  # returns dict or raises
    """Attempt to fix truncated JSON (e.g. unterminated string). Returns parsed dict or re-raises."""
    import json
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        err_msg = str(e)
        if "Unterminated string" not in err_msg and "Expecting value" not in err_msg:
            raise
        pos = getattr(e, "pos", None)
    else:
        pos = None

    # 1) Try fixed suffixes first
    for suffix in ('"}]}', '"}\n]}\n}', '"]}', '"}', '}]}'):
        try:
            return json.loads(s + suffix)
        except json.JSONDecodeError:
            continue

    # 2) Use error position: close string at pos then close structure
    if pos is not None and pos <= len(s):
        try:
            repaired = s[:pos] + '"'
            if '"claims"' in repaired and repaired.rstrip().endswith('"'):
                repaired += "]}" if repaired.strip().endswith('[') or '[' in repaired[repaired.rfind('"claims"'):] else "}]}"
            else:
                repaired += "]}"
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

    # 3) Trim to last complete claim: find last "}, or "}\n, then close claims array and root
    for needle in ('"},', '"}\n,'):
        idx = s.rfind(needle)
        if idx != -1:
            # Include the "}" (and drop trailing comma if we use it as boundary)
            up_to = idx + 2
            try:
                trimmed = s[:up_to].rstrip().rstrip(",") + "]}"
                return json.loads(trimmed)
            except json.JSONDecodeError:
                continue

    raise ValueError("JSON could not be parsed or repaired (possibly truncated)")


def parse_stage1_v4(raw: str | dict[str, Any] | list[Any], chunk_id: str) -> Stage1ResultV4:
    """Parse JSON (string, dict, or list of claims) and validate as Stage1ResultV4. Raises ValidationError on failure."""
    import json
    if isinstance(raw, dict):
        data: Any = raw
    elif isinstance(raw, list):
        data = {"claims": raw, "warnings": []}
    else:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = _try_repair_truncated_json(raw)
    # Accept root as array of claims (matches OUTPUT SCHEMA: list of { type, value, evidence })
    if isinstance(data, list):
        data = {"claims": data, "warnings": []}
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object or array of claims")
    if "chunk_id" not in data:
        data = {**data, "chunk_id": chunk_id}
    # If root looks like a single claim (has type + evidence but no claims array), wrap in claims
    if "claims" not in data or not isinstance(data.get("claims"), list):
        if isinstance(data.get("type"), str) and "evidence" in data:
            single_claim = {
                "type": data["type"],
                "evidence": data.get("evidence", []),
                "value": data.get("value"),
            }
            if data.get("state") is not None:
                single_claim["state"] = data["state"]
            if data.get("action") is not None:
                single_claim["action"] = data["action"]
            data = {
                **{k: v for k, v in data.items() if k not in ("type", "evidence", "state", "action", "value")},
                "claims": [single_claim],
                "warnings": data.get("warnings", []),
            }
            if "chunk_id" not in data:
                data["chunk_id"] = chunk_id
        else:
            data.setdefault("claims", [])
    _normalize_claims_for_parsing(data, chunk_id)
    return Stage1ResultV4.model_validate(data)
