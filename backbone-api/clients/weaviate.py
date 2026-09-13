"""FastAPI evidence module for Weaviate access.

This module provides a thin wrapper around the Weaviate v4 client and
creates an idempotent ``EvidenceChunk`` collection and exposes a helper
function to obtain a client instance.
"""

from __future__ import annotations

import os
from typing import Any

import weaviate
from weaviate.classes.config import Property, DataType, Configure

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

def get_weaviate_client() -> weaviate.WeaviateClient:
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


def ensure_weaviate_collection(collection_name: str) -> None:
    """Create the ``collection_name`` collection if it does not exist.

    The operation is idempotent – calling it multiple times will not
    raise an exception or overwrite an existing collection.
    """
    client = get_weaviate_client()
    try:
        if client.collections.exists(collection_name):
            # Already present – nothing to do.
            return
        client.collections.create(
            collection_name,
            vector_config=Configure.Vectors.self_provided(),
        )
    finally:
        client.close()

# ---------------------------------------------------------------------------
# End of module
# ---------------------------------------------------------------------------
