from typing import Iterable

from inference_contracts.evidence import Evidence
from inference_contracts.evidence_chunk import EvidenceChunk

# Simple projection helpers – these are intentionally explicit.

def evidence_to_chunk(evidence: Evidence) -> EvidenceChunk:
    """Project an :class:`Evidence` into an :class:`EvidenceChunk`.

    The function is a thin wrapper that simply copies the ``id`` and
    ``text`` fields.  It is kept separate so that future changes to the
    projection logic can be isolated.
    """
    return EvidenceChunk(id=evidence.id, text=evidence.text)


def chunks_to_evidence(chunks: Iterable[EvidenceChunk]) -> Iterable[Evidence]:
    """Inverse projection – useful for tests that round‑trip data.
    """
    for chunk in chunks:
        yield Evidence(id=chunk.id, text=chunk.text)
