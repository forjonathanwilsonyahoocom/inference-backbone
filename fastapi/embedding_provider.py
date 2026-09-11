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
    """Abstract base class for embedding providers.

    Subclasses must implement :meth:`embed_documents` and
    :meth:`embed_query`.
    """

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    async def embed_query(self, text: str) -> List[float]:
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

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = []
        for text in texts:
            payload = {"model": self.model, "prompt": text}
            data = await self._post(payload)
            
            vector = data["embedding"]
            # Return as normalized float32 for fast dot-product cosine similarity
            arr = np.array(vector, dtype=np.float32)
                        
            embeddings = embeddings + [ arr / np.linalg.norm(arr)]
            print("EMBEDDED!")
            
        if embeddings is None or not isinstance(embeddings, list):
            raise ValueError("Malformed response: missing 'embeddings' list")
        # Validate each embedding is a list of floats
        for emb in embeddings:
            if not isinstance(emb, list) or not all(isinstance(v, (float, int)) for v in emb):
                raise ValueError("Malformed response: embeddings must be list of floats")
        return embeddings

    async def embed_query(self, text: str) -> List[float]:
        if not text:
            return []
        payload = {"model": self.model, "input": text}
        data = await self._post(payload)
        embeddings = data.get("embeddings")
        if embeddings is None or not isinstance(embeddings, list):
            raise ValueError("Malformed response: missing 'embeddings' list")
        if len(embeddings) != 1:
            raise ValueError("Malformed response: expected single embedding for query")
        emb = embeddings[0]
        if not isinstance(emb, list) or not all(isinstance(v, (float, int)) for v in emb):
            raise ValueError("Malformed response: embedding must be list of floats")
        return emb

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.aclose()

# End of module
