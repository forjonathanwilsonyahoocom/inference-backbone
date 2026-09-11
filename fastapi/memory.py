"""FastAPI memory module for Weaviate access.

This module provides a thin wrapper around the Weaviate v4 client that
creates an idempotent ``MemoryArtifact`` collection and exposes a helper
function to obtain a client instance.

The collection is defined with externally supplied vectors (``self_provided``)
and the following properties:

* ``content``          – TEXT
* ``artifact_id``      – TEXT
* ``artifact_type``    – TEXT
* ``execution_id``     – TEXT
* ``event_id``         – TEXT
* ``source``           – TEXT
* ``source_url``       – TEXT
* ``chunk_index``      – INT
* ``chunk_count``      – INT
* ``parent_id``        – TEXT
* ``embedding_model``  – TEXT
* ``embedding_task``   – TEXT

The module is intentionally lightweight – it does not expose the raw
Weaviate client to the rest of the application.  Only the two helper
functions are exported.
"""

from __future__ import annotations

import os
from typing import Any

import weaviate
from weaviate.classes.config import Property, DataType

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

# Default connection parameters – these match the docker‑compose setup.
_HTTP_HOST = os.getenv("WEAVIATE_HTTP_HOST", "weaviate")
_HTTP_PORT = int(os.getenv("WEAVIATE_HTTP_PORT", "8080"))
_GRPC_HOST = os.getenv("WEAVIATE_GRPC_HOST", "weaviate")
_GRPC_PORT = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["_get_client", "ensure_memory_collection"]


def _get_client() -> weaviate.WeaviateClient:
    """Return a new :class:`weaviate.WeaviateClient` instance.

    The function reads the connection parameters from environment
    variables.  It is intentionally lightweight so that callers can
    create a client on demand without keeping a global singleton.
    """
    return weaviate.connect_to_custom(
        http_host=_HTTP_HOST,
        http_port=_HTTP_PORT,
        http_secure=False,
        grpc_host=_GRPC_HOST,
        grpc_port=_GRPC_PORT,
        grpc_secure=False,
    )


def ensure_memory_collection() -> None:
    """Create the ``MemoryArtifact`` collection if it does not exist.

    The operation is idempotent – calling it multiple times will not
    raise an exception or overwrite an existing collection.
    """
    client = _get_client()
    try:
        if client.collections.exists("MemoryArtifact"):
            # Already present – nothing to do.
            return

        # Define the schema – the order of properties is not
        # significant but keeping it stable makes debugging easier.
        schema = {
            "class": "MemoryArtifact",
            "properties": [
                {"name": "content", "dataType": ["text"]},
                {"name": "artifact_id", "dataType": ["text"]},
                {"name": "artifact_type", "dataType": ["text"]},
                {"name": "execution_id", "dataType": ["text"]},
                {"name": "event_id", "dataType": ["text"]},
                {"name": "source", "dataType": ["text"]},
                {"name": "source_url", "dataType": ["text"]},
                {"name": "chunk_index", "dataType": ["int"]},
                {"name": "chunk_count", "dataType": ["int"]},
                {"name": "parent_id", "dataType": ["text"]},
                {"name": "embedding_model", "dataType": ["text"]},
                {"name": "embedding_task", "dataType": ["text"]},
            ],
            "vectorIndexConfig": {
                "vectorIndexType": "hnsw",
                "distanceMetric": "COSINE",
                "vectorIndexConfig": {
                    "ef": 64,
                    "M": 16,
                    "maxConnections": 512,
                    "cleanupIntervalSeconds": 30,
                },
            },
        }

        client.collections.create(
            class_config=schema,
            vector_index_config=weaviate.classes.config.VectorIndexConfig(
                vector_index_type="hnsw",
                distance_metric=weaviate.classes.config.DistanceMetric.COSINE,
                ef=64,
                M=16,
                max_connections=512,
                cleanup_interval_seconds=30,
            ),
        )
    finally:
        client.close()

# ---------------------------------------------------------------------------
# End of module
# ---------------------------------------------------------------------------
