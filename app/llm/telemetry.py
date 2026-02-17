"""Observability: redaction, structured logging, metrics. No ad hoc logs in service/client."""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Redaction: patterns to mask (never log or store raw)
_SECRET_PATTERNS = [
    re.compile(r"\b(?:sk-[a-zA-Z0-9]{20,})\b", re.IGNORECASE),  # OpenAI-style
    re.compile(r"\b(?:AIza[a-zA-Z0-9_-]{35})\b"),  # Google API key style
    re.compile(r"\bBearer\s+[a-zA-Z0-9_.-]+\b", re.IGNORECASE),
]
_PII_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")  # email
_PREVIEW_MAX_CHARS = 200


def redact_preview(text: str) -> str:
    """Redact secrets and PII, then truncate. Use for prompt/response previews."""
    if not text:
        return ""
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    out = _PII_PATTERN.sub("[EMAIL]", out)
    if len(out) > _PREVIEW_MAX_CHARS:
        out = out[: _PREVIEW_MAX_CHARS] + "..."
    return out


def log_llm_call(
    *,
    llm_run_id: str,
    workspace_id: str | None = None,
    provider: str,
    model: str,
    profile: str,
    stage: str | None = None,
    latency_ms: int,
    status: str,
    error_code: str | None = None,
) -> None:
    """Emit structured log for one LLM call. Never log prompt text or API keys."""
    extra: dict[str, Any] = {
        "llm_run_id": llm_run_id,
        "provider": provider,
        "model": model,
        "profile": profile,
        "latency_ms": latency_ms,
        "status": status,
    }
    if workspace_id is not None:
        extra["workspace_id"] = workspace_id
    if stage is not None:
        extra["stage"] = stage
    if error_code is not None:
        extra["error_code"] = error_code
    logger.info("llm_call", extra=extra)


# Metrics: stub implementation. Register with Prometheus if the app has a registry.
_metrics_enabled = False


def set_metrics_enabled(enabled: bool) -> None:
    global _metrics_enabled
    _metrics_enabled = enabled


def emit_request_metric(provider: str, model: str, profile: str, status: str) -> None:
    if _metrics_enabled:
        pass  # TODO: llm_requests_total.labels(...).inc()
    else:
        logger.debug("metric llm_requests_total %s %s %s %s", provider, model, profile, status)


def emit_latency_metric(provider: str, model: str, latency_ms: float) -> None:
    if _metrics_enabled:
        pass  # TODO: llm_latency_ms.labels(...).observe(latency_ms)
    else:
        logger.debug("metric llm_latency_ms %s %s %s", provider, model, latency_ms)


def emit_tokens_metric(provider: str, model: str, kind: str, count: int) -> None:
    if _metrics_enabled:
        pass
    else:
        logger.debug("metric llm_tokens %s %s %s %s", provider, model, kind, count)


def emit_error_metric(provider: str, code: str) -> None:
    if _metrics_enabled:
        pass
    else:
        logger.debug("metric llm_errors %s %s", provider, code)


def stable_hash(content: str) -> str:
    """SHA256 hex digest for canonical cache/idempotency keys."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
