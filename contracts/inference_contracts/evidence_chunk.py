from pydantic import BaseModel


class EvidenceChunk(BaseModel):
    chunk_id: str | None = None
    execution_id: str
    evidence_id: str
    source_type: str | None = None #backwards compat before this existed
    instance_number: int # numbering within the execution
    
    content: str

    chunk_index: int
    chunk_count: int

    embedding_model: str | None = None

