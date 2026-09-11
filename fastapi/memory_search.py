"""FastAPI endpoint for semantic search over the MemoryArtifact collection.

The endpoint implements the specification:

* POST /memory/search
* Request body: ``{"query": "text", "limit": 8}``
* Pipeline:
  1. Embed the query using :class:`OllamaEmbeddingProvider`.
  2. Perform a vector search against the ``MemoryArtifact`` collection.
  3. Return a list of results containing only the required fields.

The implementation uses the Weaviate 4.23.x collections/query API and
does not expose the raw client to callers.
"""

from __future__ import annotations

import os
from typing import List, Dict

import weaviate
from weaviate.classes.config import Configure

from .embedding_provider import OllamaEmbeddingProvider

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------
_HTTP_HOST = os.getenv("WEAVIATE_HTTP_HOST", "weaviate")
_HTTP_PORT = int(os.getenv("WEAVIATE_HTTP_PORT", "8080"))
_GRPC_HOST = os.getenv("WEAVIATE_GRPC_HOST", "weaviate")
_GRPC_PORT = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))

# ---------------------------------------------------------------------------
# Helper: create a Weaviate client
# ---------------------------------------------------------------------------

def _get_client() -> weaviate.Client:
    return weaviate.connect_to_custom(
        http_host=_HTTP_HOST,
        http_port=_HTTP_PORT,
        http_secure=False,
        grpc_host=_GRPC_HOST,
        grpc_port=_GRPC_PORT,
        grpc_secure=False,
    )

# ---------------------------------------------------------------------------
# FastAPI router
# ---------------------------------------------------------------------------
from fastapi import APIRouter, HTTPException

router = APIRouter()

# ---------------------------------------------------------------------------
# Endpoint implementation
# ---------------------------------------------------------------------------
@router.post("/memory/search")
async def memory_search(payload: Dict) -> List[Dict]:
    """Perform a semantic search over the MemoryArtifact collection.

    Expected JSON keys:
    * ``query`` – the search string
    * ``limit`` – optional maximum number of results (default 8)
    """
    if "query" not in payload:
        raise HTTPException(status_code=400, detail="Missing required key: query")
    query_text: str = payload["query"]
    limit: int = int(payload.get("limit", 8))
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be positive")

    # 1. Embed the query
    provider = OllamaEmbeddingProvider()
    try:
        query_vector = await provider.embed_query(query_text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {exc}")

    # 2. Perform vector search
    client = _get_client()
    try:
        collection = client.collections.get("MemoryArtifact")
        # Build the query payload
        query_payload = {
            "vector": query_vector,
            "limit": limit,
            "properties": [
                "artifact_id",
                "parent_id",
                "content",
                "artifact_type",
                "execution_id",
                "event_id",
                "source",
                "source_url",
                "chunk_index",
                "chunk_count",
            ],
        }
        results = collection.query(query_payload)
        # The response structure: {"data": {"Get": {"MemoryArtifact": [ {"id":..., "properties":{...} } ] }}}
        artifacts = results.get("data", {}).get("Get", {}).get("MemoryArtifact", [])
        # Normalize
        normalized = []
        for art in artifacts:
            props = art.get("properties", {})
            normalized.append({
                "artifact_id": props.get("artifact_id"),
                "parent_id": props.get("parent_id"),
                "content": props.get("content"),
                "artifact_type": props.get("artifact_type"),
                "execution_id": props.get("execution_id"),
                "event_id": props.get("event_id"),
                "source": props.get("source"),
                "source_url": props.get("source_url"),
                "chunk_index": props.get("chunk_index"),
                "chunk_count": props.get("chunk_count"),
            })
        return normalized
    finally:
        client.close()

# End of module
