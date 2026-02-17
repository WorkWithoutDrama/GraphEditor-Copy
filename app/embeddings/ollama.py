"""Ollama embed client: POST to /api/embed."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.embeddings.settings import EmbedSettings

logger = logging.getLogger(__name__)


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
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self._base}/api/embed", json=payload)
            resp.raise_for_status()
            data = resp.json()

        raw = data.get("embeddings", [])
        if not raw:
            return []
        if isinstance(raw[0], (int, float)):
            return [raw]
        return [[float(x) for x in vec] for vec in raw]
