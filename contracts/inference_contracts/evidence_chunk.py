from pydantic import BaseModel


class EvidenceChunk(BaseModel):
    chunk_id: str | None = None
    evidence_id: str

    content: str

    chunk_index: int
    chunk_count: int

    embedding_model: str | None = None
    embedding_task: str

