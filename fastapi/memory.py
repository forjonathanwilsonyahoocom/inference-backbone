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
from weaviate.collections.classes.config import (
    Property,
    DataType,
    Configure,
)
from weaviate.collections.classes import Collection

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


def _get_client() -> weaviate.Client:
    """Return a new :class:`weaviate.Client` instance.

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
        schema = CollectionSchema(
            properties=[
                Property(name="content", data_type=DataType.TEXT),
                Property(name="artifact_id", data_type=DataType.TEXT),
                Property(name="artifact_type", data_type=DataType.TEXT),
                Property(name="execution_id", data_type=DataType.TEXT),
                Property(name="event_id", data_type=DataType.TEXT),
                Property(name="source", data_type=DataType.TEXT),
                Property(name="source_url", data_type=DataType.TEXT),
                Property(name="chunk_index", data_type=DataType.INT),
                Property(name="chunk_count", data_type=DataType.INT),
                Property(name="parent_id", data_type=DataType.TEXT),
                Property(name="embedding_model", data_type=DataType.TEXT),
                Property(name="embedding_task", data_type=DataType.TEXT),
            ],
            description="Collection for storing memory artifacts with externally supplied vectors.",
        )

        client.collections.create(
            name="MemoryArtifact",
            schema=schema,
            vector_config=Configure.Vectors.self_provided(),
        )
    finally:
        client.close()

# ---------------------------------------------------------------------------
# End of module
# ---------------------------------------------------------------------------
