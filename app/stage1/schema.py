"""Pydantic schemas for Stage 1 LLM extraction output (strict validation)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

# Stage 1 v1: only these epistemic tags (addressed doc D0.3)
EPISTEMIC_EXPLICIT = "EXPLICIT"
EPISTEMIC_IMPLICIT = "IMPLICIT"
EPISTEMIC_MODEL_INFERRED = "MODEL_INFERRED"
EPISTEMIC_TAGS = (EPISTEMIC_EXPLICIT, EPISTEMIC_IMPLICIT, EPISTEMIC_MODEL_INFERRED)

CLAIM_TYPE_ACTOR = "ACTOR"
CLAIM_TYPE_OBJECT = "OBJECT"
CLAIM_TYPE_STATE = "STATE"
CLAIM_TYPE_ACTION = "ACTION"
CLAIM_TYPE_DENY = "DENY"
CLAIM_TYPE_NOTE = "NOTE"
CLAIM_TYPES = (CLAIM_TYPE_ACTOR, CLAIM_TYPE_OBJECT, CLAIM_TYPE_STATE, CLAIM_TYPE_ACTION, CLAIM_TYPE_DENY, CLAIM_TYPE_NOTE)


# --- Evidence ---
class ChunkRef(BaseModel):
    chunk_id: str
    char_start: int | None = None
    char_end: int | None = None


class Evidence(BaseModel):
    snippet: str = Field(..., max_length=500)
    chunk_ref: ChunkRef | None = None


# --- Claim value types (per plan 03) ---
class ActorValue(BaseModel):
    name: str
    kind: Literal["role", "system", "external", "unknown"] | None = None
    description: str | None = None


class ObjectValue(BaseModel):
    name: str
    description: str | None = None


class StateValue(BaseModel):
    object_name: str
    state: str


class ActionEffect(BaseModel):
    transition_to: str | None = None
    no_change: bool | None = None


class ActionValue(BaseModel):
    name: str
    goal: str | None = None
    actors_allowed: list[str] = Field(default_factory=list)
    target_object: str | None = None
    allowed_states: list[str] = Field(default_factory=list)
    effect: ActionEffect | dict[str, Any] | None = None
    place: str | None = None
    metadata_refs: dict[str, Any] | None = None


class DenyValue(BaseModel):
    actor: str
    action_name: str
    reason: str | None = None


class NoteValue(BaseModel):
    text: str = Field(..., max_length=500)


# --- Claim (discriminated by type) ---
class Claim(BaseModel):
    type: Literal["ACTOR", "OBJECT", "STATE", "ACTION", "DENY", "NOTE"]
    epistemic_tag: Literal["EXPLICIT", "IMPLICIT", "MODEL_INFERRED"]  # RULE_INFERRED not allowed in v1
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    rule_id: str | None = None
    value: ActorValue | ObjectValue | StateValue | ActionValue | DenyValue | NoteValue | dict[str, Any]
    evidence: list[Evidence] = Field(..., min_length=1)

    @model_validator(mode="after")
    def model_inferred_requires_rationale_low_confidence(self) -> "Claim":
        if self.epistemic_tag != EPISTEMIC_MODEL_INFERRED:
            return self
        if self.confidence is not None and self.confidence > 0.5:
            raise ValueError("MODEL_INFERRED must have confidence <= 0.5")
        if isinstance(self.value, dict):
            if "rationale" not in self.value:
                raise ValueError("MODEL_INFERRED must include rationale in value")
        return self


# Allow NOTE with no evidence in schema for future; v1 prompt requires evidence for all
# So we keep evidence min_length=1; when NOTE is enabled we could relax per claim type.


class Stage1ExtractionResult(BaseModel):
    prompt_version: str = "chunk_claims_extract_v1"
    chunk_id: str
    summary: str = ""
    claims: list[Claim] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def parse_and_validate_extraction(raw: str, chunk_id: str) -> Stage1ExtractionResult:
    """Parse JSON string and validate as Stage1ExtractionResult. Raises ValidationError on failure."""
    import json
    data = json.loads(raw) if isinstance(raw, str) else raw
    if "chunk_id" not in data:
        data["chunk_id"] = chunk_id
    return Stage1ExtractionResult.model_validate(data)
