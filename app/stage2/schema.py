"""Stage 2 decision output schema (matches output_schema.md)."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceRef(BaseModel):
    """Internal: full reference after resolution (used by applier and audit)."""
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    evidence_id: str | None = None
    chunk_id: str | None = None
    snippet: str | None = None


class EvidenceRefLLM(BaseModel):
    """LLM-facing: only snippet; claim_id, evidence_id, chunk_id are filled server-side."""
    model_config = ConfigDict(extra="forbid")
    snippet: str = ""


class DecisionBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal[
        "ACCEPT_AS_CANONICAL",
        "MERGE_INTO",
        "REJECT",
        "DEFER",
        "SPLIT_CONFLICT",
    ]
    canonical_claim_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = ""
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class NormalizationBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    canonical_label: str | None = None
    aliases: list[str] = Field(default_factory=list)
    notes: str | None = None


class ActionEndpoints(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor_claim_id: str | None = None
    object_claim_id: str | None = None


class AttachmentsBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    object_claim_ids: list[str] = Field(default_factory=list)
    actor_claim_ids: list[str] = Field(default_factory=list)
    action_endpoints: ActionEndpoints = Field(default_factory=ActionEndpoints)


class ConflictMember(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    role: Literal["seed", "candidate", "other"]
    reason: str = ""


class ConflictBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_label: str | None = None
    members: list[ConflictMember] = Field(default_factory=list)


class DecisionBlockLLM(BaseModel):
    """LLM-facing: evidence_refs contain only snippet; IDs filled server-side."""
    model_config = ConfigDict(extra="forbid")
    kind: Literal[
        "ACCEPT_AS_CANONICAL",
        "MERGE_INTO",
        "REJECT",
        "DEFER",
        "SPLIT_CONFLICT",
    ]
    canonical_claim_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = ""
    evidence_refs: list[EvidenceRefLLM] = Field(default_factory=list)


class Stage2DecisionOutputLLM(BaseModel):
    """LLM output: no seed_claim_id; evidence_refs snippet-only. Convert to Stage2DecisionOutput after resolution."""

    model_config = ConfigDict(extra="ignore")

    pass_kind: Annotated[
        Literal["ACTOR", "OBJECT", "STATE", "ACTION"],
        Field(description="Must match the pass that produced this decision"),
    ]
    decision: DecisionBlockLLM
    normalization: NormalizationBlock = Field(default_factory=NormalizationBlock)
    attachments: AttachmentsBlock = Field(default_factory=AttachmentsBlock)
    conflict: ConflictBlock = Field(default_factory=ConflictBlock)


class Stage2DecisionOutput(BaseModel):
    """Internal Stage-2 decision (after filling seed_claim_id and resolving evidence_refs); used by applier and audit."""

    model_config = ConfigDict(extra="ignore")

    pass_kind: Annotated[
        Literal["ACTOR", "OBJECT", "STATE", "ACTION"],
        Field(description="Must match the pass that produced this decision"),
    ]
    seed_claim_id: str
    decision: DecisionBlock
    normalization: NormalizationBlock = Field(default_factory=NormalizationBlock)
    attachments: AttachmentsBlock = Field(default_factory=AttachmentsBlock)
    conflict: ConflictBlock = Field(default_factory=ConflictBlock)
