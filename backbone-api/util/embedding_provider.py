"""Embedding provider abstraction and Ollama implementation.

This module defines a minimal async interface for embedding services and
provides an implementation that talks to an external Ollama instance.

The design follows the constraints:

* No Docker or Nomic SDK usage.
* Configuration via environment variables.
* All HTTP errors propagate as ``httpx.HTTPError``.
* The provider is fully testable by mocking :class:`httpx.AsyncClient`.
"""

from __future__ import annotations

import os
from typing import List, Any
import numpy as np
import httpx

__all__ = ["EmbeddingProvider", "OllamaEmbeddingProvider"]


class EmbeddingProvider:
    """Abstract base class for embedding provider.

    Subclasses must implement :meth:`embed` 
    """

    async def embed(self, text: str) -> List[float]:
        raise NotImplementedError


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama‑backed embedding provider.

    The provider reads two environment variables at construction time:

    * ``OLLAMA_BASE_URL`` – Base URL of the Ollama server (e.g.
      ``http://ollama.example.com:11434``).  This variable is required.
    * ``OLLAMA_EMBED_MODEL`` – Name of the model to use for embeddings.
      Defaults to ``nomic-embed-text:latest``.
    """

    def __init__(self) -> None:
        base = os.getenv("OLLAMA_BASE_URL")
        if not base:
            raise ValueError("Environment variable OLLAMA_BASE_URL must be set")
        self.base_url = base.rstrip("/")
        self.model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        self.client = httpx.AsyncClient(base_url=self.base_url)

    async def _post(self, payload: Any) -> Any:
        """Send a POST request to the Ollama embeddings endpoint.

        Raises ``httpx.HTTPError`` on network or HTTP errors.
        """
        url = "/api/embeddings"
        response = await self.client.post(url, json=payload, timeout=30.0)
        print("POST ATTEMPT",url, payload)
        response.raise_for_status()
        return response.json()

    async def embed(self, text: str) -> List[float]:
        if not text:
            return []
        payload = {"model": self.model, "prompt": text}
        data = await self._post(payload)
        vector = data["embedding"]
        # Return as normalized float32 for fast dot-product cosine similarity
        arr = np.array(vector, dtype=np.float32)
                    
        embedding =  (arr / np.linalg.norm(arr)).astype(float).tolist() 
 
        if not isinstance(embedding, list) or not all(isinstance(v, (float, int)) for v in embedding):
            raise ValueError("Malformed response: embedding must be list of floats")
        return embedding

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.aclose()

# End of module
