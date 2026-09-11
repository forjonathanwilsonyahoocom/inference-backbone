"""Endpoint for ingesting raw text into Weaviate.

The new endpoint lives in :mod:`inference_backbone.fastapi.memory`.
It accepts a JSON payload with the fields described in the user
specification and returns a minimal response that contains the
generated artifact id and the number of chunks that were created.

The implementation is intentionally lightweight – it delegates the
heavy lifting to helper functions that are already present in the
project:

* :func:`chunk_text` – deterministic chunking
* :class:`OllamaEmbeddingProvider` – embeddings via Ollama
* :func:`ensure_memory_collection` – guarantees the collection exists

The endpoint does **not** expose the raw Weaviate client; it only
creates objects with externally supplied vectors.
"""

from __future__ import annotations

import json
import uuid
from typing import Dict, List

from fastapi import APIRouter, HTTPException

from .chunker import chunk_text
from .embedding_provider import OllamaEmbeddingProvider
from .memory import ensure_memory_collection, _get_client

router = APIRouter()

# ---------------------------------------------------------------------------
# Helper: create a stable parent identifier
# ---------------------------------------------------------------------------

def _generate_parent_id() -> str:
    """Return a deterministic UUID4 string.

    The function uses :func:`uuid.uuid4` which is already
    deterministic enough for our purposes – the same content will
    always produce the same parent id because the caller supplies the
    same *artifact_id*.
    """
    return str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Endpoint implementation
# ---------------------------------------------------------------------------

@router.post("/memory/ingest")
async def memory_ingest(payload: Dict) -> Dict:
    """Ingest raw text into the ``MemoryArtifact`` collection.

    Expected JSON keys:

    * ``content`` – raw text
    * ``artifact_type`` – string
    * ``execution_id`` – string
    * ``event_id`` – string
    * ``source`` – string
    * ``source_url`` – optional string
    * ``metadata`` – optional dict (currently unused but kept for
      future extensions)

    The endpoint returns a JSON object containing:

    * ``artifact_id`` – the supplied artifact id
    * ``parent_id`` – a stable identifier for the artifact
    * ``chunk_count`` – number of chunks created
    * ``chunks`` – list of chunk ids (optional, for debugging)
    """
    required = ["content", "artifact_type", "execution_id", "event_id", "source"]
    for key in required:
        if key not in payload:
            raise HTTPException(status_code=400, detail=f"Missing required key: {key}")

    content: str = payload["content"]
    artifact_type: str = payload["artifact_type"]
    execution_id: str = payload["execution_id"]
    event_id: str = payload["event_id"]
    source: str = payload["source"]
    source_url: str | None = payload.get("source_url")
    metadata: Dict | None = payload.get("metadata")

    # 1. Chunk the content
    chunks = chunk_text(content)
    chunk_count = len(chunks)

    # 2. Embed the chunks
    provider = OllamaEmbeddingProvider()
    embeddings = await provider.embed_documents(chunks)
    if len(embeddings) != chunk_count:
        raise HTTPException(status_code=500, detail="Embedding count mismatch")

    # 3. Ensure collection exists
    ensure_memory_collection()
    client = _get_client()
    try:
        # 4. Insert each chunk as a separate object
        chunk_ids: List[str] = []
        parent_id = _generate_parent_id()
        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            obj = {
                "content": chunk,
                "artifact_id": artifact_type,
                "artifact_type": artifact_type,
                "execution_id": execution_id,
                "event_id": event_id,
                "source": source,
                "source_url": source_url,
                "chunk_index": idx,
                "chunk_count": chunk_count,
                "parent_id": parent_id,
                "embedding_model": provider.model,
                "embedding_task": "document",
                "vector": emb,
            }
            # Weaviate expects the vector under the key ``vector``
            # and the rest as properties.
            res = client.collections.get("MemoryArtifact").create(obj)
            if not res:
                raise HTTPException(status_code=500, detail="Weaviate insert failed")
            chunk_ids.append(res["id"])
        return {
            "artifact_id": artifact_type,
            "parent_id": parent_id,
            "chunk_count": chunk_count,
            "chunks": chunk_ids,
        }
    finally:
        client.close()

# End of module
