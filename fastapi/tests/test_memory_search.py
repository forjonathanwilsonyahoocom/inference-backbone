import os
import json
import pytest
import requests
from fastapi.testclient import TestClient
from app import app
from chunker import chunk_text
from memory import _get_client, ensure_memory_collection

# Helper functions

def _is_weaviate_reachable() -> bool:
    client = None
    try:
        client = _get_client()
        return client.is_ready()
    except Exception:
        return False
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass

def _is_ollama_reachable(base_url: str) -> bool:
    try:
        resp = requests.post(
            f"{base_url}/api/embeddings",
            json={"model": "nomic-embed-text:latest", "input": ["test"]},
            timeout=5,
        )
        return resp.status_code == 200 and "embeddings" in resp.json()
    except Exception:
        return False

# Set default env vars for tests
os.environ.setdefault("WEAVIATE_HTTP_HOST", "localhost")
os.environ.setdefault("WEAVIATE_HTTP_PORT", "8084")
os.environ.setdefault("WEAVIATE_GRPC_HOST", "localhost")
os.environ.setdefault("WEAVIATE_GRPC_PORT", "50051")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")

@pytest.mark.skipif(not _is_weaviate_reachable(), reason="Weaviate not reachable")
@pytest.mark.skipif(
    not _is_ollama_reachable(os.getenv("OLLAMA_BASE_URL")),
    reason="Ollama not reachable",
)
def test_memory_search_end_to_end():
    """Full‑stack test of the /memory/search endpoint.

    The test:
    1. Ingests a known text via the /memory/ingest endpoint.
    2. Performs a semantic search with a query that is semantically
       related to the ingested text.
    3. Verifies that the returned results contain the expected content
       and that all metadata fields survive the round‑trip.
    4. Cleans up the inserted objects.
    """
    client = TestClient(app)

    # ---------------------------------------------------------------------
    # 1. Ingest known text
    # ---------------------------------------------------------------------
    content = (
        "The quick brown fox jumps over the lazy dog. "
        "Pack my box with five dozen liquor jugs. "
        "How vexingly quick daft zebras jump!"
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
    ingest_resp = client.post("/memory/ingest", json=payload)
    assert ingest_resp.status_code == 200, f"Ingest failed: {ingest_resp.text}"
    ingest_data = ingest_resp.json()
    assert ingest_data["artifact_id"] == payload["artifact_type"], "artifact_id mismatch"
    assert "parent_id" in ingest_data
    assert "chunk_count" in ingest_data
    assert "chunks" in ingest_data

    # ---------------------------------------------------------------------
    # 2. Perform semantic search
    # ---------------------------------------------------------------------
    # Query that is semantically related to the content: "quick fox"
    search_payload = {"query": "quick fox", "limit": 5}
    search_resp = client.post("/memory/search", json=search_payload)
    assert search_resp.status_code == 200, f"Search failed: {search_resp.text}"
    results = search_resp.json()
    assert isinstance(results, list), "Results should be a list"
    assert len(results) > 0, "Expected at least one search result"

    # ---------------------------------------------------------------------
    # 3. Verify that at least one result contains the expected content
    # ---------------------------------------------------------------------
    expected_chunks = chunk_text(content)
    found = False
    for res in results:
        # Each result should contain the required keys
        required_keys = {
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
        }
        assert required_keys.issubset(res.keys()), f"Missing keys in result: {set(res) - required_keys}"
        # Check that the content matches one of the chunks
        if res["content"] in expected_chunks:
            found = True
            # Verify metadata matches the ingest payload
            assert res["artifact_id"] == payload["artifact_type"], "artifact_id mismatch"
            assert res["execution_id"] == payload["execution_id"], "execution_id mismatch"
            assert res["event_id"] == payload["event_id"], "event_id mismatch"
            assert res["source"] == payload["source"], "source mismatch"
            assert res["source_url"] == payload.get("source_url"), "source_url mismatch"
            assert res["chunk_count"] == ingest_data["chunk_count"], "chunk_count mismatch"
            assert res["parent_id"] == ingest_data["parent_id"], "parent_id mismatch"
    assert found, "No result matched the expected content"

    # ---------------------------------------------------------------------
    # 4. Cleanup inserted objects
    # ---------------------------------------------------------------------
    weaviate_client = _get_client()
    try:
        for chunk_id in ingest_data["chunks"]:
            weaviate_client.collections.get("EvidenceChunk").delete(chunk_id)
    finally:
        weaviate_client.close()

    # Verify cleanup
    weaviate_client = _get_client()
    try:
        for chunk_id in ingest_data["chunks"]:
            obj = weaviate_client.collections.get("EvidenceChunk").get(chunk_id)
            assert obj is None, f"Chunk {chunk_id} still present after cleanup"
    finally:
        weaviate_client.close()

    # ---------------------------------------------------------------------
    # 5. Test limit enforcement
    # ---------------------------------------------------------------------
    # Re‑ingest to have data again
    ingest_resp = client.post("/memory/ingest", json=payload)
    assert ingest_resp.status_code == 200
    ingest_data = ingest_resp.json()
    search_payload = {"query": "quick fox", "limit": 1}
    search_resp = client.post("/memory/search", json=search_payload)
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert len(results) == 1, "Search limit not respected"

    # Cleanup second batch
    weaviate_client = _get_client()
    try:
        for chunk_id in ingest_data["chunks"]:
            weaviate_client.collections.get("EvidenceChunk").delete(chunk_id)
    finally:
        weaviate_client.close()

    # ---------------------------------------------------------------------
    # 6. Test error handling
    # ---------------------------------------------------------------------
    # Missing query
    bad_resp = client.post("/memory/search", json={"limit": 5})
    assert bad_resp.status_code == 400, "Expected 400 for missing query"
    # Negative limit
    bad_resp = client.post("/memory/search", json={"query": "quick", "limit": -1})
    assert bad_resp.status_code == 400, "Expected 400 for negative limit"

    # ---------------------------------------------------------------------
    # 7. Test empty results
    # ---------------------------------------------------------------------
    # Query something unlikely
    empty_resp = client.post("/memory/search", json={"query": "zzzzzzzzzz", "limit": 5})
    assert empty_resp.status_code == 200
    empty_results = empty_resp.json()
    assert isinstance(empty_results, list)
    assert len(empty_results) == 0, "Expected no results for unrelated query"

    # All checks passed
    print("Memory search integration test passed")

# End of test file
