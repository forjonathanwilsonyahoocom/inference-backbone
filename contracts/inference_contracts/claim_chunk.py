from pydantic import BaseModel


class ClaimChunk(BaseModel):
    chunk_id: str | None = None
    execution_id: str
    evidence_id: str
    event_id: str
    
    content: str

    chunk_index: int
    chunk_count: int

    embedding_model: str | None = None
    embedding_task: str

