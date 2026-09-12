# import pytest

from inference_contracts.evidence import Evidence
from inference_contracts.evidence_chunk import EvidenceChunk
from inference_contracts.projection import evidence_to_chunk, chunks_to_evidence


def sample_evidence() -> Evidence:
    return Evidence(id="e1", text="Sample evidence text.")


def test_projection_roundtrip(sample_evidence: Evidence):
    chunk = evidence_to_chunk(sample_evidence)
    assert isinstance(chunk, EvidenceChunk)
    assert chunk.id == sample_evidence.id
    assert chunk.text == sample_evidence.text

    # round‑trip back
    recovered = list(chunks_to_evidence([chunk]))
    assert len(recovered) == 1
    assert recovered[0] == sample_evidence


def test_schema_generation():
    # Ensure the schema contains the expected fields
    schema = Evidence.model_json_schema()
    assert "properties" in schema
    assert "id" in schema["properties"]
    assert "text" in schema["properties"]
    assert schema["properties"]["id"]["type"] == "string"
    assert schema["properties"]["text"]["type"] == "string"
