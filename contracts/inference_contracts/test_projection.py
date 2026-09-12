import unittest
from datetime import datetime

from .evidence import Evidence
from .evidence_chunk import EvidenceChunk
from .projection import evidence_to_chunks, chunks_to_evidence

class TestProjection(unittest.TestCase):
    def setUp(self):
        self.evidence = Evidence(
            evidence_id="ev1",
            execution_id="ex1",
            event_id="evnt1",
            content="Hello world! This is a test content that will be split.",
            content_hash="hash1",
            source_type="type1",
            observed_at=datetime.now(),
            retrieved_at=datetime.now(),
            extraction_method="method1",
            worker_version="v1",
            metadata={},
        )

    def test_chunks_preserve_identity(self):
        chunks = evidence_to_chunks(self.evidence, chunk_size=10)
        # all chunks should reference same evidence_id
        for chunk in chunks:
            self.assertEqual(chunk.evidence_id, self.evidence.evidence_id)

    def test_chunks_preserve_content(self):
        chunks = evidence_to_chunks(self.evidence, chunk_size=10)
        reconstructed = chunks_to_evidence(chunks)
        self.assertEqual(reconstructed.content, self.evidence.content)

if __name__ == "__main__":
    unittest.main()
