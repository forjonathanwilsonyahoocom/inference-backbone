from datetime import datetime
from pathlib import Path
from typing import List

from .evidence import Evidence
from .evidence_chunk import EvidenceChunk

# Simple projection: split content into chunks of max 200 chars
MAX_CHUNK_SIZE = 200

def evidence_to_chunks(evidence: Evidence, chunk_size: int = MAX_CHUNK_SIZE) -> List[EvidenceChunk]:
    content = evidence.content
    chunks = []
    for i, start in enumerate(range(0, len(content), chunk_size)):
        chunk_text = content[start : start + chunk_size]
        chunk = EvidenceChunk(
            chunk_id=f"{evidence.evidence_id}_chunk_{i}",
            evidence_id=evidence.evidence_id,
            content=chunk_text,
            chunk_index=i,
            chunk_count=0,  # will be updated later
            embedding_model="default-model",
            embedding_task="default-task",
        )
        chunks.append(chunk)
    # update chunk_count
    for chunk in chunks:
        chunk.chunk_count = len(chunks)
    return chunks

# Reverse projection: reconstruct content from chunks

def chunks_to_evidence(chunks: List[EvidenceChunk]) -> Evidence:
    if not chunks:
        raise ValueError("No chunks provided")
    # assume all chunks belong to same evidence_id
    evidence_id = chunks[0].evidence_id
    # sort by chunk_index
    chunks_sorted = sorted(chunks, key=lambda c: c.chunk_index)
    content = "".join(c.content for c in chunks_sorted)
    # create a minimal Evidence with just id and content
    return Evidence(
        evidence_id=evidence_id,
        execution_id="",
        event_id="",
        content=content,
        content_hash="",
        source_type="",
        observed_at=datetime.now(),
        retrieved_at=datetime.now(),
        extraction_method="",
        worker_version="",
        metadata={},
    )

# Simple test harness
if __name__ == "__main__":
    # load sample evidence from json file if exists
    sample_path = Path("sample_evidence.json")
    if sample_path.exists():
        data = json.loads(sample_path.read_text())
        ev = Evidence(**data)
    else:
        ev = Evidence(
            evidence_id="ev1",
            execution_id="ex1",
            event_id="evnt1",
            content="This is a long content string that will be split into chunks.",
            content_hash="hash1",
            source_type="type1",
            observed_at=None,
            retrieved_at=None,
            extraction_method="method1",
            worker_version="v1",
            metadata={},
        )
    chunks = evidence_to_chunks(ev)
    print("Generated", len(chunks), "chunks")
    ev_reconstructed = chunks_to_evidence(chunks)
    print("Reconstructed content matches:", ev.content == ev_reconstructed.content)

