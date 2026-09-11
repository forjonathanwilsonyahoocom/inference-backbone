"""Integration test: worker event → indexed artifact → validator retrieves artifact → validator associates it with execution/event identity.

This test demonstrates the semantic memory retrieval flow:
1. A worker event is executed (simulated)
2. The result is ingested into Weaviate (via the fastapi app)
3. The validator searches for relevant artifacts (via the fastapi app)
4. The validator can distinguish direct vs. retrieved evidence

The test does NOT modify the existing validator behavior — it only adds
the supplemental evidence path.
"""

import json
import uuid
from typing import Any

from fastapi.testclient import TestClient

from fastapi.app import app as fastapi_app
from main import app as validator_app


# ---------------------------------------------------------------------------
# 1. Simulate a worker event
# ---------------------------------------------------------------------------

def simulate_worker_event() -> dict:
    """Simulate a tool call from the worker agent."""
    return {
        "iteration": 1,
        "tool": "read_file",
        "args": {"path": "./inference-backbone/README.md"},
        "result": "This is the README content...",
    }


# ---------------------------------------------------------------------------
# 2. Ingest the result into Weaviate
# ---------------------------------------------------------------------------

def ingest_into_memory(event: dict) -> dict:
    """Ingest a tool result into Weaviate via the memory_ingest endpoint."""
    client = TestClient(fastapi_app)
    payload = {
        "content": event["result"],
        "artifact_type": event["tool"],
        "execution_id": str(uuid.uuid4()),
        "event_id": str(uuid.uuid4()),
        "source": "worker-agent",
        "source_url": None,
    }

    response = client.post("/memory/ingest", json=payload)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# 3. Search for the artifact
# ---------------------------------------------------------------------------

def search_memory(query: str, limit: int = 5) -> list:
    """Search Weaviate for relevant artifacts."""
    client = TestClient(fastapi_app)
    payload = {"query": query, "limit": limit}
    response = client.post("/memory/search", json=payload)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# 4. Validate with supplemental evidence
# ---------------------------------------------------------------------------

def validate_with_supplemental(
    task_description: str,
    final_response: str,
    events: list,
    supplemental_evidence: list,
) -> dict:
    """Validate claims against both direct and supplemental evidence."""
    client = TestClient(validator_app)
    payload = {
        "task_description": task_description,
        "final_response": final_response,
        "events": events,
        "supplemental_evidence": supplemental_evidence,
    }

    response = client.post("/validate", json=payload)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# 5. Run the integration test
# ---------------------------------------------------------------------------

def test_semantic_memory_flow():
    """Demonstrate the full flow: worker event → indexed artifact → validator retrieves artifact → validator can associate it with execution/event identity."""

    # Step 1: Simulate a worker event
    worker_event = simulate_worker_event()
    print(f"Step 1: Worker event executed")
    print(f"  Tool: {worker_event['tool']}")
    print(f"  Result: {worker_event['result'][:50]}...")

    # Step 2: Ingest into memory
    ingested = ingest_into_memory(worker_event)
    print(f"\nStep 2: Ingested into memory")
    print(f"  Artifact ID: {ingested['artifact_id']}")
    print(f"  Parent ID: {ingested['parent_id']}")
    print(f"  Chunk count: {ingested['chunk_count']}")

    # Step 3: Search for the artifact
    search_results = search_memory("README content", limit=5)
    print(f"\nStep 3: Searched memory")
    print(f"  Found {len(search_results)} results")
    if search_results:
        print(f"  First result artifact_id: {search_results[0]['artifact_id']}")
        print(f"  First result content: {search_results[0]['content'][:50]}...")

    # Step 4: Validate with supplemental evidence
    task = "Read the README and report its content."
    final_response = "The README says 'This is the README content...'."
    events = [worker_event]
    supplemental = search_results[:2] if search_results else []

    validation_result = validate_with_supplemental(
        task_description=task,
        final_response=final_response,
        events=events,
        supplemental_evidence=supplemental,
    )
    print(f"\nStep 4: Validation result")
    print(f"  Claims: {validation_result.get('claims', [])}")
    print(f"  Overall verdict: {validation_result.get('overall_verdict')}")

    # Step 5: Verify provenance
    claims = validation_result.get("claims", [])
    if claims:
        print(f"\nStep 5: Provenance check")
        for claim in claims:
            print(f"  Claim: {claim['text']}")
            print(f"    Supported: {claim['supported']}")
            print(f"    Evidence: {claim['evidence']}")
            print(f"    Provenance: {claim['provenance']}")

    return validation_result


if __name__ == "__main__":
    result = test_semantic_memory_flow()
    print(f"\nFinal result: {json.dumps(result, indent=2)}")
