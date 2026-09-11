import os
import json
import pytest
import requests
from fastapi.testclient import TestClient
from inference_backbone.fastapi.app import app
from inference_backbone.fastapi.chunker import chunk_text
from inference_backbone.fastapi.embedding_provider import OllamaEmbeddingProvider
from inference_backbone.fastapi.memory import _get_client

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _is_weaviate_reachable() -> bool:
    """Return True if the Weaviate instance defined by env vars is reachable."""
    try:
        client = _get_client()
        return client.is_ready()
    except Exception:
        return False
    finally:
        try:
            client.close()
        except Exception:
            pass


def _is_ollama_reachable(base_url: str) -> bool:
    """Return True if the Ollama server responds to an embeddings request."""
    try:
        resp = requests.post(
            f"{base_url}/api/embeddings",
            json={"model": "nomic-embed-text:latest", "input": ["test"]},
            timeout=5,
        )
        return resp.status_code == 200 and "embeddings" in resp.json()
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Test configuration
# ---------------------------------------------------------------------------
# Use the default Docker‑Compose values – the tests will be skipped if the
# services are not running.
os.environ.setdefault("WEAVIATE_HTTP_HOST", "localhost")
os.environ.setdefault("WEAVIATE_HTTP_PORT", "8084")
os.environ.setdefault("WEAVIATE_GRPC_HOST", "localhost")
os.environ.setdefault("WEAVIATE_GRPC_PORT", "50051")

# Ollama – the tests will be skipped if the server is not reachable.
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _is_weaviate_reachable(), reason="Weaviate not reachable")
@pytest.mark.skipif(
    not _is_ollama_reachable(os.getenv("OLLAMA_BASE_URL")),
    reason="Ollama not reachable",
)
def test_memory_ingest_end_to_end():
    """Full‑stack test of the /memory/ingest endpoint.

    The test:
    1. Builds a payload with a short text.
    2. Calls the FastAPI endpoint via TestClient.
    3. Verifies the HTTP response.
    4. Checks that the returned chunk IDs exist in Weaviate.
    5. Validates that the stored objects contain the expected properties
       and vectors.
    6. Cleans up the inserted objects.
    """
    client = TestClient(app)

    # ---------------------------------------------------------------------
    # 1. Build payload
    # ---------------------------------------------------------------------
    content = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris."
    )
    payload = {
        "content": content,
        "artifact_type": "test-artifact",
        "execution_id": "exec-123",
        "event_id": "event-456",
        "source": "unit-test",
        "source_url": "http://example.com",
        "metadata": {"foo": "bar"},
    }

    # ---------------------------------------------------------------------
    # 2. Call endpoint
    # ---------------------------------------------------------------------
    resp = client.post("/memory/ingest", json=payload)
    assert resp.status_code == 200, f"Unexpected status: {resp.text}"
    data = resp.json()

    # ---------------------------------------------------------------------
    # 3. Basic response checks
    # ---------------------------------------------------------------------
    assert data["artifact_id"] == payload["artifact_type"], "artifact_id mismatch"
    assert "parent_id" in data, "Missing parent_id"
    assert "chunk_count" in data, "Missing chunk_count"
    assert "chunks" in data, "Missing chunks list"

    # ---------------------------------------------------------------------
    # 4. Chunking logic
    # ---------------------------------------------------------------------
    expected_chunks = chunk_text(content)
    assert data["chunk_count"] == len(expected_chunks), "chunk_count mismatch"
    assert len(data["chunks"]) == len(expected_chunks), "chunks list length mismatch"

    # ---------------------------------------------------------------------
    # 5. Verify objects in Weaviate
    # ---------------------------------------------------------------------
    weaviate_client = _get_client()
    try:
        for idx, chunk_id in enumerate(data["chunks"]):
            obj = weaviate_client.collections.get("MemoryArtifact").get(chunk_id)
            assert obj is not None, f"Chunk {chunk_id} not found in Weaviate"
            props = obj["properties"]
            # Basic property checks
            assert props["content"] == expected_chunks[idx]
            assert props["artifact_id"] == payload["artifact_type"]
            assert props["artifact_type"] == payload["artifact_type"]
            assert props["execution_id"] == payload["execution_id"]
            assert props["event_id"] == payload["event_id"]
            assert props["source"] == payload["source"]
            assert props["source_url"] == payload.get("source_url")
            assert props["chunk_index"] == idx
            assert props["chunk_count"] == len(expected_chunks)
            assert props["parent_id"] == data["parent_id"]
            assert props["embedding_model"] == os.getenv("OLLAMA_EMBED_MODEL")
            assert props["embedding_task"] == "document"
            # Vector checks
            vector = obj["vector"]
            assert vector is not None, "Missing vector"
            assert isinstance(vector, list), "Vector is not a list"
            assert len(vector) > 0, "Empty vector"
    finally:
        weaviate_client.close()

    # ---------------------------------------------------------------------
    # 6. Cleanup – delete inserted objects
    # ---------------------------------------------------------------------
    weaviate_client = _get_client()
    try:
        for chunk_id in data["chunks"]:
            weaviate_client.collections.get("MemoryArtifact").delete(chunk_id)
    finally:
        weaviate_client.close()

    # Verify cleanup
    weaviate_client = _get_client()
    try:
        for chunk_id in data["chunks"]:
            obj = weaviate_client.collections.get("MemoryArtifact").get(chunk_id)
            assert obj is None, f"Chunk {chunk_id} still present after cleanup"
    finally:
        weaviate_client.close()

    # ---------------------------------------------------------------------
    # 7. Repeat ingestion to test deterministic parent_id
    # ---------------------------------------------------------------------
    resp2 = client.post("/memory/ingest", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["parent_id"] == data["parent_id"], "Parent ID should be deterministic"

    # Cleanup second batch
    weaviate_client = _get_client()
    try:
        for chunk_id in data2["chunks"]:
            weaviate_client.collections.get("MemoryArtifact").delete(chunk_id)
    finally:
        weaviate_client.close()
