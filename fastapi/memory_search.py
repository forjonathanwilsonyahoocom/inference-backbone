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
from weaviate.classes.query import MetadataQuery

from embedding_provider import OllamaEmbeddingProvider

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
    print("/memory/search")
    
    if "query" not in payload:
        raise HTTPException(status_code=400, detail="Missing required key: query")
    query_text: str = payload["query"]
    limit: int = int(payload.get("limit", 8))
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be positive")

    print(query_text, limit )
    # 1. Embed the query
    provider = OllamaEmbeddingProvider()
    try:
        query_vector = await provider.embed_query(query_text)
    except Exception as exc:
        print("EMBEDDING FAILURE",exc)
        raise HTTPException(status_code=500, detail=f"Embedding failed: {exc}")

    # 2. Perform vector search
    client = _get_client()

    print("EMBEDDING FAILURE",exc)
    try:
        collection =  client.collections.use("MemoryArtifact")
        # Build the query payload
        
        results = collection.query.near_vector(
            near_vector=query_vector, # your query vector goes here
            limit=limit,
            return_metadata=MetadataQuery(distance=True))
            
        # Normalize
        normalized = []
        for art in response.objects:
            normalized.append({"properties" : art.properties,
                               "distance" : art.metadata.distance})
        return normalized
    except Exception as e:
        print("COLLECTION QUERY FAILURE",e)
    finally:
        client.close()

# End of module
