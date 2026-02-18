"""Stage 1 LLM extraction: call LLM, parse JSON, repair if needed."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.llm.client_litellm import LiteLLMClient
from app.llm.types import LLMMessage, LLMRequest, LLMProvider
from app.stage1.config import REPAIR_RAW_HEAD_CHARS, REPAIR_RAW_TAIL_CHARS
from app.stage1.prompt import build_extraction_messages, build_repair_messages
from app.stage1.schema import Stage1ExtractionResult, parse_and_validate_extraction

logger = logging.getLogger(__name__)

# Default model_id format: "provider/modelname" e.g. ollama/llama3.2
def _provider_from_model_id(model_id: str) -> LLMProvider:
    prefix = (model_id or "").split("/")[0].lower()
    if prefix == "gemini" or prefix.startswith("gemini/"):
        return LLMProvider.GEMINI
    return LLMProvider.OLLAMA


def _strip_json_block(raw: str) -> str:
    """Remove markdown code fence if present."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    return raw.strip()


async def extract_one_chunk(
    chunk_id: str,
    chunk_text: str,
    model_id: str,
    temperature: float,
    max_tokens: int,
    client: LiteLLMClient | None = None,
    repair_attempts: int = 1,
    repair_raw_max_chars: int = 12_000,
    timeout_s: float = 210.0,
) -> tuple[Stage1ExtractionResult | None, str | None, str | None, dict[str, Any] | None]:
    """
    Call LLM to extract claims from one chunk. Returns (result, raw_text, error_message, usage_dict).
    On validation failure, tries repair once; if still failing returns (None, raw_text, error, usage).
    """
    client = client or LiteLLMClient(concurrency_limit=8, max_retries=2)
    provider = _provider_from_model_id(model_id)
    messages = build_extraction_messages(chunk_id, chunk_text or "")
    req = LLMRequest(
        messages=[LLMMessage(role=m["role"], content=m["content"]) for m in messages],
        temperature=temperature,
        max_output_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    raw_text: str | None = None
    usage_dict: dict[str, Any] | None = None
    try:
        resp = await client.acompletion(provider, model_id, req, timeout_s=timeout_s)
        raw_text = resp.text
        usage_dict = {
            "prompt_tokens": resp.usage.input_tokens if resp.usage else 0,
            "completion_tokens": resp.usage.output_tokens if resp.usage else 0,
            "total_tokens": resp.usage.total_tokens if resp.usage else 0,
            "latency_ms": resp.latency_ms,
        }
    except Exception as e:
        logger.warning("LLM call failed for chunk %s: %s", chunk_id, e)
        return None, None, str(e), None

    # Parse and validate
    try:
        cleaned = _strip_json_block(raw_text)
        result = parse_and_validate_extraction(cleaned, chunk_id)
        return result, raw_text, None, usage_dict
    except Exception as e:
        validation_error = str(e)
        logger.debug("Validation failed for chunk %s: %s", chunk_id, validation_error)
    # Repair
    for attempt in range(repair_attempts):
        try:
            repair_messages = build_repair_messages(
                raw_text or "",
                head_chars=REPAIR_RAW_HEAD_CHARS,
                tail_chars=min(repair_raw_max_chars - REPAIR_RAW_HEAD_CHARS, 10_000),
            )
            repair_req = LLMRequest(
                messages=[LLMMessage(role=m["role"], content=m["content"]) for m in repair_messages],
                temperature=0.0,
                max_output_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            repair_resp = await client.acompletion(provider, model_id, repair_req, timeout_s=timeout_s)
            repair_raw = repair_resp.text
            cleaned = _strip_json_block(repair_raw)
            result = parse_and_validate_extraction(cleaned, chunk_id)
            return result, raw_text, None, usage_dict
        except Exception as repair_e:
            logger.debug("Repair attempt %s failed for chunk %s: %s", attempt + 1, chunk_id, repair_e)
            validation_error = str(repair_e)
    return None, raw_text, validation_error, usage_dict
