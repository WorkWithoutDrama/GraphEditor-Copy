"""Stage 1 parser registry: prompt_version -> (parse_fn, post_validators)."""
from __future__ import annotations

import json
from typing import Any, Callable

from app.stage1.schema import parse_and_validate_extraction
from app.stage1.schema_v4 import parse_stage1_v4, PROMPT_VERSION_V4
from app.stage1.validators import validate_evidence_substrings

PROMPT_VERSION_V3 = "chunk_claims_extract_v3_explicit_only"

# Post-validator: (result, chunk_text) -> list[str] (warnings). Substring validator raises.
PostValidator = Callable[[Any, str], list[str]]

_REGISTRY: dict[str, tuple[Callable[[str | dict, str], Any], list[PostValidator]]] = {}


def _v4_substring_validator(result: Any, chunk_text: str) -> list[str]:
    """Drop claims with invalid evidence (no evidence or snippet not in chunk); return warnings."""
    return validate_evidence_substrings(result, chunk_text)


def _parse_v3(raw: str | dict[str, Any], chunk_id: str):
    return parse_and_validate_extraction(
        json.dumps(raw) if isinstance(raw, dict) else raw, chunk_id
    )


def register(
    prompt_version: str,
    parse_fn: Callable[[str | dict, str], Any],
    post_validators: list[PostValidator] | None = None,
) -> None:
    _REGISTRY[prompt_version] = (parse_fn, post_validators or [])


def get(
    prompt_version: str,
) -> tuple[Callable[[str | dict, str], Any], list[PostValidator]]:
    """Return (parse_fn, post_validators) for the given prompt_version."""
    entry = _REGISTRY.get(prompt_version)
    if entry is None:
        raise KeyError(f"Unknown prompt_version: {prompt_version}")
    return entry


def parse_with_registry(
    raw: str | dict[str, Any],
    chunk_id: str,
    chunk_text: str,
    *,
    prompt_version: str | None = None,
) -> tuple[Any, list[str]]:
    """
    Parse raw output using the registry for the given (or detected) prompt_version.
    Runs post_validators (v4: substring validation).
    Returns (result, list of extra warnings). Substring validator may raise ValueError.
    """
    if prompt_version is None and isinstance(raw, dict):
        prompt_version = raw.get("prompt_version")
    if prompt_version is None and isinstance(raw, str):
        try:
            data = json.loads(raw)
            prompt_version = data.get("prompt_version")
        except Exception:
            pass
    if not prompt_version:
        prompt_version = PROMPT_VERSION_V4
    parse_fn, post_validators = get(prompt_version)
    result = parse_fn(raw, chunk_id)
    extra_warnings: list[str] = []
    for validator in post_validators:
        extra_warnings.extend(validator(result, chunk_text))
    return result, extra_warnings


# Register v3 (existing schema, no post validators)
register(PROMPT_VERSION_V3, _parse_v3, [])

# Register v4 (v4 schema + substring validator)
register(
    PROMPT_VERSION_V4,
    parse_stage1_v4,
    [_v4_substring_validator],
)
