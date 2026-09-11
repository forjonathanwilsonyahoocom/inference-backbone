import pytest
import weaviate
from memory import ensure_memory_collection, _get_client

# Test that the collection can be created and is idempotent

@pytest.mark.timeout(10)
def test_memory_collection_creation_and_idempotency():
    """Verify that ``EvidenceChunk`` collection is created and that
    calling the creation routine twice does not raise an exception.
    """
    # First call – should create the collection
    ensure_memory_collection()
    client = _get_client()
    try:
        assert client.collections.exists("EvidenceChunk"), "Collection should exist after first call"
        # Inspect the schema to confirm properties
        schema = client.collections.get("EvidenceChunk").schema
        prop_names = {p.name for p in schema.properties}
        expected = {
            "content",
            "artifact_id",
            "artifact_type",
            "execution_id",
            "event_id",
            "source",
            "source_url",
            "chunk_index",
            "chunk_count",
            "parent_id",
            "embedding_model",
            "embedding_task",
        }
        assert prop_names == expected, f"Unexpected properties: {prop_names - expected}"
        # Second call – should be idempotent
        ensure_memory_collection()
    finally:
        client.close()
