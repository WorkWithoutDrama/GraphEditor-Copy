"""Ollama embed client: POST to /api/embed."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.embeddings.settings import EmbedSettings

logger = logging.getLogger(__name__)

# Retries for transient failures (e.g. model loading)
_EMBED_RETRY_ATTEMPTS = 3
_EMBED_RETRY_DELAY = 3.0


class OllamaEmbedClient:
    """Embed texts via Ollama /api/embed endpoint."""

    def __init__(self, settings: EmbedSettings | None = None) -> None:
        self._settings = settings or EmbedSettings()
        self._base = self._settings.ollama_api_base.rstrip("/")
        self._model = self._settings.ollama_model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts. Returns list of vectors."""
        if not texts:
            return []

        payload: dict[str, Any] = {
            "model": self._model,
            "input": texts if len(texts) > 1 else texts[0],
            "keep_alive": self._settings.ollama_keep_alive,
        }

        timeout = self._settings.embed_timeout
        last_error: Exception | None = None
        for attempt in range(_EMBED_RETRY_ATTEMPTS):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(f"{self._base}/api/embed", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                break
            except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
                last_error = e
                if attempt < _EMBED_RETRY_ATTEMPTS - 1:
                    logger.warning(
                        "Embed request failed (attempt %s/%s): %s; retrying in %.1fs",
                        attempt + 1,
                        _EMBED_RETRY_ATTEMPTS,
                        e,
                        _EMBED_RETRY_DELAY,
                    )
                    await asyncio.sleep(_EMBED_RETRY_DELAY)
                else:
                    raise
        else:
            if last_error is not None:
                raise last_error
            raise RuntimeError("embed_texts: no response and no error")

        raw = data.get("embeddings", [])
        if not raw:
            return []
        if isinstance(raw[0], (int, float)):
            return [raw]
        return [[float(x) for x in vec] for vec in raw]
